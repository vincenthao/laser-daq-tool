"""设备树视图 — 三级结构：DeviceType -> Slot -> TC."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtWidgets import QTreeView, QWidget  # Qt 控件
from PyQt6.QtCore import pyqtSignal, QModelIndex, Qt  # Qt 核心
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon, QColor, QPixmap, QPainter  # Qt GUI
import pandas as pd  # 数据处理库

from laser_daq.models.device_type import DeviceType  # 设备类型
from laser_daq.models.annotation import Annotation  # 标注


class DeviceTree(QTreeView):
    """三级树控件：DeviceType → Slot → TC.

    Signals:
        selection_changed(node_id, slot, tc): 选中了 TC 叶子节点
    """  # 类文档

    selection_changed = pyqtSignal(int, int, int)  # node_id, slot, tc

    def __init__(self, parent: QWidget = None) -> None:
        """初始化 DeviceTree.

        Args:
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._model: QStandardItemModel = QStandardItemModel(self)  # 标准项模型
        self._model.setHorizontalHeaderLabels(["设备 / Slot / TC"])  # 单列表头
        self.setModel(self._model)  # 设置模型
        self.setIndentation(16)  # 缩进
        self.setHeaderHidden(False)  # 显示表头
        self.setAnimated(True)  # 启用展开动画
        self.selectionModel().currentChanged.connect(self._on_current_changed)  # 选择变化

    def set_devices(self,
                    device_types: dict[int, DeviceType],
                    annotations: dict[tuple[int, int, int], Annotation],
                    raw_df: pd.DataFrame) -> None:
        """根据当前数据状态重建树.

        Args:
            device_types: node_id -> DeviceType 映射
            annotations: (node_id, slot, tc) -> Annotation 映射
            raw_df: 原始窄表 DataFrame
        """  # 方法文档
        self._model.clear()  # 清空模型
        self._model.setHorizontalHeaderLabels(["设备 / Slot / TC"])  # 重置表头

        if not device_types:  # 无设备
            return  # 返回空树

        # 按设备类型名称分组
        type_groups: dict[str, list[DeviceType]] = {}  # 分组字典
        for dt in device_types.values():  # 遍历设备
            type_groups.setdefault(dt.name, []).append(dt)  # 按名称分组

        for type_name, devices in sorted(type_groups.items()):  # 遍历每种类型
            # 类型级别项
            type_item = QStandardItem(f"{type_name}")  # 类型项
            type_item.setEditable(False)  # 不可编辑
            type_item.setData("type", Qt.ItemDataRole.UserRole)  # 标记类型
            bold_font = type_item.font()  # 获取字体
            bold_font.setBold(True)  # 加粗
            type_item.setFont(bold_font)  # 设置字体
            self._model.appendRow(type_item)  # 添加到根

            for dt in sorted(devices, key=lambda d: d.node_id):  # 按 node_id 排序
                # 设备级别项
                device_item = QStandardItem(  # 设备项
                    f"设备 {dt.node_id} — {dt.name}"  # 显示 node_id 和类型名
                )  # 设备标签
                device_item.setEditable(False)  # 不可编辑
                device_item.setData(("device", dt.node_id), Qt.ItemDataRole.UserRole)  # 存储类型 + node_id
                type_item.appendRow(device_item)  # 添加到类型下

                # 获取此设备的 slot 数据
                node_df = raw_df[raw_df["node_id"] == dt.node_id]  # 筛选数据
                slots_in_data = sorted(node_df["slot"].unique())  # 数据中的 slot

                for slot in slots_in_data:  # 遍历每个 slot
                    slot_item = QStandardItem(f"Slot {slot}")  # Slot 项
                    slot_item.setEditable(False)  # 不可编辑
                    slot_item.setData(("slot", dt.node_id, slot), Qt.ItemDataRole.UserRole)  # 存储信息
                    device_item.appendRow(slot_item)  # 添加到设备下

                    # 获取此 slot 的 tc 数据
                    slot_df = node_df[node_df["slot"] == slot]  # 筛选 slot 数据
                    for tc in sorted(slot_df["tc"].unique()):  # 遍历唯一 TC
                        tc_item = QStandardItem()  # TC 项
                        tc_item.setEditable(False)  # 不可编辑
                        tc_item.setData((dt.node_id, slot, tc), Qt.ItemDataRole.UserRole)  # 存储键

                        # 查找标注
                        ann = annotations.get((dt.node_id, slot, tc))  # 获取标注
                        if ann:  # 有标注
                            tc_item.setText(f"tc={tc} — {ann.name} ({ann.unit})")  # 显示标注信息
                            if ann.include_in_training:  # 纳入训练
                                tc_item.setIcon(_make_icon(QColor("#27ae60")))  # 绿色圆
                            else:  # 不纳入
                                tc_item.setIcon(_make_icon(QColor("#f39c12")))  # 橙色圆
                        else:  # 未标注
                            tc_item.setText(f"tc={tc}")  # 仅显示 tc
                            tc_item.setIcon(_make_icon(QColor("#e74c3c")))  # 红色圆（需标注）

                        slot_item.appendRow(tc_item)  # 添加到 slot 下

        self.expandAll()  # 展开所有节点

    def _on_current_changed(self, current: QModelIndex,
                            previous: QModelIndex) -> None:
        """当前选中项变化 — 如果是 TC 叶子则发射 selection_changed.

        Args:
            current: 当前选中索引
            previous: 之前选中索引
        """  # 方法文档
        if not current.isValid():  # 无效选择
            return  # 不处理
        item: QStandardItem = self._model.itemFromIndex(current)  # 获取项
        data = item.data(Qt.ItemDataRole.UserRole)  # 获取用户数据
        if isinstance(data, tuple) and len(data) == 3:  # TC 叶子节点
            if isinstance(data[0], int):  # 确认是 (node_id, slot, tc)
                self.selection_changed.emit(data[0], data[1], data[2])  # 发射信号


def _make_icon(color: QColor, size: int = 10) -> QIcon:
    """生成纯色圆形图标.

    Args:
        color: 圆的颜色
        size: 图像尺寸（像素）

    Returns:
        纯色圆 QIcon
    """  # 工具函数文档
    pixmap = QPixmap(size, size)  # 创建位图
    pixmap.fill(Qt.GlobalColor.transparent)  # 透明背景
    painter = QPainter(pixmap)  # 创建画笔
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 抗锯齿
    painter.setBrush(color)  # 设置画刷颜色
    painter.setPen(Qt.PenStyle.NoPen)  # 无边框
    painter.drawEllipse(1, 1, size - 2, size - 2)  # 画圆
    painter.end()  # 结束绘制
    return QIcon(pixmap)  # 返回图标
