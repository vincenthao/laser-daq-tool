"""宽表 CSV 导出 (V2) — 按设备类型分组."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型
from typing import Optional  # 可选类型

from PyQt6.QtCore import QObject, pyqtSignal, QThread  # Qt 核心类
import pandas as pd  # 数据处理库

from laser_daq.models.data_model import DataModel  # 数据模型
from laser_daq.models.annotation import Annotation  # 标注
from laser_daq.constants import DataType, PD_PWR_NAME, PD_PWR_UNIT, EXCLUDED_FUNC_GROUPS  # 常量
from laser_daq.workers.export_worker import ExportWorker  # 导出工作线程


class ExportController(QObject):
    """管理训练集 CSV 的导出 (V2).

    Signals:
        export_started(): 开始导出
        export_progress(current, total): 进度更新
        export_finished(file_paths): 导出完成（路径列表）
        export_error(message): 导出失败
    """  # 类文档

    export_started = pyqtSignal()  # 开始导出
    export_progress = pyqtSignal(int, int)  # 当前, 总计
    export_finished = pyqtSignal(object)  # list[Path]
    export_error = pyqtSignal(str)  # 错误消息

    def __init__(self, data_model: DataModel, parent: QObject = None) -> None:
        """初始化 ExportController.

        Args:
            data_model: 共享的 DataModel 实例
            parent: Qt 父对象
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._model: DataModel = data_model  # 持有数据模型引用
        self._thread: Optional[QThread] = None  # 工作线程
        self._worker: Optional[ExportWorker] = None  # 工作对象

    def export(self, output_dir: object, selected_types: object) -> None:
        """导出每种设备类型的宽表 CSV (V2).

        Args:
            output_dir: 输出目录（str 或 Path）
            selected_types: 要导出的设备类型名称列表
        """  # 方法文档
        if self._model.raw_df.empty:  # 无数据
            self.export_error.emit("没有数据可以导出，请先导入 CSV")
            return

        try:  # 捕获异常
            out_path = Path(str(output_dir))  # 确保是 Path 对象

            types_list: list[str] = []
            if isinstance(selected_types, list):
                types_list = selected_types
            elif selected_types is not None:
                try:
                    types_list = list(selected_types)
                except TypeError:
                    pass

            file_data: dict[str, pd.DataFrame] = {}  # 文件名 -> DataFrame
            grouped = self._model.get_grouped_devices()  # 按设备类型分组

            total = 0  # 总计数
            for type_name, devices in grouped.items():
                if types_list and type_name not in types_list:
                    continue
                for dt in devices:
                    for slot in sorted(dt.slots):
                        slot_data = self._model.get_slot_data(dt.node_id, slot)  # V2: 自动过滤 RPTREGS
                        if slot_data.empty:
                            continue
                        annotations = self._model.get_annotations_for_slot(dt.node_id, slot)  # 获取标注
                        wide_df = self.build_wide_table(slot_data, annotations, dt.node_id, slot)
                        if wide_df is not None and not wide_df.empty:
                            filename = f"{type_name}_node{dt.node_id}_slot{slot}.csv"
                            file_data[filename] = wide_df
                            total += 1

            if not file_data:
                self.export_error.emit("没有匹配的数据可导出")
                return

            self.export_started.emit()

            # 创建工作线程
            self._thread = QThread(self)
            self._worker = ExportWorker()
            self._worker.moveToThread(self._thread)

            self._thread.started.connect(
                lambda: self._worker.write_files(str(out_path), file_data)
            )
            self._worker.write_finished.connect(self._on_write_finished)
            self._worker.write_error.connect(self._on_write_error)
            self._worker.write_finished.connect(self._thread.quit)
            self._worker.write_error.connect(self._thread.quit)
            self._thread.finished.connect(self._thread.deleteLater)

            self._thread.start()
        except Exception as exc:
            self.export_error.emit(str(exc))

    def _on_write_finished(self, count: int) -> None:
        """导出写入完成回调."""
        self.export_progress.emit(count, count)
        self.export_finished.emit(count)

    def _on_write_error(self, message: str) -> None:
        """导出写入错误回调."""
        self.export_error.emit(message)

    @staticmethod
    def build_wide_table(slot_df: pd.DataFrame,
                          annotations: dict[tuple[str, int], Annotation],
                          node_id: int,
                          slot_id: int) -> Optional[pd.DataFrame]:
        """将窄表 slot 数据转换为宽表训练格式 (V2).

        步骤：
        1. 过滤 RPTREGS 行确保只处理主动上报数据
        2. 按 uptime + (func, tp) pivot
        3. 列重命名为 {name}_{unit}
        4. 计算 DEV 列（actual - target 配对）
        5. 添加 PD_PWR_mW 列（填充 NaN）
        6. 前向填充目标值
        7. 按 uptime 排序

        Args:
            slot_df: 单个 slot 的窄表数据 (V2: 含 func, tp, val_float 列)
            annotations: (func_group, tp) -> Annotation 映射
            node_id: 设备节点 ID
            slot_id: 槽位 ID

        Returns:
            宽表 DataFrame，无数据时返回 None
        """  # 方法文档
        if slot_df.empty:  # 空数据
            return None

        # V2: 入口处过滤 RPTREGS
        slot_df = slot_df[~slot_df["func"].isin(EXCLUDED_FUNC_GROUPS)]  # 只有主动上报
        if slot_df.empty:
            return None

        # V2: 创建组合键列用于 pivot
        slot_df = slot_df.copy()  # 防止 SettingWithCopyWarning
        slot_df["key"] = list(zip(slot_df["func"], slot_df["tp"]))  # (func, tp) 对作为组合键

        # 步骤1：按 uptime + (func, tp) pivot
        pivot_df = slot_df.pivot_table(
            index="uptime",
            columns="key",
            values="val_float",  # V2: val_float 替代 val
            aggfunc="first",
        ).reset_index()

        # 步骤2：按标注重命名列
        rename_map: dict[tuple[str, int], str] = {}  # (func, tp) -> 新列名
        for key, ann in annotations.items():  # key 已经是 (func, tp)
            if key in pivot_df.columns:  # 该组合键在 pivot 列中
                col_name = f"{ann.name}_{ann.unit}" if ann.unit else ann.name
                rename_map[key] = col_name
        pivot_df = pivot_df.rename(columns=rename_map)

        # 步骤3：计算 DEV 列（actual - target 配对）(V2: 基于数据类型配对)
        actual_items: list[tuple[str, str, str]] = []  # [(col_name, ann_name, unit), ...]
        target_items: list[tuple[str, str, str]] = []  # [(col_name, ann_name, unit), ...]
        for key, ann in annotations.items():
            if key not in rename_map:
                continue
            col_name = rename_map[key]
            if ann.data_type == DataType.ACTUAL:
                actual_items.append((col_name, ann.name, ann.unit))
            elif ann.data_type == DataType.TARGET:
                target_items.append((col_name, ann.name, ann.unit))

        # 配对策略：优先名称匹配（ACTUAL→TARGET），否则同 slot 内一一配对
        for act_col, act_name, act_unit in actual_items:
            from laser_daq.models.annotation import QuantityCatalog
            matched_tgt = None  # 匹配的目标列名
            # 先尝试名称约定匹配
            target_hint = QuantityCatalog.target_for_actual(act_name)
            if target_hint:
                for tgt_col, tgt_name, tgt_unit in target_items:
                    if tgt_name == target_hint:  # 精确匹配 target 名称
                        matched_tgt = tgt_col
                        break
            # 若未匹配，取第一个可用的 target
            if matched_tgt is None and target_items:
                matched_tgt = target_items[0][0]  # 取第一个目标值列

            if matched_tgt and matched_tgt in pivot_df.columns:
                dev_name = act_name.replace("ACTUAL", "DEV")
                dev_col = f"{dev_name}_{act_unit}" if act_unit else dev_name
                pivot_df[dev_col] = pivot_df[act_col] - pivot_df[matched_tgt].ffill()

        # 步骤4：添加 PD_PWR_mW 列（NaN）
        pd_pwr_col = f"{PD_PWR_NAME}_{PD_PWR_UNIT}"
        pivot_df[pd_pwr_col] = float("nan")

        # 步骤5：前向填充所有目标值列
        for tgt_col, _, _ in target_items:
            if tgt_col in pivot_df.columns:
                pivot_df[tgt_col] = pivot_df[tgt_col].ffill()

        # 步骤6：添加 node_id 列，按 uptime 排序
        pivot_df["node_id"] = node_id
        pivot_df = pivot_df.sort_values("uptime").reset_index(drop=True)

        # 调整列顺序：uptime, node_id 放前面
        cols = ["uptime", "node_id"] + [c for c in pivot_df.columns
                                         if c not in ("uptime", "node_id")]
        return pivot_df[cols]
