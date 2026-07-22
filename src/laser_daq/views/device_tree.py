"""设备树视图 (V2) — 三级结构：DeviceType -> Slot -> (func, tp)."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtWidgets import QTreeView, QWidget  # Qt 控件
from PyQt6.QtCore import pyqtSignal, QModelIndex, Qt  # Qt 核心
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon, QColor, QPixmap, QPainter  # Qt GUI
import pandas as pd  # 数据处理库

from laser_daq.models.device_type import DeviceType  # 设备类型
from laser_daq.models.annotation import Annotation  # 标注


class DeviceTree(QTreeView):
    """三级树控件 (V2)：DeviceType → Slot → (func, tp).

    Signals:
        selection_changed(node_id, slot, func_group, tp): 选中了叶子节点
    """  # 类文档

    selection_changed = pyqtSignal(int, int, str, int)  # V2: node_id, slot, func_group, tp

    def __init__(self, parent: QWidget = None) -> None:
        """初始化 DeviceTree.

        Args:
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._model: QStandardItemModel = QStandardItemModel(self)  # 标准项模型
        self._model.setHorizontalHeaderLabels(["设备 / Slot / (func, tp)"])  # V2 表头
        self.setModel(self._model)  # 设置模型
        self.setIndentation(16)  # 缩进
        self.setHeaderHidden(False)  # 显示表头
        self.setAnimated(True)  # 启用展开动画
        self.selectionModel().currentChanged.connect(self._on_current_changed)  # 选择变化

    def set_devices(self,
                    device_types: dict[int, DeviceType],
                    annotations: dict[tuple[int, int, str, int], Annotation],
                    raw_df: pd.DataFrame) -> None:
        """根据当前数据状态重建树.

        直接从 raw_df 读取 node_id/slot/func/tp，不显示设备类型推测.

        Args:
            device_types: 保留参数兼容，但不在树中显示
            annotations: (node_id, slot, func_group, tp) -> Annotation 映射
            raw_df: 原始窄表 DataFrame
        """  # 方法文档
        self._model.clear()  # 清空模型
        self._model.setHorizontalHeaderLabels(["设备 / Slot / (func, tp)"])  # 表头

        if raw_df.empty:  # 无数据
            return  # 返回空树

        # 直接从数据读取 node_id 列表
        node_ids = sorted(raw_df["node_id"].unique())  # 所有唯一 node_id

        for node_id in node_ids:  # 遍历每个设备
            node_id_int = int(node_id)  # 确保 int 类型
            node_df = raw_df[raw_df["node_id"] == node_id_int]  # 该设备数据

            # 设备级别项（直接显示 node_id，不做类型推测）
            device_item = QStandardItem(f"设备 {node_id_int}")  # 简洁标识
            device_item.setEditable(False)  # 不可编辑
            device_item.setData(("device", node_id_int), Qt.ItemDataRole.UserRole)  # 存储数据
            bold_font = device_item.font()  # 获取字体
            bold_font.setBold(True)  # 加粗
            device_item.setFont(bold_font)  # 设置字体
            self._model.appendRow(device_item)  # 直接添加到根

            slots_in_data = sorted(node_df["slot"].unique())  # 该设备的 slot 列表

            for slot in slots_in_data:  # 遍历每个 slot
                slot_int = int(slot)  # 确保 int 类型
                slot_item = QStandardItem(f"Slot {slot_int}")  # Slot 项
                slot_item.setEditable(False)  # 不可编辑
                slot_item.setData(("slot", node_id_int, slot_int), Qt.ItemDataRole.UserRole)
                device_item.appendRow(slot_item)  # 添加到设备下

                # 获取此 slot 的 (func, tp) 组合
                slot_df = node_df[node_df["slot"] == slot_int]  # 筛选 slot 数据
                tp_pairs = list(slot_df.groupby(["func", "tp"]).size().index)  # 去重 (func, tp) 对
                for func_group, tp_val in sorted(tp_pairs, key=lambda x: (x[0], x[1])):  # 排序
                    tp_val_int = int(tp_val)  # 确保 int 类型
                    tp_item = QStandardItem()  # 叶子项
                    tp_item.setEditable(False)  # 不可编辑
                    tp_item.setData((node_id_int, slot_int, func_group, tp_val_int),
                                  Qt.ItemDataRole.UserRole)  # 四元组

                    # 查找标注
                    ann = annotations.get((node_id_int, slot_int, func_group, tp_val_int))
                    if ann:  # 有标注
                        tp_item.setText(f"{func_group} tp={tp_val_int} — {ann.name} ({ann.unit})")
                        if ann.include_in_training:  # 纳入训练
                            tp_item.setIcon(_make_icon(QColor("#27ae60")))  # 绿色圆
                        else:  # 不纳入
                            tp_item.setIcon(_make_icon(QColor("#f39c12")))  # 橙色圆
                    else:  # 未标注
                        tp_item.setText(f"{func_group} tp={tp_val_int}")
                        tp_item.setIcon(_make_icon(QColor("#e74c3c")))  # 红色圆

                    slot_item.appendRow(tp_item)  # 添加到 slot 下

        self.expandAll()  # 展开所有节点

    def _on_current_changed(self, current: QModelIndex,
                            previous: QModelIndex) -> None:
        """当前选中项变化 (V2) — 如果是叶子则发射 selection_changed.

        Args:
            current: 当前选中索引
            previous: 之前选中索引
        """  # 方法文档
        if not current.isValid():
            return
        item: QStandardItem = self._model.itemFromIndex(current)
        data = item.data(Qt.ItemDataRole.UserRole)
        # V2: 四元组 (node_id, slot, func_group, tp)
        if isinstance(data, tuple) and len(data) == 4 and isinstance(data[0], int):
            self.selection_changed.emit(data[0], data[1], data[2], data[3])


def _make_icon(color: QColor, size: int = 10) -> QIcon:
    """生成纯色圆形图标.

    Args:
        color: 圆的颜色
        size: 图像尺寸（像素）

    Returns:
        纯色圆 QIcon
    """  # 工具函数文档
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return QIcon(pixmap)
