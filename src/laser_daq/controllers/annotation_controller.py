"""管理标注 CRUD 和跨 slot 匹配."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtCore import QObject, pyqtSignal  # Qt 基类和信号

from laser_daq.models.data_model import DataModel  # 数据模型
from laser_daq.models.annotation import Annotation  # 标注


class AnnotationController(QObject):
    """标注操作的统一入口.

    Signals:
        annotation_updated(node_id, slot, tc): 单个标注已更新
        batch_applied(count): 批量应用完成
    """  # 类文档

    annotation_updated = pyqtSignal(int, int, int)  # node_id, slot, tc
    batch_applied = pyqtSignal(int)  # 批量应用数量

    def __init__(self, data_model: DataModel, parent: QObject = None) -> None:
        """初始化 AnnotationController.

        Args:
            data_model: 共享的 DataModel 实例
            parent: Qt 父对象
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._model: DataModel = data_model  # 持有数据模型引用

    def update_annotation(self, node_id: int, slot: int, tc: int,
                          annotation: object) -> None:
        """应用单个标注更新.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            tc: typecode 值
            annotation: Annotation 实例
        """  # 方法文档
        self._model.set_annotation(node_id, slot, tc, annotation)  # 存入数据模型
        self.annotation_updated.emit(node_id, slot, tc)  # 发射更新信号

    def apply_to_all_matching(self, node_id: int, slot: int, tc: int,
                               annotation: object) -> None:
        """查找所有 tc 值相同的 (n, s, tc) 并应用标注.

        用于 UI 中的 "Apply to All Matching" 按钮.

        Args:
            node_id: 当前设备节点 ID（用于获取 tc 值）
            slot: 当前槽位（用于获取 tc 值）
            tc: typecode 值（匹配条件）
            annotation: Annotation 实例（将覆盖 node_id/slot 为各匹配项的值）
        """  # 方法文档
        if self._model.raw_df.empty:  # 无数据
            self.batch_applied.emit(0)  # 发射 0 计数
            return  # 返回

        # 查找数据中所有 tc 值相同的行
        mask = self._model.raw_df["tc"] == tc  # 筛选同 tc 的行
        matching = self._model.raw_df.loc[mask, ["node_id", "slot", "tc"]]  # 获取匹配行
        unique_combos = matching.drop_duplicates()  # 去重

        count: int = 0  # 应用计数
        for _, row in unique_combos.iterrows():  # 遍历每个唯一组合
            n = int(row["node_id"])  # node_id
            s = int(row["slot"])  # slot
            t = int(row["tc"])  # tc
            # 创建新 Annotation，复制用户设置但使用当前行的 node_id 和 slot
            new_ann = Annotation(  # 构造新标注
                node_id=n,  # 使用当前 node_id
                slot=s,  # 使用当前 slot
                tc=t,  # 使用当前 tc
                name=annotation.name,  # 复制名称
                unit=annotation.unit,  # 复制单位
                data_type=annotation.data_type,  # 复制数据类型
                include_in_training=annotation.include_in_training,  # 复制训练标记
            )  # 完成
            self._model.set_annotation(n, s, t, new_ann)  # 存入数据模型
            count += 1  # 计数加一

        self.batch_applied.emit(count)  # 发射批量完成信号
