"""编排 CSV 导入流程 — 文件 I/O、验证、去重、模型更新."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型
from typing import Optional  # 可选类型

from PyQt6.QtCore import QObject, pyqtSignal, QThread  # Qt 核心类
import pandas as pd  # 数据处理库

from laser_daq.models.data_model import DataModel  # 数据模型
from laser_daq.models.device_type import TypeDetector  # 设备类型检测器
from laser_daq.workers.import_worker import ImportWorker  # 导入工作线程


class ImportController(QObject):
    """管理 CSV 加载管道.

    Signals:
        import_started(path): 开始加载
        import_progress(rows_read, total): 进度更新
        import_finished(model): DataModel 已就绪
        import_error(message): 加载失败
    """  # 类文档

    import_started = pyqtSignal(str)  # 源文件名
    import_progress = pyqtSignal(int, int)  # 当前行, 总行数
    import_finished = pyqtSignal(object)  # DataModel 实例
    import_error = pyqtSignal(str)  # 错误消息

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """初始化 ImportController.

        Args:
            parent: Qt 父对象
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造
        self._thread: Optional[QThread] = None  # 工作线程
        self._worker: Optional[ImportWorker] = None  # 工作对象
        self._data_model: DataModel = DataModel()  # 数据模型实例

    def load_csv(self, paths: object) -> None:
        """启动异步 CSV 加载（单文件模式，使用列表中的第一个文件）.

        Args:
            paths: 文件路径列表（list[Path]）
        """  # 方法文档
        if not paths:  # 空列表
            return  # 直接返回

        # 转为 Python 列表以处理各种输入类型
        if isinstance(paths, list):  # 列表类型
            path_list = paths  # 直接使用
        else:  # 其他类型（如信号传递的 object）
            try:  # 尝试迭代
                path_list = list(paths)  # 转为列表
            except TypeError:  # 不可迭代
                self.import_error.emit("无效的文件路径参数")  # 发射错误
                return  # 返回

        if not path_list:  # 空列表
            return  # 直接返回

        first_path = Path(path_list[0])  # 取第一个文件路径
        self.import_started.emit(first_path.name)  # 发射开始信号

        # ---- 清理上一次的线程和 worker ----
        # 旧线程已完成时通过 finished→deleteLater 自清理
        # 此处只断开 Python 引用，不访问 C++ 对象（可能已被 Qt 销毁）
        self._thread = None  # 释放旧线程引用
        self._worker = None  # 释放旧 worker 引用

        # ---- 创建新的工作线程 ----
        thread = QThread()  # 本地变量，线程结束自动清理
        worker = ImportWorker()  # 本地变量
        worker.moveToThread(thread)  # 将 worker 移到线程

        # 连接信号：worker 完成 → 退出线程 → 清理
        worker.read_finished.connect(thread.quit)  # 读取成功 → 退出线程
        worker.read_error.connect(thread.quit)  # 读取失败 → 退出线程
        thread.finished.connect(thread.deleteLater)  # 线程结束 → 清理自身
        thread.finished.connect(worker.deleteLater)  # 线程结束 → 清理 worker

        # 连接信号：worker → 控制器回调
        worker.read_finished.connect(self._on_worker_finished)  # 读取成功
        worker.read_error.connect(self._on_worker_error)  # 读取失败

        # 线程启动 → 调用 worker.load
        file_path_str = str(first_path)  # 转为字符串避免跨线程问题
        thread.started.connect(  # 线程启动时
            lambda fp=file_path_str: worker.load(fp)  # 用默认参数捕获，直接引用 worker
        )  # 闭包

        # 保存引用以供后续 load_csv 调用识别（但不用于清理）
        self._thread = thread  # 保存新线程引用
        self._worker = worker  # 保存新 worker 引用

        thread.start()  # 启动线程

    def _on_worker_finished(self, df: pd.DataFrame, source: str) -> None:
        """ImportWorker 读取完成后的回调.

        执行验证、去重、存储到 DataModel，触发设备发现.

        Args:
            df: 读取的 DataFrame
            source: 源文件路径字符串
        """  # 方法文档
        try:  # 捕获异常
            # 验证列
            missing = DataModel.validate_columns(df)  # 检查缺失列
            if missing:  # 有缺失列（理论上 worker 已检查，此处二次确认）
                self.import_error.emit(f"数据验证失败: 缺少列 {missing}")  # 发射错误
                return  # 返回

            # 去重
            df = DataModel.deduplicate(df)  # 删除重复行
            self.import_progress.emit(len(df), len(df))  # 发射进度（已完成）

            # 存储到 DataModel
            self._data_model.set_raw_data(df, Path(source))  # 设置原始数据

            # 触发设备发现
            device_types = TypeDetector.discover(df)  # 检测设备类型
            self._data_model.set_device_types(device_types)  # 存储设备类型

            self.import_finished.emit(self._data_model)  # 发射完成信号
        except Exception as exc:  # 捕获异常
            self.import_error.emit(str(exc))  # 发射错误信号

    def _on_worker_error(self, message: str) -> None:
        """ImportWorker 读取失败的回调.

        Args:
            message: 错误消息
        """  # 方法文档
        self.import_error.emit(message)  # 转发错误信号

    @property
    def data_model(self) -> DataModel:
        """获取当前 DataModel 实例."""
        return self._data_model  # 返回数据模型
