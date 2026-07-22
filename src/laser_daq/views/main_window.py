"""顶层应用窗口 — 组装所有面板并接线信号."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型
from typing import cast  # 类型转换

from PyQt6.QtWidgets import (  # Qt 控件
    QMainWindow, QSplitter, QTabWidget, QMenuBar, QMenu, QStatusBar,  # 主窗口组件
    QMessageBox, QToolBar, QWidget, QVBoxLayout, QLabel, QProgressBar,  # 对话框和控件
)  # 导入
from PyQt6.QtCore import Qt, QTimer  # Qt 常量
from PyQt6.QtGui import QAction  # 动作

from laser_daq.views.import_panel import ImportPanel  # 导入面板
from laser_daq.views.preview_table import PreviewTable  # 预览表格
from laser_daq.views.device_tree import DeviceTree  # 设备树
from laser_daq.views.annotation_panel import AnnotationPanel  # 标注面板
from laser_daq.views.chart_view import ChartView  # 图表视图
from laser_daq.views.stats_panel import StatsPanel  # 统计面板
from laser_daq.views.export_dialog import ExportDialog  # 导出对话框
from laser_daq.controllers.import_controller import ImportController  # 导入控制器
from laser_daq.controllers.discovery_controller import DiscoveryController  # 发现控制器
from laser_daq.controllers.annotation_controller import AnnotationController  # 标注控制器
from laser_daq.controllers.export_controller import ExportController  # 导出控制器
from laser_daq.models.data_model import DataModel  # 数据模型
from laser_daq.constants import APP_NAME  # 应用名称


class MainWindow(QMainWindow):
    """根应用窗口.

    职责：
      - 构建控件树
      - 实例化控制器
      - 接线所有信号/槽连接
      - 持有持久的 DataModel 实例
    """  # 类文档

    def __init__(self) -> None:
        """初始化 MainWindow — 创建所有子控件、控制器并接线."""
        super().__init__()  # 调用基类构造

        # ---- 数据模型（唯一实例）----
        self._data_model: DataModel = DataModel()  # 核心状态容器

        # ---- 控制器 ----
        self._import_ctrl: ImportController = ImportController(self)  # 导入管道
        self._discovery_ctrl: DiscoveryController = DiscoveryController(self)  # 设备发现
        self._annotation_ctrl: AnnotationController = AnnotationController(  # 标注管理
            self._data_model, self  # 传入数据模型
        )  # 标注控制器
        self._export_ctrl: ExportController = ExportController(  # 导出管道
            self._data_model, self  # 传入数据模型
        )  # 导出控制器

        # ---- 视图（由 _setup_* 方法中赋值，Pylance 自动推断类型）----
        self._import_panel = None  # 见 _setup_central_widget
        self._preview_table = None  # 见 _setup_central_widget
        self._device_tree = None  # 见 _setup_central_widget
        self._annotation_panel = None  # 见 _setup_central_widget
        self._chart_view = None  # 见 _setup_central_widget
        self._stats_panel = None  # 见 _setup_central_widget
        self._status_progress = None  # 见 _setup_status_bar
        self._status_label = None  # 见 _setup_status_bar

        # ---- 构建界面 ----
        self._setup_menu_bar()  # 菜单栏
        self._setup_tool_bar()  # 工具栏
        self._setup_central_widget()  # 中央控件树
        self._setup_status_bar()  # 状态栏
        self._connect_signals()  # 接线所有信号

        self.setWindowTitle(APP_NAME)  # 设置窗口标题
        self.resize(1280, 800)  # 默认窗口大小
        self.setMinimumSize(960, 600)  # 最小窗口大小

    # =========================================================================
    # 布局构建（在 __init__ 中调用一次）
    # =========================================================================

    def _setup_menu_bar(self) -> None:
        """构建文件、模板、视图菜单."""
        menu_bar = cast(QMenuBar, self.menuBar())  # QMainWindow 必定返回有效值

        # 文件菜单
        file_menu = cast(QMenu, menu_bar.addMenu("文件(&F)"))  # addMenu 决不返回 None

        import_action: QAction = QAction("导入 CSV...(&I)", self)  # 导入动作
        import_action.setShortcut("Ctrl+O")  # 快捷键 Ctrl+O
        import_action.triggered.connect(self._on_import_action)  # 触发导入
        file_menu.addAction(import_action)  # 添加到菜单

        file_menu.addSeparator()  # 分隔线

        self._export_action: QAction = QAction("导出训练数据...(&E)", self)  # 导出动作
        self._export_action.setShortcut("Ctrl+E")  # 快捷键 Ctrl+E
        self._export_action.triggered.connect(self._show_export_dialog)  # 触发导出对话框
        self._export_action.setEnabled(False)  # 初始禁用（无数据时）
        file_menu.addAction(self._export_action)  # 添加到菜单

        file_menu.addSeparator()  # 分隔线

        quit_action: QAction = QAction("退出(&Q)", self)  # 退出动作
        quit_action.setShortcut("Ctrl+Q")  # 快捷键 Ctrl+Q
        quit_action.triggered.connect(self.close)  # 关闭窗口
        file_menu.addAction(quit_action)  # 添加到菜单

        # 模板菜单（V0.2 扩展）
        template_menu = cast(QMenu, menu_bar.addMenu("模板(&T)"))  # addMenu 决不返回 None
        self._template_save_action: QAction = QAction("保存模板...", self)  # 保存模板
        self._template_load_action: QAction = QAction("加载模板...", self)  # 加载模板
        self._template_save_action.setEnabled(False)  # V0.2 启用
        self._template_load_action.setEnabled(False)  # V0.2 启用
        template_menu.addAction(self._template_save_action)  # 添加保存
        template_menu.addAction(self._template_load_action)  # 添加加载

        # 视图菜单
        view_menu = cast(QMenu, menu_bar.addMenu("视图(&V)"))  # addMenu 决不返回 None
        about_action: QAction = QAction("关于(&A)", self)  # 关于动作
        about_action.triggered.connect(self._show_about)  # 显示关于
        view_menu.addAction(about_action)  # 添加到视图菜单

    def _setup_tool_bar(self) -> None:
        """快速操作工具栏."""
        toolbar: QToolBar = QToolBar("工具栏")  # 创建工具栏
        toolbar.setMovable(False)  # 不可移动
        self.addToolBar(toolbar)  # 添加到窗口

        import_btn = cast(QAction, toolbar.addAction("导入 CSV"))  # addAction 决不返回 None
        import_btn.triggered.connect(self._on_import_action)  # 触发导入
        toolbar.addSeparator()  # 分隔

        export_btn = cast(QAction, toolbar.addAction("导出训练数据"))  # addAction 决不返回 None
        export_btn.triggered.connect(self._show_export_dialog)  # 触发导出对话框

    def _setup_central_widget(self) -> None:
        """构建三栏 QSplitter 布局.

        布局：
          左栏（垂直分割）：ImportPanel + DeviceTree
          中栏（标签页）：Data(PreviewTable) | Chart | Stats
          右栏：AnnotationPanel
        """  # 方法文档
        # 外部分割器（水平三栏）
        outer_splitter: QSplitter = QSplitter(Qt.Orientation.Horizontal, self)  # 水平分割

        # ---- 左栏 ----
        left_splitter: QSplitter = QSplitter(Qt.Orientation.Vertical)  # 垂直分割

        self._import_panel = ImportPanel(self)  # 导入面板
        left_splitter.addWidget(self._import_panel)  # 添加导入面板

        self._device_tree = DeviceTree(self)  # 设备树
        left_splitter.addWidget(self._device_tree)  # 添加设备树

        left_splitter.setSizes([150, 350])  # 左栏内初始比例
        outer_splitter.addWidget(left_splitter)  # 添加到外部分割器

        # ---- 中栏（标签页）----
        tab_widget: QTabWidget = QTabWidget(self)  # 标签页控件

        # 数据预览标签
        self._preview_table = PreviewTable(self)  # 预览表格
        tab_widget.addTab(self._preview_table, "数据预览")  # 添加数据标签

        # 图表标签
        self._chart_view = ChartView(self)  # 图表视图
        tab_widget.addTab(self._chart_view, "时序图表")  # 添加图表标签

        # 统计标签
        self._stats_panel = StatsPanel(self)  # 统计面板
        tab_widget.addTab(self._stats_panel, "统计摘要")  # 添加统计标签

        outer_splitter.addWidget(tab_widget)  # 添加到外部分割器

        # ---- 右栏 ----
        self._annotation_panel = AnnotationPanel(self)  # 标注面板
        outer_splitter.addWidget(self._annotation_panel)  # 添加到外部分割器

        # 设置分割比例（左:中:右 = 1:2:1）
        outer_splitter.setSizes([300, 600, 300])  # 三栏宽度
        outer_splitter.setStretchFactor(0, 1)  # 左栏弹性
        outer_splitter.setStretchFactor(1, 2)  # 中栏弹性
        outer_splitter.setStretchFactor(2, 1)  # 右栏弹性

        self.setCentralWidget(outer_splitter)  # 设置中央控件

    def _setup_status_bar(self) -> None:
        """状态栏 — 带进度条."""
        status = cast(QStatusBar, self.statusBar())  # QMainWindow 必定返回有效值

        self._status_label = QLabel("就绪")  # 状态文本
        status.addWidget(self._status_label, 1)  # 弹性空间

        self._status_progress = QProgressBar()  # 进度条
        self._status_progress.setMaximumWidth(200)  # 最大宽度 200px
        self._status_progress.setVisible(False)  # 初始隐藏
        status.addPermanentWidget(self._status_progress)  # 固定右侧

    # =========================================================================
    # 信号接线（核心：唯一接线点）
    # =========================================================================

    def _connect_signals(self) -> None:
        """接线所有控制器 <-> 视图信号.

        这是核心接线点 — 保持耦合显式可见.
        所有信号路由在此明确定义.
        """  # 方法文档
        # ---- 导入流程 ----
        self._import_panel.file_dropped.connect(self._import_ctrl.load_csv)  # 拖拽 → 导入
        self._import_ctrl.import_started.connect(self._on_import_started)  # 开始导入
        self._import_ctrl.import_progress.connect(self._status_progress.setValue)  # 进度更新
        self._import_ctrl.import_finished.connect(self._on_import_finished)  # 导入完成
        self._import_ctrl.import_error.connect(self._on_error)  # 导入错误

        # ---- 设备树选择 → 标注面板 ----
        self._device_tree.selection_changed.connect(  # 树选择变更
            self._annotation_panel.load_annotation  # 加载标注
        )  # 连线

        # ---- 标注面板变更 → 控制器 ----
        self._annotation_panel.annotation_changed.connect(  # 标注变更
            self._annotation_ctrl.update_annotation  # 更新标注
        )  # 连线
        self._annotation_panel.apply_all_requested.connect(  # 批量应用
            self._annotation_ctrl.apply_to_all_matching  # 批量更新
        )  # 连线

        # ---- 标注更新后刷新设备树 ----
        self._annotation_ctrl.annotation_updated.connect(self._refresh_device_tree)  # 刷新树
        self._annotation_ctrl.batch_applied.connect(self._refresh_device_tree)  # 批量后刷新

        # ---- 设备树选择 → 图表/统计 ----
        self._device_tree.selection_changed.connect(  # 树选择
            self._chart_view.update_for_selection  # 更新图表（V0.3）
        )  # 连线
        self._device_tree.selection_changed.connect(  # 树选择
            self._stats_panel.update_for_selection  # 更新统计（V0.3）
        )  # 连线

        # ---- 导出流程 ----
        self._export_ctrl.export_started.connect(self._on_export_started)  # 开始导出
        self._export_ctrl.export_progress.connect(self._on_export_progress)  # 进度
        self._export_ctrl.export_finished.connect(self._on_export_finished)  # 完成
        self._export_ctrl.export_error.connect(self._on_error)  # 错误

    # =========================================================================
    # 槽函数
    # =========================================================================

    def _on_import_action(self) -> None:
        """菜单/工具栏导入动作 — 打开文件对话框."""
        from PyQt6.QtWidgets import QFileDialog  # 文件对话框
        paths, _ = QFileDialog.getOpenFileNames(  # 多文件选择
            self, "选择 CSV 文件", "",  # 标题和默认路径
            "CSV 文件 (*.csv);;所有文件 (*)",  # 过滤
        )  # 文件对话框
        if paths:  # 用户选择了文件
            self._import_panel.file_dropped.emit([Path(p) for p in paths])  # 手动发射拖拽信号

    def _on_import_started(self, name: str) -> None:
        """导入开始 — 更新状态栏.

        Args:
            name: 源文件名
        """  # 方法文档
        self._status_label.setText(f"正在加载: {name}...")  # 更新状态文本
        self._status_progress.setVisible(True)  # 显示进度条
        self._status_progress.setRange(0, 0)  # 不确定模式（动画滚动条）

    def _on_import_finished(self, model: DataModel) -> None:
        """导入完成 — 填充预览表格和设备树.

        Args:
            model: 已加载的 DataModel 实例
        """  # 方法文档
        self._data_model = model  # 更新本地引用

        # 更新预览表格
        self._preview_table.set_data(model.raw_df)  # 显示数据

        # 更新设备树
        self._device_tree.set_devices(  # 构建设备树
            model.device_types,  # 设备类型映射
            model.annotations,  # 标注映射
            model.raw_df,  # 原始数据
        )  # 设置树

        # 启用导出
        self._export_action.setEnabled(True)  # 启用导出菜单

        # 更新状态栏
        self._status_label.setText(  # 状态文本
            f"已加载: {model.source_path.name if model.source_path else '未知'} "
            f"({len(model.raw_df)} 行, {len(model.device_types)} 个设备)"
        )  # 显示文件名、行数、设备数
        self._status_progress.setVisible(False)  # 隐藏进度条

        # 更新导入控制器内部的数据模型引用（供后续导入使用）
        self._import_ctrl._data_model = model  # 更新内部引用

    def _on_error(self, message: str) -> None:
        """显示错误对话框.

        Args:
            message: 错误消息
        """  # 方法文档
        self._status_label.setText(f"错误: {message}")  # 状态栏显示错误
        self._status_progress.setVisible(False)  # 隐藏进度条
        QMessageBox.critical(self, "错误", message)  # 弹出错误对话框

    def _show_export_dialog(self) -> None:
        """显示导出对话框."""
        if not self._data_model.is_loaded:  # 无数据
            QMessageBox.warning(self, "警告", "请先导入 CSV 数据")  # 警告
            return  # 返回

        device_types = list(self._data_model.get_grouped_devices().keys())  # 获取设备类型列表
        dialog: ExportDialog = ExportDialog(device_types, self)  # 创建导出对话框
        dialog.export_requested.connect(self._export_ctrl.export)  # 连接导出信号
        dialog.exec()  # 模态显示

    def _on_export_started(self) -> None:
        """导出开始."""
        self._status_label.setText("正在导出训练数据...")  # 更新状态
        self._status_progress.setVisible(True)  # 显示进度条
        self._status_progress.setRange(0, 0)  # 不确定模式

    def _on_export_progress(self, current: int, total: int) -> None:
        """导出进度更新.

        Args:
            current: 当前文件索引
            total: 总文件数
        """  # 方法文档
        if total > 0 and current > 0:  # 有效进度
            self._status_progress.setRange(0, total)  # 设置范围
            self._status_progress.setValue(current)  # 更新值

    def _on_export_finished(self, count: int) -> None:
        """导出完成.

        Args:
            count: 成功导出的文件数
        """  # 方法文档
        self._status_label.setText(f"导出完成: {count} 个文件")  # 更新状态
        self._status_progress.setVisible(False)  # 隐藏进度条
        QMessageBox.information(  # 成功提示
            self, "导出完成",  # 标题
            f"成功导出 {count} 个训练数据文件",  # 内容
        )  # 信息对话框

    def _show_about(self) -> None:
        """显示关于对话框."""
        from laser_daq.constants import APP_VERSION  # 版本号
        QMessageBox.about(  # 关于对话框
            self, "关于",  # 标题
            f"<h3>{APP_NAME}</h3>"
            f"<p>版本: {APP_VERSION}</p>"
            f"<p>激光数据标注与训练集生成工具</p>"
            f"<p>用于导入、标注和导出 MCXN947 采集的激光设备数据</p>",
        )  # HTML 内容

    def _refresh_device_tree(self, *args) -> None:
        """刷新设备树显示（标注变更后调用）."""
        if self._data_model.is_loaded:  # 有数据
            self._device_tree.set_devices(  # 重建树
                self._data_model.device_types,
                self._data_model.annotations,
                self._data_model.raw_df,
            )  # 刷新
