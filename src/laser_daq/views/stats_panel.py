"""统计摘要面板 — 显示选中 slot 的统计信息."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem  # Qt 控件
from PyQt6.QtCore import Qt  # Qt 常量
import pandas as pd  # 数据处理

from laser_daq.models.data_model import DataModel  # 数据模型


class StatsPanel(QWidget):
    """显示选中 (node_id, slot) 的摘要统计 — 均值、标准差、最大偏差、数据点数、时间跨度."""  # 类文档

    def __init__(self, data_model: DataModel, parent: QWidget = None) -> None:
        """初始化 StatsPanel.

        Args:
            data_model: 共享的 DataModel 实例
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._data_model = data_model  # 持有数据模型引用

        layout = QVBoxLayout(self)  # 垂直布局
        layout.setContentsMargins(4, 4, 4, 4)  # 边距

        # 标题
        self._info_label = QLabel("选择设备/Slot 查看统计摘要")  # 提示标签
        self._info_label.setStyleSheet("font-weight: bold; font-size: 12px;")  # 加粗
        layout.addWidget(self._info_label)  # 添加标题

        # 统计表格
        self._table = QTableWidget(0, 6)  # 0行6列
        self._table.setHorizontalHeaderLabels(  # 表头
            ["物理量", "均值", "标准差", "最大偏差", "数据点数", "时间跨度"]  # 6 列
        )  # 设置表头
        self._table.horizontalHeader().setStretchLastSection(True)  # 最后一列拉伸
        self._table.setAlternatingRowColors(True)  # 交替行颜色
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # 只读
        layout.addWidget(self._table)  # 添加表格

    def update_for_selection(self, node_id: int, slot: int,
                              func_group: str = "", tp: int = 0) -> None:
        """根据设备树选择更新统计信息.

        func_group="" 且 tp=-1: 显示该 slot 所有测量量的统计
        否则: 显示单个 (func_group, tp) 的统计

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            func_group: 功能组
            tp: 类型码
        """  # 方法文档
        if not self._data_model.is_loaded:  # 无数据
            self._clear()  # 清空
            return  # 返回

        slot_df = self._data_model.get_slot_data(node_id, slot)  # 获取数据
        if slot_df.empty:  # 无数据
            self._clear()  # 清空
            return  # 返回

        self._info_label.setText(f"设备 {node_id} Slot {slot} — 统计摘要")  # 更新标题

        if func_group == "" and tp == -1:  # slot 级别 — 全部测量量
            groups = slot_df.groupby(["func", "tp"])  # 按 (func, tp) 分组
        else:  # 单个 (func, tp)
            mask = (slot_df["func"] == func_group) & (slot_df["tp"] == tp)  # 筛选
            filtered = slot_df.loc[mask]  # 子集
            if filtered.empty:  # 无数据
                self._clear()  # 清空
                return  # 返回
            groups = filtered.groupby(["func", "tp"])  # 单组

        self._table.setRowCount(0)  # 清空表格
        row = 0  # 行索引

        for (fg, tp_val), group in groups:  # 遍历每个组合
            vals = group["val_float"]  # 值序列
            uptimes = group["uptime"]  # 时间序列

            # 查找标注名称
            ann = self._data_model.get_annotation(node_id, slot, fg, tp_val)  # 获取标注
            label = f"{ann.name}" if ann and ann.name else f"{fg} tp={tp_val}"  # 标签

            mean_val = vals.mean()  # 均值
            std_val = vals.std()  # 标准差
            max_dev = (vals - mean_val).abs().max() if len(vals) > 0 else 0  # 最大偏差
            count = len(vals)  # 数据点数
            time_span = f"{uptimes.min():.0f}–{uptimes.max():.0f}s" if len(uptimes) > 0 else "-"  # 时间范围

            self._table.insertRow(row)  # 插入行
            self._table.setItem(row, 0, QTableWidgetItem(label))  # 物理量名
            self._table.setItem(row, 1, QTableWidgetItem(f"{mean_val:.4g}"))  # 均值
            self._table.setItem(row, 2, QTableWidgetItem(f"{std_val:.4g}"))  # 标准差
            self._table.setItem(row, 3, QTableWidgetItem(f"{max_dev:.4g}"))  # 最大偏差
            self._table.setItem(row, 4, QTableWidgetItem(str(count)))  # 数据点数
            self._table.setItem(row, 5, QTableWidgetItem(time_span))  # 时间跨度
            row += 1  # 下一行

        self._table.resizeColumnsToContents()  # 自动调整列宽

    def _clear(self) -> None:
        """清空表格."""
        self._info_label.setText("选择设备/Slot 查看统计摘要")  # 默认提示
        self._table.setRowCount(0)  # 清空
