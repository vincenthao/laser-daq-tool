"""导出对话框 — 选择输出目录和设备类型."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型

from PyQt6.QtWidgets import (  # Qt 控件
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,  # 布局和基础控件
    QCheckBox, QGroupBox, QFileDialog, QMessageBox, QDialogButtonBox,  # 对话框相关
    QScrollArea, QWidget,  # 滚动区域
)  # 导入
from PyQt6.QtCore import pyqtSignal, Qt  # 信号和常量


class ExportDialog(QDialog):
    """导出设置对话框.

    Signals:
        export_requested(output_dir, selected_types): 用户确认导出
    """  # 类文档

    export_requested = pyqtSignal(object, object, bool)  # Path, list[str], merge_all_flag

    def __init__(self, device_type_names: list[str], parent: QWidget = None) -> None:
        """初始化 ExportDialog.

        Args:
            device_type_names: 可导出的设备类型名称列表
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self.setWindowTitle("导出训练数据")  # 窗口标题
        self.setMinimumWidth(450)  # 最小宽度
        self.setModal(True)  # 模态对话框

        self._output_dir: Path = Path.home()  # 默认输出目录（用户主目录）

        layout: QVBoxLayout = QVBoxLayout(self)  # 垂直布局

        # 输出目录选择
        dir_group: QGroupBox = QGroupBox("输出目录")  # 目录分组
        dir_layout: QHBoxLayout = QHBoxLayout(dir_group)  # 水平布局
        self._dir_label: QLabel = QLabel(str(self._output_dir), self)  # 目录路径标签
        self._dir_label.setStyleSheet("color: #666;")  # 灰色文字
        self._dir_label.setWordWrap(True)  # 自动换行
        browse_btn: QPushButton = QPushButton("浏览...", self)  # 浏览按钮
        browse_btn.clicked.connect(self._on_browse_dir)  # 连接浏览
        dir_layout.addWidget(self._dir_label, 1)  # 路径标签（弹性）
        dir_layout.addWidget(browse_btn)  # 浏览按钮
        layout.addWidget(dir_group)  # 添加分组

        # 设备类型选择
        type_group: QGroupBox = QGroupBox("选择要导出的设备类型")  # 类型分组
        type_layout: QVBoxLayout = QVBoxLayout(type_group)  # 垂直布局

        # 滚动区域（类型多时）
        scroll = QScrollArea()  # 滚动区域
        scroll.setWidgetResizable(True)  # 内容自适应
        scroll.setMaximumHeight(200)  # 最大高度
        scroll_content = QWidget()  # 滚动内容
        self._type_checkboxes: dict[str, QCheckBox] = {}  # 类型名 -> 勾选框
        cb_layout: QVBoxLayout = QVBoxLayout(scroll_content)  # 勾选框布局

        for name in sorted(device_type_names):  # 遍历每种设备类型
            cb = QCheckBox(name, scroll_content)  # 创建勾选框
            cb.setChecked(True)  # 默认全选
            self._type_checkboxes[name] = cb  # 存入字典
            cb_layout.addWidget(cb)  # 添加到布局

        cb_layout.addStretch()  # 弹性空间
        scroll.setWidget(scroll_content)  # 设置滚动内容
        type_layout.addWidget(scroll)  # 添加滚动区域

        # 全选/全不选按钮
        select_layout: QHBoxLayout = QHBoxLayout()  # 水平布局
        select_all_btn: QPushButton = QPushButton("全选", self)  # 全选按钮
        select_none_btn: QPushButton = QPushButton("全不选", self)  # 全不选按钮
        select_all_btn.clicked.connect(  # 全选回调
            lambda: [cb.setChecked(True) for cb in self._type_checkboxes.values()]  # 全部勾选
        )  # lambda
        select_none_btn.clicked.connect(  # 全不选回调
            lambda: [cb.setChecked(False) for cb in self._type_checkboxes.values()]  # 全部取消
        )  # lambda
        select_layout.addWidget(select_all_btn)  # 添加全选
        select_layout.addWidget(select_none_btn)  # 添加全不选
        select_layout.addStretch()  # 弹性空间
        type_layout.addLayout(select_layout)  # 添加到分组

        layout.addWidget(type_group)  # 添加分组

        # 合并选项
        self._merge_check: QCheckBox = QCheckBox("合并同一设备类型所有 slot 为单文件", self)  # 合并勾选框
        self._merge_check.setToolTip("勾选后按 uptime 合并所有 slot，列名加 _s0/_s1 后缀")  # 提示
        layout.addWidget(self._merge_check)  # 添加合并选项

        # 确认/取消按钮
        button_box: QDialogButtonBox = QDialogButtonBox(  # 标准按钮盒
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,  # 确定+取消
            self,  # 父控件
        )  # 按钮盒
        button_box.accepted.connect(self._on_confirm)  # 确定按钮
        button_box.rejected.connect(self.reject)  # 取消按钮
        layout.addWidget(button_box)  # 添加按钮

    def _on_browse_dir(self) -> None:
        """打开目录选择对话框."""
        dir_path = QFileDialog.getExistingDirectory(  # 目录选择对话框
            self, "选择输出目录", str(self._output_dir),  # 标题和默认路径
        )  # 目录对话框
        if dir_path:  # 用户选择了目录
            self._output_dir = Path(dir_path)  # 更新输出目录
            self._dir_label.setText(str(self._output_dir))  # 更新显示

    def _on_confirm(self) -> None:
        """确认导出 — 验证选择并发射信号."""
        selected = [name for name, cb in self._type_checkboxes.items()
                     if cb.isChecked()]  # 收集勾选的类型

        if not selected:  # 未选择任何类型
            QMessageBox.warning(self, "警告", "请至少选择一种设备类型")  # 警告对话框
            return  # 不关闭对话框

        self.export_requested.emit(self._output_dir, selected, self._merge_check.isChecked())  # 发射导出信号（含合并标志）
        self.accept()  # 关闭对话框
