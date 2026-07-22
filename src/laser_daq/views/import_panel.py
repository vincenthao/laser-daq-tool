"""拖拽区域和浏览按钮 — CSV 导入入口."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型

from PyQt6.QtWidgets import (  # Qt 控件
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,  # 布局和控件
)  # 导入
from PyQt6.QtCore import pyqtSignal, Qt  # 信号和 Qt 常量
from PyQt6.QtGui import QDragEnterEvent, QDropEvent  # 拖拽事件类型


class DropArea(QLabel):
    """自定义 QLabel，接受文件拖拽事件.

    Signals:
        files_dropped(paths): 拖拽了 CSV 文件
    """  # 类文档

    files_dropped = pyqtSignal(object)  # list[Path]

    def __init__(self, parent: QWidget = None) -> None:
        """初始化 DropArea.

        Args:
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self.setAcceptDrops(True)  # 启用拖拽接受
        self.setText("拖拽 CSV 文件到此处\n或点击下方按钮浏览")  # 提示文本
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 居中对齐
        self.setMinimumHeight(120)  # 最小高度
        self.setStyleSheet(  # 样式
            "QLabel { border: 2px dashed #999; border-radius: 8px; "
            "padding: 20px; background: #f5f5f5; color: #666; font-size: 13px; }"
        )  # 虚线边框样式

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """拖拽进入事件 — 接受包含 URL 的拖拽.

        Args:
            event: 拖拽进入事件
        """  # 事件文档
        if event.mimeData().hasUrls():  # 包含文件 URL
            event.acceptProposedAction()  # 接受拖拽
            self.setStyleSheet(  # 高亮样式
                "QLabel { border: 2px dashed #4a90d9; border-radius: 8px; "
                "padding: 20px; background: #e8f0fe; color: #333; font-size: 13px; }"
            )  # 蓝色高亮虚线边框

    def dragLeaveEvent(self, event) -> None:
        """拖拽离开事件 — 恢复默认样式.

        Args:
            event: 拖拽离开事件
        """  # 事件文档
        self.setStyleSheet(  # 恢复默认样式
            "QLabel { border: 2px dashed #999; border-radius: 8px; "
            "padding: 20px; background: #f5f5f5; color: #666; font-size: 13px; }"
        )  # 灰色虚线边框

    def dropEvent(self, event: QDropEvent) -> None:
        """放下事件 — 提取 CSV 文件路径并发射信号.

        Args:
            event: 放下事件
        """  # 事件文档
        self.setStyleSheet(  # 恢复默认样式
            "QLabel { border: 2px dashed #999; border-radius: 8px; "
            "padding: 20px; background: #f5f5f5; color: #666; font-size: 13px; }"
        )  # 灰色虚线边框

        paths: list[Path] = [  # 提取所有文件路径
            Path(u.toLocalFile()) for u in event.mimeData().urls()  # URL 转本地路径
        ]  # 路径列表
        csv_paths: list[Path] = [p for p in paths
                                  if p.suffix.lower() == ".csv"]  # 只保留 CSV
        if csv_paths:  # 有 CSV 文件
            self.files_dropped.emit(csv_paths)  # 发射信号


class ImportPanel(QWidget):
    """左侧面板 — DropArea + 浏览按钮.

    Signals:
        file_dropped(paths): 用户选择了 CSV 文件
    """  # 类文档

    file_dropped = pyqtSignal(object)  # list[Path]

    def __init__(self, parent: QWidget = None) -> None:
        """初始化 ImportPanel.

        Args:
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        layout: QVBoxLayout = QVBoxLayout(self)  # 垂直布局
        layout.setContentsMargins(8, 8, 8, 8)  # 边距

        # 标题
        title_label: QLabel = QLabel("导入数据", self)  # 标题标签
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")  # 加粗标题
        layout.addWidget(title_label)  # 添加标题

        # 拖拽区域
        self._drop_area: DropArea = DropArea(self)  # 创建拖拽区
        layout.addWidget(self._drop_area)  # 添加拖拽区

        # 浏览按钮
        self._browse_btn: QPushButton = QPushButton("浏览 CSV 文件...", self)  # 浏览按钮
        layout.addWidget(self._browse_btn)  # 添加按钮

        layout.addStretch()  # 底部弹性空间

        # 内部信号接线
        self._drop_area.files_dropped.connect(self.file_dropped)  # 拖拽转发
        self._browse_btn.clicked.connect(self._on_browse)  # 浏览按钮

    def _on_browse(self) -> None:
        """打开 QFileDialog 选择 CSV 文件."""
        paths, _ = QFileDialog.getOpenFileNames(  # 多文件选择对话框
            self, "选择 CSV 文件", "",  # 标题和默认路径
            "CSV 文件 (*.csv);;所有文件 (*)",  # 过滤
        )  # 文件对话框
        if paths:  # 用户选择了文件
            self.file_dropped.emit([Path(p) for p in paths])  # 发射信号
