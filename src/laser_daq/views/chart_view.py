"""嵌入式 matplotlib 时序图表 — V0.1 占位，V0.3 完整实现."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel  # Qt 控件
import matplotlib  # 绘图库
matplotlib.use("QtAgg")  # 设置 Qt 后端
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # Qt 画布
from matplotlib.figure import Figure  # matplotlib 图形
import pandas as pd  # 数据处理


class ChartView(QWidget):
    """多标签图表视图 — 时序分析.

    嵌入 matplotlib Figure、工具栏和物理量选择器.
    V0.1 仅显示占位提示，V0.3 实现完整图表功能.
    """  # 类文档

    def __init__(self, parent: QWidget = None) -> None:
        """初始化 ChartView.

        Args:
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        layout: QVBoxLayout = QVBoxLayout(self)  # 垂直布局

        # V0.1 占位：显示 matplotlib 空白画布
        self._figure: Figure = Figure(figsize=(6, 4), dpi=100)  # 创建图形
        self._canvas: FigureCanvasQTAgg = FigureCanvasQTAgg(self._figure)  # Qt 画布
        layout.addWidget(self._canvas)  # 添加画布

        # 占位文本
        self._placeholder: QLabel = QLabel(  # 占位标签
            "选择设备/Slot 后显示时序图 (V0.3)",  # 提示文本
            self,  # 父控件
        )  # 标签
        self._placeholder.setStyleSheet("color: #999; font-size: 14px;")  # 灰色居中样式
        self._placeholder.setAlignment(self._placeholder.alignment())  # 保持对齐
        layout.addWidget(self._placeholder)  # 添加占位

        # 绘制初始空图
        ax = self._figure.add_subplot(111)  # 添加子图
        ax.text(0.5, 0.5, "时序图表 — V0.3 实现",  # 占位文字
                ha="center", va="center", color="#ccc",  # 居中灰色
                fontsize=14, transform=ax.transAxes)  # 相对坐标
        ax.set_xticks([])  # 隐藏 x 刻度
        ax.set_yticks([])  # 隐藏 y 刻度
        self._canvas.draw_idle()  # 空闲时重绘

    def update_for_selection(self, node_id: int, slot: int,
                              func_group: str = "", tp: int = 0) -> None:
        """根据设备树选择更新图表（V0.3 实现）.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            func_group: 功能组 (V2)
            tp: 类型码 (V2)
        """  # 方法文档
        # V0.2 中为 no-op，留待 V0.3 实现
        pass  # 占位

    def plot_time_series(self, x: pd.Series, y: pd.Series,
                          label: str, unit: str) -> None:
        """单线时序图.

        Args:
            x: X 轴数据（uptime）
            y: Y 轴数据（值）
            label: 图例标签
            unit: Y 轴单位
        """  # 方法文档
        self._figure.clear()  # 清空图形
        ax = self._figure.add_subplot(111)  # 添加子图
        ax.plot(x, y, label=label, color="steelblue")  # 画折线图
        ax.set_xlabel("Uptime (s)")  # X 轴标签
        ax.set_ylabel(unit)  # Y 轴标签
        ax.legend()  # 显示图例
        ax.grid(True, alpha=0.3)  # 网格线
        self._figure.tight_layout()  # 紧凑布局
        self._canvas.draw_idle()  # 空闲时重绘
