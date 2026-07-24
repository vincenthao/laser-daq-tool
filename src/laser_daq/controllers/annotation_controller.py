"""管理标注 CRUD 和跨 slot 匹配 (V2)."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtCore import QObject, pyqtSignal  # Qt 基类和信号

from laser_daq.models.data_model import DataModel  # 数据模型
from laser_daq.models.annotation import Annotation  # 标注


class AnnotationController(QObject):
    """标注操作的统一入口 (V2: 键含 func_group).

    Signals:
        annotation_updated(node_id, slot, func_group, tp): 单个标注已更新
        batch_applied(count): 批量应用完成
    """  # 类文档

    annotation_updated = pyqtSignal(int, int, str, int)  # V2: node_id, slot, func_group, tp
    batch_applied = pyqtSignal(int)  # 批量应用数量

    def __init__(self, data_model: DataModel, parent: QObject = None) -> None:
        """初始化 AnnotationController.

        Args:
            data_model: 共享的 DataModel 实例
            parent: Qt 父对象
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._model: DataModel = data_model  # 持有数据模型引用

    def update_annotation(self, node_id: int, slot: int, func_group: str, tp: int,
                          annotation: object) -> None:
        """应用单个标注更新 (V2: 新增 func_group 参数).

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            func_group: 功能组 ("RPTCURR", "RPTTEMP")
            tp: 类型码值
            annotation: Annotation 实例
        """  # 方法文档
        self._model.set_annotation(node_id, slot, func_group, tp, annotation)  # 存入数据模型
        self.annotation_updated.emit(node_id, slot, func_group, tp)  # 发射更新信号

    def apply_to_all_matching(self, node_id: int, slot: int, func_group: str, tp: int,
                               annotation: object) -> None:
        """查找所有 (func_group, tp) 相同的条目并应用标注.

        用于 UI 中的 "Apply to All Matching" 按钮.

        Args:
            node_id: 当前设备节点 ID
            slot: 当前槽位
            func_group: 当前功能组（匹配条件）
            tp: 类型码值（匹配条件）
            annotation: Annotation 实例（将覆盖 node_id/slot 为各匹配项的值）
        """  # 方法文档
        if self._model.raw_df.empty:  # 无数据
            self.batch_applied.emit(0)
            return

        # 查找同一设备中所有 (func_group, tp) 相同的行（限定 node_id，不同设备物理含义不同）
        mask = ((self._model.raw_df["node_id"] == node_id) &
                (self._model.raw_df["func"] == func_group) &
                (self._model.raw_df["tp"] == tp))
        matching = self._model.raw_df.loc[mask, ["node_id", "slot", "func", "tp"]]
        unique_combos = matching.drop_duplicates()

        count: int = 0  # 应用计数
        for _, row in unique_combos.iterrows():  # 遍历每个唯一组合
            n = int(row["node_id"])
            s = int(row["slot"])
            fg = str(row["func"])
            t = int(row["tp"])
            new_ann = Annotation(
                node_id=n, slot=s, func_group=fg, tp=t,
                name=annotation.name,
                unit=annotation.unit,
                data_type=annotation.data_type,
                include_in_training=annotation.include_in_training,
            )
            self._model.set_annotation(n, s, fg, t, new_ann)
            count += 1

        self.batch_applied.emit(count)  # 发射批量完成信号
