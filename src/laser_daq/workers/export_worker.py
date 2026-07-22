"""后台 CSV 写入器 — 在 QThread 中运行以避免 GUI 冻结."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型

from PyQt6.QtCore import QObject, pyqtSignal  # Qt 基类和信号
import pandas as pd  # 数据处理库


class ExportWorker(QObject):
    """将宽表 DataFrame 写入 CSV 文件.

    将此对象通过 moveToThread(thread) 移到 QThread 中执行.

    Signals:
        file_written(path): 单个文件写入成功
        write_finished(count): 所有文件写入完成
        write_error(message): 写入失败
    """  # 类文档

    file_written = pyqtSignal(str)  # 文件路径
    write_finished = pyqtSignal(int)  # 成功写入的文件数
    write_error = pyqtSignal(str)  # 错误消息

    def __init__(self, parent: QObject = None) -> None:
        """初始化 ExportWorker.

        Args:
            parent: Qt 父对象
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造

    def write_files(self, output_dir: str, file_data: dict[str, pd.DataFrame]) -> None:
        """槽函数 — 将多个 DataFrame 写入 CSV 文件.

        Args:
            output_dir: 输出目录路径
            file_data: 文件名 -> DataFrame 的映射字典
        """  # 方法文档
        output_path = Path(output_dir)  # 转为 Path 对象
        count: int = 0  # 成功计数

        try:  # 捕获异常
            output_path.mkdir(parents=True, exist_ok=True)  # 确保输出目录存在

            for filename, df in file_data.items():  # 遍历所有文件
                filepath = output_path / filename  # 拼接完整路径
                df.to_csv(filepath, index=False, na_rep="NaN")  # 写入 CSV，NaN 用字符串表示
                self.file_written.emit(str(filepath))  # 发射文件写入信号
                count += 1  # 计数加一

            self.write_finished.emit(count)  # 发射完成信号
        except Exception as exc:  # 捕获所有异常
            self.write_error.emit(str(exc))  # 发射错误信号
