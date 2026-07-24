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

    def set_data_model(self, model: DataModel) -> None:
        """更新数据模型引用（导入完成后由 MainWindow 调用）.

        Args:
            model: 新的 DataModel 实例
        """  # 方法文档
        self._model = model  # 更新引用

    def export(self, output_dir: object, selected_types: object, merge_all: bool = False) -> None:
        """导出每种设备类型的宽表 CSV (V2).

        Args:
            output_dir: 输出目录（str 或 Path）
            selected_types: 要导出的设备类型名称列表
            merge_all: True 时合并同一设备类型所有 slot 为单文件（按 uptime 对齐）
        """  # 方法文档
        if self._model.raw_df.empty:  # 无数据
            self.export_error.emit("没有数据可以导出，请先导入 CSV")
            return

        # ---- 清理上一次的线程和 worker ----
        # 旧线程已完成时通过 finished→deleteLater 自清理
        # 此处只断开 Python 引用，不访问 C++ 对象（可能已被 Qt 销毁）
        self._thread = None  # 释放旧线程引用
        self._worker = None  # 释放旧 worker 引用

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

            # 合并模式：同一设备类型所有 slot 按 uptime 合并为单文件
            if merge_all and file_data:  # 需要合并且有数据
                file_data = self._merge_slot_files(file_data)  # 按设备类型合并

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

        # 步骤1：按 sample_seq + (func, tp) pivot（V3: sample_seq 替代 uptime 做对齐主键）
        pivot_df = slot_df.pivot_table(
            index="sample_seq",
            columns="key",
            values="val_float",
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

        # 配对策略：优先名称匹配（ACTUAL→TARGET），否则按顺序一一配对
        available_targets: list[tuple[str, str, str]] = list(target_items)  # 可消耗的目标列表
        for act_col, act_name, act_unit in actual_items:
            from laser_daq.models.annotation import QuantityCatalog
            matched_tgt = None  # 匹配的目标列名
            # 先尝试名称约定匹配
            target_hint = QuantityCatalog.target_for_actual(act_name)
            if target_hint:
                for i, (tgt_col, tgt_name, tgt_unit) in enumerate(available_targets):  # 带索引遍历
                    if tgt_name == target_hint:  # 精确匹配 target 名称
                        matched_tgt = available_targets.pop(i)[0]  # 取出并移除已匹配项
                        break
            # 若未匹配，取第一个可用的 target 并移除
            if matched_tgt is None and available_targets:
                matched_tgt = available_targets.pop(0)[0]  # 取第一个并从列表移除

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

        # 步骤6：添加 node_id 列和 uptime_avg（V3: 附该 sample_seq 的平均时间）
        pivot_df["node_id"] = node_id  # 设备 ID
        if "uptime" in slot_df.columns:  # 原始数据含 uptime（V3 格式在最后一列）
            ts = slot_df.groupby("sample_seq")["uptime"].mean().reset_index()  # 按 sample_seq 取平均时间
            ts.rename(columns={"uptime": "uptime_avg"}, inplace=True)  # 重命名
            pivot_df = pivot_df.merge(ts, on="sample_seq", how="left")  # 关联时间
        pivot_df = pivot_df.sort_values("sample_seq").reset_index(drop=True)  # 按 sample_seq 排序

        # 调整列顺序：sample_seq, node_id 放前面
        cols = ["sample_seq", "node_id"] + [c for c in pivot_df.columns
                                         if c not in ("sample_seq", "node_id")]
        return pivot_df[cols]

    @staticmethod
    def _merge_slot_files(file_data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """将同一设备类型的所有 slot 按 uptime 合并为单文件.

        列名添加 _n{node_id}_s{slot} 后缀以区分来源.

        Args:
            file_data: 原始文件名 -> DataFrame 映射（如 "Laser_node2_slot0.csv" -> df）

        Returns:
            合并后的文件名 -> DataFrame 映射（如 "Laser.csv" -> merged_df）
        """  # 方法文档
        import re  # 正则解析文件名

        # 按设备类型分组收集
        type_groups: dict[str, list[tuple[int, int, pd.DataFrame]]] = {}  # type_name -> [(node_id, slot, df)]
        pattern = re.compile(r"^(.+)_node(\d+)_slot(\d+)\.csv$")  # 解析 "TypeName_nodeX_slotY.csv"

        for filename, df in file_data.items():  # 遍历所有文件
            m = pattern.match(filename)  # 匹配文件名格式
            if not m:  # 不匹配时跳过（保留原样）
                type_groups.setdefault("_other", []).append((0, 0, df))  # 归入 other
                continue  # 下一个
            type_name = m.group(1)  # 设备类型名
            node_id = int(m.group(2))  # 节点 ID
            slot = int(m.group(3))  # 槽位
            type_groups.setdefault(type_name, []).append((node_id, slot, df))  # 收集

        result: dict[str, pd.DataFrame] = {}  # 合并结果

        for type_name, items in type_groups.items():  # 遍历每种设备类型
            if type_name == "_other":  # 不匹配的文件保留原样
                for _, _, df in items:  # 重新放回（理论上不会到这里）
                    pass  # 跳过
                continue  # 下一个类型

            # 按 sample_seq 逐步合并（V3: 同批次精确对齐）
            merged: pd.DataFrame | None = None  # 累积合并结果
            for node_id, slot, df in items:  # 遍历该类型所有 slot
                suffix = f"_n{node_id}_s{slot}"  # 列后缀
                # 重命名非公用列
                rename: dict[str, str] = {}  # 原列名 -> 新列名
                for col in df.columns:  # 遍历所有列
                    if col in ("sample_seq", "node_id"):  # 公用对齐列，跳过
                        continue  # 不重命名
                    rename[col] = f"{col}{suffix}"  # 添加后缀
                df_renamed = df.rename(columns=rename)  # 重命名
                # 删除 node_id 和 uptime_avg 列（合并后无意义，且多节点合并会列名冲突）
                for drop_col in ("node_id", "uptime_avg"):  # 需删除的列
                    if drop_col in df_renamed.columns:  # 列存在
                        df_renamed = df_renamed.drop(columns=[drop_col])  # 删除

                if merged is None:  # 第一个 DataFrame
                    merged = df_renamed  # 直接赋值
                else:  # 后续 DataFrame
                    merged = pd.merge(merged, df_renamed, on="sample_seq", how="outer")  # V3: 按 sample_seq 外连接

            if merged is not None and not merged.empty:  # 合并成功
                merged = merged.sort_values("sample_seq").reset_index(drop=True)  # V3: 按 sample_seq 排序
                result[f"{type_name}.csv"] = merged  # 存入结果

        return result if result else file_data  # 有合并结果则返回，否则返回原数据
