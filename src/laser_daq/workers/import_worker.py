"""后台 CSV 读取器 (V2) — 在 QThread 中运行以避免 GUI 冻结."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型

from PyQt6.QtCore import QObject, pyqtSignal  # Qt 基类和信号
import pandas as pd  # 数据处理库

from laser_daq.constants import REQUIRED_COLUMNS, EXCLUDED_FUNC_GROUPS  # 必需列 + 排除列表


class ImportWorker(QObject):
    """读取 CSV 文件并返回 DataFrame (V2 格式).

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
        """槽函数 — 读取 CSV 文件并验证列结构 (V2: 6 列).

        设计为通过信号触发或 QMetaObject.invokeMethod 调用.

        处理步骤:
        1. 读取 CSV
        2. 验证 6 个必需列
        3. 数值类型转换 (node_id, slot, tp, val_float)
        4. func 列保留为字符串
        5. 过滤 RPTREGS 行
        6. 删除关键列为 NaN 的行

        Args:
            file_path: CSV 文件的路径字符串
        """  # 方法文档
        try:  # 捕获所有异常
            path = Path(file_path)  # 转为 Path 对象

            if not path.exists():  # 文件不存在
                raise FileNotFoundError(f"文件不存在: {file_path}")

            if path.suffix.lower() != ".csv":  # 非 CSV 文件
                raise ValueError(f"不是 CSV 文件: {path.name}")

            df: pd.DataFrame = pd.read_csv(path)  # 读取 CSV

            # 验证必需列 (V2: 6 列)
            missing: list[str] = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if missing:  # 有缺失列
                raise ValueError(
                    f"缺少列: {', '.join(missing)}. "
                    f"必需列 (V2): {', '.join(REQUIRED_COLUMNS)}"
                )

            # 将关键列转为数值类型，非法值转为 NaN
            for col in ("node_id", "slot", "tp"):  # V2: tp 替代 tc
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["val_float"] = pd.to_numeric(df["val_float"], errors="coerce")  # V2: val_float

            # func 列保留为字符串（不过滤，保留 RPTCURR/RPTTEMP/RPTREGS）
            df["func"] = df["func"].astype(str).str.strip()  # 确保为字符串类型

            # V2 新增: 过滤掉 RPTREGS 读响应
            before_filter = len(df)  # 过滤前行数
            df = df[~df["func"].isin(EXCLUDED_FUNC_GROUPS)]  # 排除 RPTREGS
            filtered_count = before_filter - len(df)  # 被过滤的行数

            # 删除关键列为 NaN 的行
            df = df.dropna(subset=["node_id", "slot", "tp"])  # V2: tp 替代 tc

            # 重置索引
            df = df.reset_index(drop=True)  # 重置 DataFrame 索引

            self.read_finished.emit(df, str(path))  # 发射成功信号
        except Exception as exc:  # 捕获所有异常
            self.read_error.emit(str(exc))  # 发射错误信号
