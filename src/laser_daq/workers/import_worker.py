"""后台 CSV 读取器 (V2) — 在 QThread 中运行以避免 GUI 冻结."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

import struct  # IEEE 754 十六进制转浮点
from pathlib import Path  # 路径类型

from PyQt6.QtCore import QObject, pyqtSignal  # Qt 基类和信号
import pandas as pd  # 数据处理库
import numpy as np  # NaN 判断

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

    # IEEE 754 单精度浮点十六进制 → 浮点数的转换缓存（同一 hex 值大量重复）
    _hex_cache: dict[str, float] = {}  # 类级别缓存

    def __init__(self, parent: QObject = None) -> None:
        """初始化 ImportWorker.

        Args:
            parent: Qt 父对象
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造

    @staticmethod
    def _hex_to_float(hex_str: str) -> float:
        """将 IEEE 754 单精度十六进制字符串转为浮点数.

        例如 "0x41C8CCCD" → 25.1.

        Args:
            hex_str: 十六进制字符串（如 "0x41C8CCCD" 或 "41C8CCCD"）

        Returns:
            转换后的浮点值，解析失败返回 NaN
        """  # 方法文档
        if not isinstance(hex_str, str):  # 非字符串（如已为数值）
            return float(hex_str) if not pd.isna(hex_str) else float("nan")  # 尝试直接转
        hex_str = hex_str.strip()  # 去除空白
        if hex_str.startswith("0x") or hex_str.startswith("0X"):  # 去掉 0x 前缀
            hex_str = hex_str[2:]  # 截取
        hex_str = hex_str.zfill(8)  # 补齐 8 位
        if hex_str in ImportWorker._hex_cache:  # 命中缓存
            return ImportWorker._hex_cache[hex_str]  # 直接返回
        try:  # 尝试转换
            value: float = struct.unpack("!f", bytes.fromhex(hex_str))[0]  # 大端字节序
            ImportWorker._hex_cache[hex_str] = value  # 缓存结果
            return value  # 返回
        except (ValueError, struct.error):  # 无效 hex
            return float("nan")  # 返回 NaN

    def load(self, file_path: str) -> None:
        """槽函数 — 读取 CSV 文件并验证列结构 (V3: 6 列).

        设计为通过信号触发或 QMetaObject.invokeMethod 调用.

        处理步骤:
        1. 读取 CSV
        2. 验证 6 个必需列 (sample_seq, node_id, slot, func, tp, val_float)
        3. 数值类型转换 (sample_seq, node_id, slot, tp, val_float)
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

            df: pd.DataFrame = pd.read_csv(path, encoding="utf-8")  # 读取 CSV（显式 UTF-8，保证跨平台中文兼容）

            # 验证必需列 (V3: sample_seq, node_id, slot, func, tp, val_float)
            missing: list[str] = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if missing:  # 有缺失列
                raise ValueError(
                    f"缺少列: {', '.join(missing)}. "
                    f"必需列 (V3): {', '.join(REQUIRED_COLUMNS)}"
                )

            # 将关键列转为数值类型，非法值转为 NaN
            for col in ("sample_seq", "node_id", "slot", "tp"):  # V3: sample_seq 替代 uptime
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["val_float"] = pd.to_numeric(df["val_float"], errors="coerce")  # V2: val_float

            # V2: val_float 全为 NaN 时，尝试从 val_hex 列转换
            if df["val_float"].isna().all() and "val_hex" in df.columns:  # val_float 无有效值
                df["val_float"] = df["val_hex"].apply(ImportWorker._hex_to_float)  # hex → float

            # func 列保留为字符串（不过滤，保留 RPTCURR/RPTTEMP/RPTREGS）
            df["func"] = df["func"].astype(str).str.strip()  # 确保为字符串类型

            # V2 新增: 过滤掉 RPTREGS 读响应
            before_filter = len(df)  # 过滤前行数
            df = df[~df["func"].isin(EXCLUDED_FUNC_GROUPS)]  # 排除 RPTREGS
            filtered_count = before_filter - len(df)  # 被过滤的行数

            # 删除关键列为 NaN 的行（含 val_float，确保图表有值可绘）
            df = df.dropna(subset=["node_id", "slot", "tp", "val_float"])  # V2: tp + val_float

            # 重置索引
            df = df.reset_index(drop=True)  # 重置 DataFrame 索引

            self.read_finished.emit(df, str(path))  # 发射成功信号
        except Exception as exc:  # 捕获所有异常
            self.read_error.emit(str(exc))  # 发射错误信号
