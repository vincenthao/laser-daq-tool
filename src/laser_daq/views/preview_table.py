"""QTableView + PandasModel — 排序和筛选的原始数据预览."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtWidgets import QTableView, QHeaderView, QWidget  # Qt 控件
from PyQt6.QtCore import (  # Qt 核心
    Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QObject,  # 模型相关
)  # 导入
import pandas as pd  # 数据处理库

from laser_daq.constants import PREVIEW_ROW_LIMIT  # 预览行限制


class PandasModel(QAbstractTableModel):
    """适配器 — 将 pd.DataFrame 呈现为 QAbstractTableModel.

    V0.1 中为只读（预览目的）。V0.3+ 可扩展为可编辑.
    """  # 类文档

    def __init__(self, df: pd.DataFrame, parent: QObject = None) -> None:
        """初始化 PandasModel.

        Args:
            df: 要呈现的 DataFrame
            parent: Qt 父对象
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._df: pd.DataFrame = df  # 持有 DataFrame 引用

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """返回行数（仅预览前 PREVIEW_ROW_LIMIT 行）.

        Args:
            parent: 父索引（未使用）

        Returns:
            行数
        """  # 方法文档
        return min(len(self._df), PREVIEW_ROW_LIMIT)  # 限制预览行数

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """返回列数.

        Args:
            parent: 父索引（未使用）

        Returns:
            列数
        """  # 方法文档
        return len(self._df.columns)  # DataFrame 列数

    def data(self, index: QModelIndex,
             role: int = Qt.ItemDataRole.DisplayRole) -> object:
        """返回指定索引处的数据.

        Args:
            index: 模型索引
            role: 数据角色

        Returns:
            单元格数据
        """  # 方法文档
        if not index.isValid():  # 无效索引
            return None  # 返回 None
        if role == Qt.ItemDataRole.DisplayRole:  # 显示角色
            value = self._df.iloc[index.row(), index.column()]  # 获取值
            if pd.isna(value):  # NaN 值
                return ""  # 显示为空
            # 数值格式化
            if isinstance(value, float):  # 浮点数
                return f"{value:.4g}"  # 4 位有效数字
            return str(value)  # 字符串化
        return None  # 其他角色返回 None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.ItemDataRole.DisplayRole) -> object:
        """返回表头数据.

        Args:
            section: 行号或列号
            orientation: 水平或垂直
            role: 数据角色

        Returns:
            表头文本
        """  # 方法文档
        if role == Qt.ItemDataRole.DisplayRole:  # 显示角色
            if orientation == Qt.Orientation.Horizontal:  # 水平表头
                return str(self._df.columns[section])  # 列名
            return str(section + 1)  # 行号（从1开始）
        return None  # 其他角色返回 None

    def get_dataframe(self) -> pd.DataFrame:
        """返回底层 DataFrame（完整数据，非仅预览）."""
        return self._df  # 返回引用


class PreviewTable(QTableView):
    """可排序、可筛选的原始数据预览表格.

    显示前 PREVIEW_ROW_LIMIT 行；完整数据始终可查询.
    """  # 类文档

    def __init__(self, parent: QWidget = None) -> None:
        """初始化 PreviewTable.

        Args:
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._proxy: QSortFilterProxyModel = QSortFilterProxyModel(self)  # 排序代理
        self.setSortingEnabled(True)  # 启用排序
        self.horizontalHeader().setStretchLastSection(True)  # 最后一列拉伸
        self.setAlternatingRowColors(True)  # 交替行颜色
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)  # 整行选择
        self.horizontalHeader().setSectionResizeMode(  # 列宽调整
            QHeaderView.ResizeMode.Interactive  # 可交互调整
        )  # 列宽模式

    def set_data(self, df: pd.DataFrame) -> None:
        """替换显示的数据.

        Args:
            df: 要显示的 DataFrame
        """  # 方法文档
        model: PandasModel = PandasModel(df, self)  # 创建 PandasModel
        self._proxy.setSourceModel(model)  # 设置源模型
        self.setModel(self._proxy)  # 设置视图模型
        # 默认按 sample_seq 升序（V3: sample_seq 替代 uptime 做主键）
        if "sample_seq" in df.columns:  # V3: sample_seq 列
            seq_col = list(df.columns).index("sample_seq")  # 找 sample_seq 列索引
            self._proxy.sort(seq_col, Qt.SortOrder.AscendingOrder)  # 升序
        elif "uptime" in df.columns:  # 兼容旧格式有 uptime 列
            uptime_col = list(df.columns).index("uptime")  # 找 uptime 列索引
            self._proxy.sort(uptime_col, Qt.SortOrder.AscendingOrder)  # 升序
        self.resizeColumnsToContents()  # 自动调整列宽
