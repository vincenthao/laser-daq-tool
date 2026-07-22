"""嵌入式 matplotlib 时序图表."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtWidgets import QWidget, QVBoxLayout  # Qt 控件
import matplotlib  # 绘图库
matplotlib.use("QtAgg")  # 设置 Qt 后端
import matplotlib.font_manager as fm  # 字体管理
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # Qt 画布
from matplotlib.figure import Figure  # matplotlib 图形
import pandas as pd  # 数据处理

# 配置 matplotlib 中文字体 — 使用 Noto Sans CJK SC（系统字体文件）
try:  # 尝试注册系统字体
    _cjk_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"  # Linux 路径
    fm.fontManager.addfont(_cjk_path)  # 注册字体
    matplotlib.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans", "sans-serif"]  # 设置字体列表
except (FileNotFoundError, RuntimeError):  # 字体文件不存在或注册失败
    matplotlib.rcParams["font.sans-serif"] = ["DejaVu Sans", "sans-serif"]  # 回退
matplotlib.rcParams["axes.unicode_minus"] = False  # 正确显示负号

from laser_daq.models.data_model import DataModel  # 数据模型


class ChartView(QWidget):
    """嵌入式 matplotlib 时序图表.

    根据设备树选择显示单个测量量或整个 slot 的时间序列.
    """  # 类文档

    def __init__(self, data_model: DataModel, parent: QWidget = None) -> None:
        """初始化 ChartView.

        Args:
            data_model: 共享的 DataModel 实例
            parent: Qt 父控件
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._data_model = data_model  # 持有数据模型引用

        layout = QVBoxLayout(self)  # 垂直布局
        layout.setContentsMargins(0, 0, 0, 0)  # 无边距

        # Matplotlib 画布
        self._figure = Figure(figsize=(5, 3), dpi=100)  # 创建图形
        self._canvas = FigureCanvasQTAgg(self._figure)  # Qt 画布
        layout.addWidget(self._canvas)  # 添加画布

        # 初始空图
        self._draw_placeholder()  # 占位提示

    def update_for_selection(self, node_id: int, slot: int,
                              func_group: str = "", tp: int = 0) -> None:
        """根据设备树选择更新图表.

        func_group="" 且 tp=-1: 显示该 slot 所有测量量
        否则: 显示单个 (func_group, tp) 的时序

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            func_group: 功能组（空字符串表示全 slot）
            tp: 类型码（-1 表示全 slot）
        """  # 方法文档
        if not self._data_model.is_loaded:  # 无数据
            self._draw_placeholder()  # 显示占位
            return  # 返回

        slot_df = self._data_model.get_slot_data(node_id, slot)  # 获取 slot 数据
        if slot_df.empty:  # 无数据
            self._draw_placeholder()  # 显示占位
            return  # 返回

        if func_group == "" and tp == -1:  # slot 级别 — 显示所有测量量
            self._plot_slot_overview(slot_df, node_id, slot)  # 多线图
        else:  # 单个 (func, tp)
            self._plot_single_measurement(slot_df, func_group, tp, node_id, slot)  # 单线图

    def _draw_placeholder(self) -> None:
        """绘制占位提示."""
        self._figure.clear()  # 清空
        ax = self._figure.add_subplot(111)  # 添加子图
        ax.text(0.5, 0.5, "选择设备/Slot/(func,tp) 显示时序图",  # 提示文字
                ha="center", va="center", color="#aaa", fontsize=12,
                transform=ax.transAxes)  # 相对坐标居中
        ax.set_xticks([])  # 隐藏刻度
        ax.set_yticks([])  # 隐藏刻度
        self._figure.tight_layout()  # 紧凑布局
        self._canvas.draw_idle()  # 空闲时重绘

    def _plot_slot_overview(self, slot_df: pd.DataFrame,
                             node_id: int, slot: int) -> None:
        """绘制 slot 级别概览 — 所有 (func, tp) 的时序叠加.

        Args:
            slot_df: slot 数据 DataFrame
            node_id: 设备节点 ID
            slot: 槽位索引
        """  # 方法文档
        self._figure.clear()  # 清空
        ax = self._figure.add_subplot(111)  # 添加子图

        # 按 (func, tp) 分组绘制
        for (fg, tp_val), group in slot_df.groupby(["func", "tp"]):  # 遍历每个组合
            group_sorted = group.sort_values("uptime")  # 按时间排序
            label = f"{fg} tp={tp_val}"  # 图例标签
            ax.plot(group_sorted["uptime"], group_sorted["val_float"],  # 画折线
                    marker=".", markersize=3, linewidth=1, label=label)  # 细线+点标记

        ax.set_xlabel("Uptime (s)")  # X 轴标签
        ax.set_ylabel("值")  # Y 轴标签
        ax.set_title(f"设备 {node_id} Slot {slot} — 全部测量量")  # 标题
        ax.legend(fontsize=7, loc="upper right")  # 小字号图例
        ax.grid(True, alpha=0.3)  # 网格线
        self._figure.tight_layout()  # 紧凑布局
        self._canvas.draw_idle()  # 空闲时重绘

    def _plot_single_measurement(self, slot_df: pd.DataFrame,
                                   func_group: str, tp: int,
                                   node_id: int, slot: int) -> None:
        """绘制单个 (func, tp) 的时序折线图.

        Args:
            slot_df: slot 数据 DataFrame
            func_group: 功能组
            tp: 类型码
            node_id: 设备节点 ID
            slot: 槽位索引
        """  # 方法文档
        mask = (slot_df["func"] == func_group) & (slot_df["tp"] == tp)  # 筛选
        data = slot_df.loc[mask].sort_values("uptime")  # 按时间排序

        if data.empty:  # 无匹配数据
            self._draw_placeholder()  # 显示占位
            return  # 返回

        # 查找标注名称
        ann = self._data_model.get_annotation(node_id, slot, func_group, tp)  # 获取标注
        label = f"{ann.name} ({ann.unit})" if ann and ann.name else f"{func_group} tp={tp}"  # 标签

        self._figure.clear()  # 清空
        ax = self._figure.add_subplot(111)  # 添加子图
        ax.plot(data["uptime"], data["val_float"],  # 画折线图
                marker="o", markersize=4, linewidth=1.5,  # 圆点标记
                color="steelblue", label=label)  # 蓝色
        ax.set_xlabel("Uptime (s)")  # X 轴标签
        ax.set_ylabel(label)  # Y 轴标签用物理量名
        ax.set_title(f"设备 {node_id} Slot {slot} — {label}")  # 标题
        ax.legend(fontsize=9)  # 图例
        ax.grid(True, alpha=0.3)  # 网格线
        self._figure.tight_layout()  # 紧凑布局
        self._canvas.draw_idle()  # 空闲时重绘
