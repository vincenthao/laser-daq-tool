"""后台 CSV 读取器 — 在 QThread 中运行以避免 GUI 冻结."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型

from PyQt6.QtCore import QObject, pyqtSignal  # Qt 基类和信号
import pandas as pd  # 数据处理库

from laser_daq.constants import REQUIRED_COLUMNS  # 必需列


class ImportWorker(QObject):
    """读取 CSV 文件并返回 DataFrame.

    将此对象通过 moveToThread(thread) 移到 QThread 中执行.

    Signals:
        read_finished(df, source_name): 读取成功
        read_error(message): 读取失败
    """  # 类文档

    read_finished = pyqtSignal(object, str)  # pd.DataFrame, 源文件名
    read_error = pyqtSignal(str)  # 错误消息

    def __init__(self, parent: QObject = None) -> None:
        """初始化 ImportWorker.

        Args:
            parent: Qt 父对象
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造

    def load(self, file_path: str) -> None:
        """槽函数 — 读取 CSV 文件并验证列结构.

        设计为通过信号触发或 QMetaObject.invokeMethod 调用.

        Args:
            file_path: CSV 文件的路径字符串
        """  # 方法文档
        try:  # 捕获所有异常
            path = Path(file_path)  # 转为 Path 对象

            if not path.exists():  # 文件不存在
                raise FileNotFoundError(f"文件不存在: {file_path}")  # 抛出异常

            if path.suffix.lower() != ".csv":  # 非 CSV 文件
                raise ValueError(f"不是 CSV 文件: {path.name}")  # 抛出异常

            df: pd.DataFrame = pd.read_csv(path)  # 读取 CSV

            # 验证必需列
            missing: list[str] = [c for c in REQUIRED_COLUMNS if c not in df.columns]  # 检查缺失列
            if missing:  # 有缺失列
                raise ValueError(  # 抛出详细错误
                    f"缺少列: {', '.join(missing)}. "
                    f"必需列: {', '.join(REQUIRED_COLUMNS)}"
                )  # 错误消息包含缺失和必需的列信息

            # 将关键列转为数值类型，非法值转为 NaN
            for col in ("node_id", "slot", "tc"):  # 遍历关键列
                df[col] = pd.to_numeric(df[col], errors="coerce")  # 转为数值
            df["val"] = pd.to_numeric(df["val"], errors="coerce")  # val 列也转数值

            # 删除关键列为 NaN 的行
            df = df.dropna(subset=["node_id", "slot", "tc"])  # 丢弃无效行

            # 重置索引
            df = df.reset_index(drop=True)  # 重置 DataFrame 索引

            self.read_finished.emit(df, str(path))  # 发射成功信号
        except Exception as exc:  # 捕获所有异常
            self.read_error.emit(str(exc))  # 发射错误信号
