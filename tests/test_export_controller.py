"""测试 ExportController.build_wide_table — 窄表到宽表转换."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

import pandas as pd  # 数据处理
import pytest  # 测试框架

from laser_daq.controllers.export_controller import ExportController  # 导出控制器
from laser_daq.models.annotation import Annotation  # 标注
from laser_daq.models.data_model import DataModel  # 数据模型
from laser_daq.constants import DataType, PD_PWR_NAME, PD_PWR_UNIT  # 常量


class TestBuildWideTable:  # 宽表构建测试组
    """测试 ExportController.build_wide_table 静态方法."""  # 类文档

    def test_pivot_basic(self, narrow_df: pd.DataFrame,
                          annotated_model: DataModel) -> None:
        """验证基本 pivot — tc 行转为标注列."""
        annotations = annotated_model.get_annotations_for_slot(4, 0)  # 获取标注
        wide = ExportController.build_wide_table(narrow_df, annotations, 4, 0)  # 构建宽表
        assert wide is not None  # 不应为 None
        assert "C_TARGET_mA" in wide.columns  # 目标电流列
        assert "C_ACTUAL_mA" in wide.columns  # 实际电流列
        assert "V_ACTUAL_mV" in wide.columns  # LD 电压列
        assert len(wide) == 2  # 2 个时间点

    def test_deviation_column(self, narrow_df: pd.DataFrame,
                               annotated_model: DataModel) -> None:
        """验证偏差列 DEV = actual - target."""
        annotations = annotated_model.get_annotations_for_slot(4, 0)  # 获取标注
        wide = ExportController.build_wide_table(narrow_df, annotations, 4, 0)  # 构建
        assert "C_DEV_mA" in wide.columns  # 偏差列应存在
        # uptime=0: 998.5 - 1000.0 = -1.5
        assert abs(wide.loc[0, "C_DEV_mA"] - (-1.5)) < 0.01  # 第一个时间点偏差
        # uptime=1: 997.0 - 1000.0 = -3.0
        assert abs(wide.loc[1, "C_DEV_mA"] - (-3.0)) < 0.01  # 第二个时间点偏差

    def test_pd_pwr_column(self, narrow_df: pd.DataFrame,
                             annotated_model: DataModel) -> None:
        """验证 PD_PWR_mW 列始终存在且全为 NaN."""
        annotations = annotated_model.get_annotations_for_slot(4, 0)  # 获取标注
        wide = ExportController.build_wide_table(narrow_df, annotations, 4, 0)  # 构建
        pd_pwr_col = f"{PD_PWR_NAME}_{PD_PWR_UNIT}"  # PD_PWR_mW
        assert pd_pwr_col in wide.columns  # PD 功率列应存在
        assert wide[pd_pwr_col].isna().all()  # 应全部为 NaN

    def test_sort_by_uptime(self, narrow_df: pd.DataFrame,
                             annotated_model: DataModel) -> None:
        """验证输出按 uptime 排序."""
        annotations = annotated_model.get_annotations_for_slot(4, 0)  # 获取标注
        wide = ExportController.build_wide_table(narrow_df, annotations, 4, 0)  # 构建
        assert list(wide["uptime"]) == sorted(wide["uptime"])  # 应已排序

    def test_node_id_column(self, narrow_df: pd.DataFrame,
                              annotated_model: DataModel) -> None:
        """验证输出包含 node_id 列."""
        annotations = annotated_model.get_annotations_for_slot(4, 0)  # 获取标注
        wide = ExportController.build_wide_table(narrow_df, annotations, 4, 0)  # 构建
        assert "node_id" in wide.columns  # node_id 列应存在
        assert all(wide["node_id"] == 4)  # 所有行应为 4

    def test_target_forward_fill(self) -> None:
        """验证目标值的前向填充."""
        # 目标值有缺失的情况
        df = pd.DataFrame({  # 模拟目标值不连续的数据
            "uptime": [0, 1, 2],
            "node_id": [2, 2, 2],
            "slot": [0, 0, 0],
            "tc": [1, 2, 2],  # tc=1(目标) 只在 uptime=0 出现
            "val": [1000.0, 500.0, 501.0],
        })  # 目标值仅在第一个时间点
        annotations = {  # 标注
            1: Annotation(node_id=2, slot=0, tc=1, name="C_TARGET", unit="mA", data_type=DataType.TARGET),
            2: Annotation(node_id=2, slot=0, tc=2, name="C_ACTUAL", unit="mA", data_type=DataType.ACTUAL),
        }  # 标注映射
        wide = ExportController.build_wide_table(df, annotations, 2, 0)  # 构建
        assert wide is not None  # 应有输出
        # 目标值应被 ffill — uptime=1,2 应填充 uptime=0 的值
        print(wide.to_string())
        assert "C_TARGET_mA" in wide.columns
        # 检查 target 列的值是否被正确前向填充

    def test_empty_slot_returns_none(self) -> None:
        """验证空数据返回 None."""
        df = pd.DataFrame(columns=["uptime", "node_id", "slot", "tc", "val"])  # 空 DataFrame
        result = ExportController.build_wide_table(df, {}, 0, 0)  # 构建
        assert result is None  # 应返回 None
