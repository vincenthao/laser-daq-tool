"""标注表单 — 每个 TC 的物理量编辑面板."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtWidgets import (  # Qt 控件
    QWidget, QVBoxLayout, QFormLayout, QComboBox, QRadioButton,  # 表单控件
    QButtonGroup, QCheckBox, QPushButton, QGroupBox, QLabel, QHBoxLayout,  # 分组和按钮
)  # 导入
from PyQt6.QtCore import pyqtSignal  # 信号

from laser_daq.models.annotation import Annotation, QuantityCatalog  # 标注模型
from laser_daq.constants import DataType, UNIT_OPTIONS  # 常量


class AnnotationPanel(QWidget):
    """右侧详情面板 — 为单个 TC 提供标注表单.

    Signals:
        annotation_changed(node_id, slot, tc, annotation): 字段值变更
        apply_all_requested(node_id, slot, tc, annotation): 应用到所有匹配项
    """  # 类文档

    annotation_changed = pyqtSignal(int, int, int, object)  # Annotation
    apply_all_requested = pyqtSignal(int, int, int, object)  # Annotation

    def __init__(self, parent: QWidget = None) -> None:
        """初始化 AnnotationPanel.

        Args:
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._current_key: tuple[int, int, int] = (0, 0, 0)  # 当前 (node_id, slot, tc)

        layout: QVBoxLayout = QVBoxLayout(self)  # 垂直布局
        layout.setContentsMargins(8, 8, 8, 8)  # 边距

        # 标题
        title_label: QLabel = QLabel("标注面板", self)  # 标题
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")  # 加粗
        layout.addWidget(title_label)  # 添加标题

        # 当前选择信息
        self._header_label: QLabel = QLabel("请从设备树中选择一个 TC", self)  # 提示信息
        self._header_label.setWordWrap(True)  # 自动换行
        self._header_label.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 8px;")  # 灰色小字
        layout.addWidget(self._header_label)  # 添加提示

        # 标注表单组
        ann_group: QGroupBox = QGroupBox("物理量标注")  # 分组框
        ann_layout: QFormLayout = QFormLayout(ann_group)  # 表单布局

        # 名称下拉
        self._name_combo: QComboBox = QComboBox()  # 名称下拉框
        self._name_combo.setEditable(True)  # 可编辑（支持自定义名称）
        self._name_combo.addItems(QuantityCatalog.all_names())  # 填充已知名称
        self._name_combo.setToolTip("选择或输入物理量名称")  # 工具提示
        ann_layout.addRow("名称:", self._name_combo)  # 添加到表单

        # 单位下拉
        self._unit_combo: QComboBox = QComboBox()  # 单位下拉框
        self._unit_combo.setEditable(True)  # 可编辑
        self._unit_combo.addItems(UNIT_OPTIONS)  # 填充单位选项
        self._unit_combo.setToolTip("选择或输入测量单位")  # 工具提示
        ann_layout.addRow("单位:", self._unit_combo)  # 添加到表单

        # 数据类型单选按钮
        self._type_group: QButtonGroup = QButtonGroup(self)  # 单选按钮组
        self._actual_radio: QRadioButton = QRadioButton("实际值")  # 实际值选项
        self._target_radio: QRadioButton = QRadioButton("目标值")  # 目标值选项
        self._other_radio: QRadioButton = QRadioButton("其他")  # 其他选项
        self._type_group.addButton(self._actual_radio, 0)  # ID=0
        self._type_group.addButton(self._target_radio, 1)  # ID=1
        self._type_group.addButton(self._other_radio, 2)  # ID=2
        self._actual_radio.setChecked(True)  # 默认为实际值
        radio_widget = QWidget()  # 容器
        radio_layout = QHBoxLayout(radio_widget)  # 水平布局
        radio_layout.setContentsMargins(0, 0, 0, 0)  # 无边距
        radio_layout.addWidget(self._actual_radio)  # 添加实际值
        radio_layout.addWidget(self._target_radio)  # 添加目标值
        radio_layout.addWidget(self._other_radio)  # 添加其他
        radio_layout.addStretch()  # 弹性空间
        ann_layout.addRow("类型:", radio_widget)  # 添加到表单

        # 训练特征勾选
        self._training_check: QCheckBox = QCheckBox("纳入训练特征")  # 勾选框
        self._training_check.setChecked(True)  # 默认选中
        self._training_check.setToolTip("勾选后该列将出现在导出的训练 CSV 中")  # 工具提示
        ann_layout.addRow("", self._training_check)  # 添加到表单（无标签）

        layout.addWidget(ann_group)  # 添加标注组

        # 应用到所有匹配按钮
        self._apply_all_btn: QPushButton = QPushButton("应用到所有相同 TC")  # 批量按钮
        self._apply_all_btn.setToolTip("将所有相同 typecode 的条目也使用此标注")  # 工具提示
        layout.addWidget(self._apply_all_btn)  # 添加按钮

        # 当前无选择的提示
        self._no_selection_label: QLabel = QLabel("")  # 占位
        layout.addWidget(self._no_selection_label)  # 添加到布局

        layout.addStretch()  # 底部弹性空间

        # 连接变更信号
        self._name_combo.currentTextChanged.connect(self._on_field_changed)  # 名称变更
        self._unit_combo.currentTextChanged.connect(self._on_field_changed)  # 单位变更
        self._type_group.buttonClicked.connect(self._on_field_changed)  # 类型变更
        self._training_check.toggled.connect(self._on_field_changed)  # 训练勾选变更
        self._apply_all_btn.clicked.connect(self._on_apply_all)  # 批量应用

        # 初始禁用状态
        self.setEnabled(False)  # 无选择时禁用整个面板

    def load_annotation(self, node_id: int, slot: int, tc: int) -> None:
        """从现有标注或默认值填充表单.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            tc: typecode 值
        """  # 方法文档
        self._current_key = (node_id, slot, tc)  # 保存当前键
        self._header_label.setText(  # 更新选择信息
            f"设备 {node_id}  |  Slot {slot}  |  tc={tc}"  # 显示层级路径
        )  # 更新标签
        self._header_label.setStyleSheet("color: #333; font-size: 12px; font-weight: bold;")  # 深色加粗

        # 获取默认标注
        default = QuantityCatalog.get_default_annotation(tc)  # 从目录获取默认值

        self._block_signals(True)  # 阻止信号（编程式设置）
        self._name_combo.setCurrentText(default.name)  # 设置名称
        self._unit_combo.setCurrentText(default.unit)  # 设置单位
        # 设置数据类型单选
        type_map = {"actual": 0, "target": 1, "other": 2}  # 类型到按钮 ID 映射
        idx = type_map.get(default.data_type.value, 2)  # 获取按钮 ID
        btn = self._type_group.button(idx)  # 获取按钮
        if btn:  # 按钮存在
            btn.setChecked(True)  # 选中
        self._training_check.setChecked(default.include_in_training)  # 设置训练标记
        self._block_signals(False)  # 恢复信号

        self.setEnabled(True)  # 启用面板

    def _on_field_changed(self) -> None:
        """任意表单字段变更时发射 annotation_changed."""
        if self._signalsBlocked():  # 信号被阻止（编程式更新中）
            return  # 不发射

        node_id, slot, tc = self._current_key  # 解包当前键
        if node_id == 0 and slot == 0 and tc == 0:  # 尚未选择 TC
            return  # 忽略

        # 获取数据类型
        type_map = {0: "actual", 1: "target", 2: "other"}  # ID 到类型字符串
        checked_id = self._type_group.checkedId()  # 获取选中 ID
        if checked_id < 0:  # 未选中任何按钮
            checked_id = 2  # 默认 other
        data_type = DataType(type_map[checked_id])  # 构造 DataType

        ann = Annotation(  # 创建标注对象
            node_id=node_id,  # 设备节点
            slot=slot,  # 槽位
            tc=tc,  # typecode
            name=self._name_combo.currentText().strip(),  # 名称（去空格）
            unit=self._unit_combo.currentText().strip(),  # 单位（去空格）
            data_type=data_type,  # 数据类型
            include_in_training=self._training_check.isChecked(),  # 训练标记
        )  # 完成

        self.annotation_changed.emit(node_id, slot, tc, ann)  # 发射信号

    def _on_apply_all(self) -> None:
        """批量应用按钮 — 发射 apply_all_requested."""
        node_id, slot, tc = self._current_key  # 解包
        if node_id == 0 and slot == 0 and tc == 0:  # 未选择
            return  # 忽略

        type_map = {0: "actual", 1: "target", 2: "other"}  # 类型映射
        checked_id = self._type_group.checkedId()  # 选中 ID
        if checked_id < 0:  # 未选中
            checked_id = 2  # 默认 other

        ann = Annotation(  # 构造标注
            node_id=node_id, slot=slot, tc=tc,
            name=self._name_combo.currentText().strip(),  # 名称
            unit=self._unit_combo.currentText().strip(),  # 单位
            data_type=DataType(type_map[checked_id]),  # 类型
            include_in_training=self._training_check.isChecked(),  # 训练标记
        )  # 完成
        self.apply_all_requested.emit(node_id, slot, tc, ann)  # 发射信号

    def _block_signals(self, block: bool) -> None:
        """控制所有表单控件的信号阻止状态.

        Args:
            block: True 阻止信号，False 恢复信号
        """  # 方法文档
        self._name_combo.blockSignals(block)  # 名称下拉
        self._unit_combo.blockSignals(block)  # 单位下拉
        self._type_group.blockSignals(block)  # 类型单选组
        self._training_check.blockSignals(block)  # 训练勾选
