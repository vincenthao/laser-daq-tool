"""宽表 CSV 导出 — 按设备类型分组."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型
from typing import Optional  # 可选类型

from PyQt6.QtCore import QObject, pyqtSignal, QThread  # Qt 核心类
import pandas as pd  # 数据处理库

from laser_daq.models.data_model import DataModel  # 数据模型
from laser_daq.models.annotation import Annotation  # 标注
from laser_daq.constants import DataType, PD_PWR_NAME, PD_PWR_UNIT  # 常量
from laser_daq.workers.export_worker import ExportWorker  # 导出工作线程


class ExportController(QObject):
    """管理训练集 CSV 的导出.

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
        """导出每种设备类型的宽表 CSV.

        Args:
            output_dir: 输出目录（str 或 Path）
            selected_types: 要导出的设备类型名称列表
        """  # 方法文档
        if self._model.raw_df.empty:  # 无数据
            self.export_error.emit("没有数据可以导出，请先导入 CSV")  # 发射错误
            return  # 返回

        try:  # 捕获异常
            out_path = Path(str(output_dir))  # 确保是 Path 对象

            # 解析 selected_types
            types_list: list[str] = []  # 类型列表
            if isinstance(selected_types, list):  # 列表
                types_list = selected_types  # 直接使用
            elif selected_types is not None:  # 其他可迭代类型
                try:  # 尝试转换
                    types_list = list(selected_types)  # 转为列表
                except TypeError:  # 不可迭代
                    pass  # 忽略

            # 构建所有要导出的 (device_type_name, slot) 组合
            file_data: dict[str, pd.DataFrame] = {}  # 文件名 -> DataFrame
            grouped = self._model.get_grouped_devices()  # 按设备类型分组

            total = 0  # 总计数
            for type_name, devices in grouped.items():  # 遍历每种设备类型
                if types_list and type_name not in types_list:  # 用户指定了类型且当前类型不在列表中
                    continue  # 跳过
                for dt in devices:  # 遍历该类型下的设备
                    for slot in sorted(dt.slots):  # 遍历该设备的每个 slot
                        slot_data = self._model.get_slot_data(dt.node_id, slot)  # 获取 slot 数据
                        if slot_data.empty:  # 空 slot
                            continue  # 跳过
                        annotations = self._model.get_annotations_for_slot(dt.node_id, slot)  # 获取标注
                        wide_df = self.build_wide_table(slot_data, annotations, dt.node_id, slot)  # 构建宽表
                        if wide_df is not None and not wide_df.empty:  # 有效宽表
                            filename = f"{type_name}_node{dt.node_id}_slot{slot}.csv"  # 文件名
                            file_data[filename] = wide_df  # 加入导出字典
                            total += 1  # 计数加一

            if not file_data:  # 没有可导出的数据
                self.export_error.emit("没有匹配的数据可导出")  # 发射错误
                return  # 返回

            self.export_started.emit()  # 发射开始信号

            # 创建工作线程
            self._thread = QThread(self)  # 创建 QThread
            self._worker = ExportWorker()  # 创建 ExportWorker
            self._worker.moveToThread(self._thread)  # 移到线程

            # 连接信号
            self._thread.started.connect(  # 线程启动
                lambda: self._worker.write_files(str(out_path), file_data)  # 调用写入
            )  # lambda 捕获路径和数据
            self._worker.file_written.connect(  # 文件写入进度
                lambda p: self.export_progress.emit(  # 转发进度
                    self.export_progress.signal if hasattr(self, '_count') else 0, total  # 计数
                )  # 进度信号
            )  # 文件写入回调
            self._worker.write_finished.connect(self._on_write_finished)  # 写入完成
            self._worker.write_error.connect(self._on_write_error)  # 写入错误
            self._worker.write_finished.connect(self._thread.quit)  # 完成后退出线程
            self._worker.write_error.connect(self._thread.quit)  # 错误后退出线程
            self._thread.finished.connect(self._thread.deleteLater)  # 线程结束后清理

            self._thread.start()  # 启动线程
        except Exception as exc:  # 捕获异常
            self.export_error.emit(str(exc))  # 发射错误

    def _on_write_finished(self, count: int) -> None:
        """导出写入完成回调.

        Args:
            count: 成功写入的文件数
        """  # 方法文档
        self.export_progress.emit(count, count)  # 发射完成进度
        self.export_finished.emit(count)  # 发射完成信号（发射文件数）

    def _on_write_error(self, message: str) -> None:
        """导出写入错误回调.

        Args:
            message: 错误消息
        """  # 方法文档
        self.export_error.emit(message)  # 转发错误

    @staticmethod
    def build_wide_table(slot_df: pd.DataFrame,
                          annotations: dict[int, Annotation],
                          node_id: int,
                          slot_id: int) -> Optional[pd.DataFrame]:
        """将窄表 slot 数据转换为宽表训练格式.

        步骤：
        1. 按 uptime 分组，pivot tc 行为标注名列
        2. 列重命名为 {name}_{unit}
        3. 计算 DEV 列（actual - target 配对）
        4. 添加 PD_PWR_mW 列（填充 NaN）
        5. 前向填充目标值
        6. 按 uptime 排序

        Args:
            slot_df: 单个 slot 的窄表数据（含 uptime, node_id, slot, tc, val）
            annotations: tc -> Annotation 映射
            node_id: 设备节点 ID
            slot_id: 槽位 ID

        Returns:
            宽表 DataFrame，无数据时返回 None
        """  # 方法文档
        if slot_df.empty:  # 空数据
            return None  # 返回 None

        # 步骤1：按 uptime + tc pivot
        pivot_df = slot_df.pivot_table(  # 透视表
            index="uptime",  # 时间索引
            columns="tc",  # tc 作为列
            values="val",  # 值列
            aggfunc="first",  # 同一 uptime+tc 取第一个值
        ).reset_index()  # 重置索引

        # 步骤2：按标注重命名列
        rename_map: dict[int, str] = {}  # tc -> 新列名
        for tc, ann in annotations.items():  # 遍历所有标注
            if tc in pivot_df.columns:  # 该 tc 在 pivot 列中
                col_name = f"{ann.name}_{ann.unit}" if ann.unit else ann.name  # {name}_{unit} 格式
                rename_map[tc] = col_name  # 记录重命名映射
        pivot_df = pivot_df.rename(columns=rename_map)  # 执行重命名

        # 步骤3：计算 DEV 列（actual - target 配对）
        # 收集 actual 和 target 对
        actual_cols: dict[str, str] = {}  # actual_name -> actual_col
        target_cols: dict[str, str] = {}  # target_name -> target_col
        for tc, ann in annotations.items():  # 遍历标注
            if tc not in rename_map:  # 跳过未被 pivot 包含的
                continue
            col_name = rename_map[tc]  # 获取列名
            if ann.data_type == DataType.ACTUAL:  # 实际值
                actual_cols[ann.name] = col_name  # 记录实际值列
            elif ann.data_type == DataType.TARGET:  # 目标值
                target_cols[ann.name] = col_name  # 记录目标值列

        # 对每个 actual，找对应的 target 计算偏差
        for act_name, act_col in actual_cols.items():  # 遍历实际值
            # 查找对应的 target（通过 QuantityCatalog.target_for_actual）
            from laser_daq.models.annotation import QuantityCatalog  # 延迟导入避免循环
            target_name = QuantityCatalog.target_for_actual(act_name)  # 获取目标值名
            if target_name and target_name in target_cols:  # 存在对应 target
                tgt_col = target_cols[target_name]  # 目标值列名
                if tgt_col in pivot_df.columns:  # 目标值列存在
                    # DEV 列名：将 ACTUAL 替换为 DEV
                    dev_name = act_name.replace("ACTUAL", "DEV")  # DEV 列名
                    dev_unit = annotations[  # 获取单位
                        next(t for t, a in annotations.items() if a.name == act_name)
                    ].unit  # 从标注中获取单位
                    dev_col = f"{dev_name}_{dev_unit}" if dev_unit else dev_name  # 完整列名
                    # 前向填充目标值后计算偏差
                    pivot_df[dev_col] = pivot_df[act_col] - pivot_df[tgt_col].ffill()  # actual - target(ffill)

        # 步骤4：添加 PD_PWR_mW 列（NaN）
        pd_pwr_col = f"{PD_PWR_NAME}_{PD_PWR_UNIT}"  # PD_PWR_mW
        pivot_df[pd_pwr_col] = float("nan")  # 全部填充 NaN

        # 步骤5：前向填充所有目标值列
        for tgt_col in target_cols.values():  # 遍历所有目标值列
            if tgt_col in pivot_df.columns:  # 列存在
                pivot_df[tgt_col] = pivot_df[tgt_col].ffill()  # 前向填充

        # 步骤6：添加 node_id 列，按 uptime 排序
        pivot_df["node_id"] = node_id  # 添加 node_id 列
        pivot_df = pivot_df.sort_values("uptime").reset_index(drop=True)  # 按 uptime 排序

        # 调整列顺序：uptime, node_id 放前面
        cols = ["uptime", "node_id"] + [c for c in pivot_df.columns
                                         if c not in ("uptime", "node_id")]  # 重新排列
        return pivot_df[cols]  # 返回排好序的宽表
