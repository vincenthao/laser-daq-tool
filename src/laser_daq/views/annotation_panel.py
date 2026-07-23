"""标注表单 (V2) — 每个 (func, tp) 的物理量编辑面板."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox, QRadioButton,
    QButtonGroup, QCheckBox, QPushButton, QGroupBox, QLabel, QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal

from laser_daq.models.annotation import Annotation, QuantityCatalog
from laser_daq.models.data_model import DataModel  # 数据模型（查找已保存标注）
from laser_daq.constants import DataType, UNIT_OPTIONS


class AnnotationPanel(QWidget):
    """右侧详情面板 (V2) — 为单个 (func, tp) 提供标注表单.

    Signals:
        annotation_changed(node_id, slot, func_group, tp, annotation): 字段值变更
        apply_all_requested(node_id, slot, func_group, tp, annotation): 应用到所有匹配项
    """  # 类文档

    annotation_changed = pyqtSignal(int, int, str, int, object)  # V2: 含 func_group
    apply_all_requested = pyqtSignal(int, int, str, int, object)  # V2: 含 func_group

    def __init__(self, data_model: DataModel, parent: QWidget = None) -> None:
        """初始化 AnnotationPanel.

        Args:
            data_model: 共享的 DataModel 实例，用于查询已保存标注
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)
        self._data_model: DataModel = data_model  # 持有数据模型引用（查询已保存标注）
        self._current_key: tuple[int, int, str, int] = (0, 0, "", 0)  # V2: (node_id, slot, func_group, tp)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题
        title_label: QLabel = QLabel("标注面板")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # 当前选择信息
        self._header_label: QLabel = QLabel("请从设备树中选择一个 (func, tp)")
        self._header_label.setWordWrap(True)
        self._header_label.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 8px;")
        layout.addWidget(self._header_label)

        # 标注表单组
        ann_group: QGroupBox = QGroupBox("物理量标注")
        ann_layout: QFormLayout = QFormLayout(ann_group)

        # 名称下拉
        self._name_combo: QComboBox = QComboBox()
        self._name_combo.setEditable(True)
        self._name_combo.addItems(QuantityCatalog.all_names())
        self._name_combo.setToolTip("选择或输入物理量名称（可自定义，如 LD2_C_ACTUAL）")
        ann_layout.addRow("名称:", self._name_combo)

        # 单位下拉
        self._unit_combo: QComboBox = QComboBox()
        self._unit_combo.setEditable(True)
        self._unit_combo.addItems(UNIT_OPTIONS)
        self._unit_combo.setToolTip("选择或输入测量单位")
        ann_layout.addRow("单位:", self._unit_combo)

        # 数据类型单选按钮
        self._type_group: QButtonGroup = QButtonGroup(self)
        self._actual_radio: QRadioButton = QRadioButton("实际值")
        self._target_radio: QRadioButton = QRadioButton("目标值")
        self._other_radio: QRadioButton = QRadioButton("其他")
        self._type_group.addButton(self._actual_radio, 0)
        self._type_group.addButton(self._target_radio, 1)
        self._type_group.addButton(self._other_radio, 2)
        self._actual_radio.setChecked(True)  # 默认为实际值
        radio_widget = QWidget()
        radio_layout = QHBoxLayout(radio_widget)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        radio_layout.addWidget(self._actual_radio)
        radio_layout.addWidget(self._target_radio)
        radio_layout.addWidget(self._other_radio)
        radio_layout.addStretch()
        ann_layout.addRow("类型:", radio_widget)

        # 训练特征勾选
        self._training_check: QCheckBox = QCheckBox("纳入训练特征")
        self._training_check.setChecked(True)
        self._training_check.setToolTip("勾选后该列将出现在导出的训练 CSV 中")
        ann_layout.addRow("", self._training_check)

        layout.addWidget(ann_group)

        # 应用到所有匹配按钮
        self._apply_all_btn: QPushButton = QPushButton("应用到所有相同 (func, tp)")
        self._apply_all_btn.setToolTip("将所有相同 func+tp 的条目也使用此标注")
        layout.addWidget(self._apply_all_btn)

        layout.addStretch()

        # 连接变更信号
        self._name_combo.currentTextChanged.connect(self._on_field_changed)
        self._unit_combo.currentTextChanged.connect(self._on_field_changed)
        self._type_group.buttonClicked.connect(self._on_field_changed)
        self._training_check.toggled.connect(self._on_field_changed)
        self._apply_all_btn.clicked.connect(self._on_apply_all)

        # 初始禁用状态
        self.setEnabled(False)

    def load_annotation(self, node_id: int, slot: int, func_group: str, tp: int) -> None:
        """从现有标注或默认值填充表单 (V2).

        Slot 级别选择（func_group="" 且 tp=-1）时禁用面板.
        优先使用已保存的标注，未保存时回退到 QuantityCatalog 默认值.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            func_group: 功能组 ("RPTCURR", "RPTTEMP")
            tp: 类型码值
        """  # 方法文档
        self._current_key = (node_id, slot, func_group, tp)

        # Slot 级别选择 — 禁用面板，提示用户展开
        if func_group == "" and tp == -1:
            self._header_label.setText(
                f"设备 {node_id}  |  Slot {slot} — 请展开选择具体 (func, tp)"
            )
            self._header_label.setStyleSheet("color: #999; font-size: 12px;")
            self.setEnabled(False)
            return

        self._header_label.setText(
            f"设备 {node_id}  |  Slot {slot}  |  {func_group} tp={tp}"
        )
        self._header_label.setStyleSheet("color: #333; font-size: 12px; font-weight: bold;")

        # 优先从 DataModel 中查找已保存的标注
        existing = self._data_model.get_annotation(node_id, slot, func_group, tp)
        if existing is not None:  # 有已保存标注，使用已有值
            ann = existing
        else:  # 无已保存标注，使用 QuantityCatalog 默认值
            ann = QuantityCatalog.get_default_annotation(func_group, tp)

        self._block_signals(True)
        self._name_combo.setCurrentText(ann.name)
        self._unit_combo.setCurrentText(ann.unit)
        type_map = {"actual": 0, "target": 1, "other": 2}
        idx = type_map.get(ann.data_type.value, 2)
        btn = self._type_group.button(idx)
        if btn:
            btn.setChecked(True)
        self._training_check.setChecked(ann.include_in_training)
        self._block_signals(False)

        self.setEnabled(True)

    def _on_field_changed(self) -> None:
        """任意表单字段变更时发射 annotation_changed (V2)."""
        if self.signalsBlocked():  # Qt 信号被阻止时跳过（load_annotation 中设置）
            return

        node_id, slot, func_group, tp = self._current_key
        if not func_group or tp == -1:  # Slot 级别选择，忽略
            return

        type_map = {0: "actual", 1: "target", 2: "other"}
        checked_id = self._type_group.checkedId()
        if checked_id < 0:
            checked_id = 2
        data_type = DataType(type_map[checked_id])

        ann = Annotation(
            node_id=node_id, slot=slot, func_group=func_group, tp=tp,
            name=self._name_combo.currentText().strip(),
            unit=self._unit_combo.currentText().strip(),
            data_type=data_type,
            include_in_training=self._training_check.isChecked(),
        )

        self.annotation_changed.emit(node_id, slot, func_group, tp, ann)

    def _on_apply_all(self) -> None:
        """批量应用按钮 — 发射 apply_all_requested (V2)."""
        node_id, slot, func_group, tp = self._current_key
        if not func_group or tp == -1:  # Slot 级别选择，忽略
            return

        type_map = {0: "actual", 1: "target", 2: "other"}
        checked_id = self._type_group.checkedId()
        if checked_id < 0:
            checked_id = 2

        ann = Annotation(
            node_id=node_id, slot=slot, func_group=func_group, tp=tp,
            name=self._name_combo.currentText().strip(),
            unit=self._unit_combo.currentText().strip(),
            data_type=DataType(type_map[checked_id]),
            include_in_training=self._training_check.isChecked(),
        )
        self.apply_all_requested.emit(node_id, slot, func_group, tp, ann)

    def _block_signals(self, block: bool) -> None:
        """控制所有表单控件的信号阻止状态."""
        self._name_combo.blockSignals(block)
        self._unit_combo.blockSignals(block)
        self._type_group.blockSignals(block)
        self._training_check.blockSignals(block)
