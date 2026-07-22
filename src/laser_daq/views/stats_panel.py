"""统计摘要面板 — V0.1 占位，V0.3 完整实现."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget  # Qt 控件
from PyQt6.QtCore import Qt  # Qt 常量


class StatsPanel(QWidget):
    """显示选中 (node_id, slot) 的摘要统计.

    V0.1 仅显示占位，V0.3 实现均值/方差/最大偏差/数据点数/时间跨度.
    """  # 类文档

    def __init__(self, parent: QWidget = None) -> None:
        """初始化 StatsPanel.

        Args:
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        layout: QVBoxLayout = QVBoxLayout(self)  # 垂直布局

        # 提示标签
        self._info_label: QLabel = QLabel("选择设备/Slot 后显示统计摘要")  # 提示
        self._info_label.setStyleSheet("color: #333; font-weight: bold; font-size: 12px;")  # 加粗
        layout.addWidget(self._info_label)  # 添加提示

        # 统计表格
        self._table: QTableWidget = QTableWidget(0, 6)  # 0行6列
        self._table.setHorizontalHeaderLabels(  # 表头
            ["物理量", "均值", "标准差", "最大偏差", "数据点数", "时间跨度"]  # 6 列
        )  # 设置表头
        self._table.horizontalHeader().setStretchLastSection(True)  # 最后一列拉伸
        self._table.setAlternatingRowColors(True)  # 交替行颜色
        layout.addWidget(self._table)  # 添加表格

        # 占位文字
        placeholder: QLabel = QLabel("统计摘要 — V0.3 实现", self)  # 占位
        placeholder.setStyleSheet("color: #999; font-size: 14px;")  # 灰色
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 居中
        layout.addWidget(placeholder)  # 添加占位

    def update_for_selection(self, node_id: int, slot: int,
                              func_group: str = "", tp: int = 0) -> None:
        """根据设备树选择更新统计（V0.3 实现）.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            func_group: 功能组 (V2)
            tp: 类型码 (V2)
        """  # 方法文档
        # V0.2 中为 no-op，留待 V0.3 实现
        pass  # 占位
