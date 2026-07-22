"""pytest 共享夹具 (V2) — 样本数据和模型."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型

import pytest  # 测试框架
import pandas as pd  # 数据处理

from laser_daq.models.data_model import DataModel  # 数据模型
from laser_daq.models.annotation import Annotation  # 标注
from laser_daq.constants import DataType  # 数据类型


@pytest.fixture  # 样本 CSV 路径夹具
def sample_csv_path() -> Path:
    """返回样本 CSV (V2 格式) 文件的路径."""
    return Path(__file__).parent.parent / "resources" / "sample_data" / "sample_mixed.csv"


@pytest.fixture  # 样本 DataFrame 夹具
def sample_dataframe(sample_csv_path: Path) -> pd.DataFrame:
    """返回从样本 CSV 读取的 DataFrame (V2)."""
    return pd.read_csv(sample_csv_path)  # 读取样本 CSV


@pytest.fixture  # 预构建窄表 DataFrame 夹具 (V2)
def narrow_df() -> pd.DataFrame:
    """返回用于单元测试的最小窄表 DataFrame (V2 格式)."""
    return pd.DataFrame({  # 构建测试数据
        "uptime": [0, 1, 0, 1, 0, 1],  # 时间戳
        "node_id": [4, 4, 4, 4, 4, 4],  # 设备节点
        "slot": [0, 0, 0, 0, 0, 0],  # 槽位
        "func": ["RPTCURR", "RPTCURR", "RPTCURR", "RPTCURR", "RPTCURR", "RPTCURR"],  # V2: 功能组
        "tp": [14, 14, 8, 8, 9, 9],  # V2: 类型码 (14=I_TGT, 8=I_ACT, 9=LDV)
        "val_float": [1000.0, 1000.0, 998.5, 997.0, 2450.0, 2460.0],  # V2: val_float
    })  # 电流板数据


@pytest.fixture  # 已标注的 DataModel 夹具 (V2)
def annotated_model(narrow_df: pd.DataFrame) -> DataModel:
    """返回预标注的 DataModel (V2)."""
    model = DataModel()  # 创建实例
    model.set_raw_data(narrow_df, Path("/tmp/test.csv"))  # 设置数据
    # V2: 添加标注使用 func_group
    model.set_annotation(4, 0, "RPTCURR", 14, Annotation(  # 目标电流
        node_id=4, slot=0, func_group="RPTCURR", tp=14,
        name="C_TARGET", unit="mA", data_type=DataType.TARGET,
    ))
    model.set_annotation(4, 0, "RPTCURR", 8, Annotation(  # 实际电流
        node_id=4, slot=0, func_group="RPTCURR", tp=8,
        name="C_ACTUAL", unit="mA", data_type=DataType.ACTUAL,
    ))
    model.set_annotation(4, 0, "RPTCURR", 9, Annotation(  # LD 电压
        node_id=4, slot=0, func_group="RPTCURR", tp=9,
        name="V_ACTUAL", unit="mV", data_type=DataType.ACTUAL,
    ))
    return model  # 返回模型
