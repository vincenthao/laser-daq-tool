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
        """根据当前数据状态重建树 (V2).

        Args:
            device_types: node_id -> DeviceType 映射
            annotations: (node_id, slot, func_group, tp) -> Annotation 映射 (V2 key)
            raw_df: 原始窄表 DataFrame (V2: 含 func, tp 列)
        """  # 方法文档
        self._model.clear()  # 清空模型
        self._model.setHorizontalHeaderLabels(["设备 / Slot / (func, tp)"])  # V2 表头

        if not device_types:  # 无设备
            return  # 返回空树

        # 按设备类型名称分组
        type_groups: dict[str, list[DeviceType]] = {}
        for dt in device_types.values():
            type_groups.setdefault(dt.name, []).append(dt)

        for type_name, devices in sorted(type_groups.items()):
            # 类型级别项
            type_item = QStandardItem(f"{type_name}")
            type_item.setEditable(False)
            type_item.setData("type", Qt.ItemDataRole.UserRole)
            bold_font = type_item.font()
            bold_font.setBold(True)
            type_item.setFont(bold_font)
            self._model.appendRow(type_item)

            for dt in sorted(devices, key=lambda d: d.node_id):
                # 设备级别项
                device_item = QStandardItem(
                    f"设备 {dt.node_id} — {dt.name}"
                )
                device_item.setEditable(False)
                device_item.setData(("device", dt.node_id), Qt.ItemDataRole.UserRole)
                type_item.appendRow(device_item)

                # V2: 获取此设备的 slot + func + tp 数据
                node_df = raw_df[raw_df["node_id"] == dt.node_id]
                slots_in_data = sorted(node_df["slot"].unique())

                for slot in slots_in_data:
                    slot_item = QStandardItem(f"Slot {slot}")
                    slot_item.setEditable(False)
                    slot_item.setData(("slot", dt.node_id, slot), Qt.ItemDataRole.UserRole)
                    device_item.appendRow(slot_item)

                    # V2: 获取此 slot 的 (func, tp) 数据
                    slot_df = node_df[node_df["slot"] == slot]
                    # 构建 (func, tp) 对唯一列表
                    tp_pairs = list(slot_df.groupby(["func", "tp"]).size().index)
                    for func_group, tp_val in sorted(tp_pairs, key=lambda x: (x[0], x[1])):
                        tp_item = QStandardItem()
                        tp_item.setEditable(False)
                        # V2: 存储四元组
                        tp_item.setData((dt.node_id, slot, func_group, tp_val),
                                      Qt.ItemDataRole.UserRole)

                        # 查找标注
                        ann = annotations.get((dt.node_id, slot, func_group, tp_val))
                        if ann:  # 有标注
                            tp_item.setText(f"{func_group} tp={tp_val} — {ann.name} ({ann.unit})")
                            if ann.include_in_training:
                                tp_item.setIcon(_make_icon(QColor("#27ae60")))  # 绿色圆
                            else:
                                tp_item.setIcon(_make_icon(QColor("#f39c12")))  # 橙色圆
                        else:  # 未标注
                            tp_item.setText(f"{func_group} tp={tp_val}")
                            tp_item.setIcon(_make_icon(QColor("#e74c3c")))  # 红色圆

                        slot_item.appendRow(tp_item)

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
