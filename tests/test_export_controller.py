"""测试 ExportController.build_wide_table (V2) — 窄表到宽表转换."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

import pandas as pd  # 数据处理
import pytest  # 测试框架

from laser_daq.controllers.export_controller import ExportController  # 导出控制器
from laser_daq.models.annotation import Annotation  # 标注
from laser_daq.models.data_model import DataModel  # 数据模型
from laser_daq.constants import DataType, PD_PWR_NAME, PD_PWR_UNIT  # 常量


class TestBuildWideTableV2:  # 宽表构建测试组 (V2)
    """测试 ExportController.build_wide_table 静态方法 (V2)."""  # 类文档

    def test_pivot_basic_v2(self, narrow_df: pd.DataFrame,
                             annotated_model: DataModel) -> None:
        """验证基本 pivot — (func,tp) 对转为标注列 (V2)."""
        annotations = annotated_model.get_annotations_for_slot(4, 0)  # 获取标注
        wide = ExportController.build_wide_table(narrow_df, annotations, 4, 0)
        assert wide is not None
        assert "C_TARGET_mA" in wide.columns
        assert "C_ACTUAL_mA" in wide.columns
        assert "V_ACTUAL_mV" in wide.columns
        assert len(wide) == 2  # 2 个时间点

    def test_deviation_column_v2(self, narrow_df: pd.DataFrame,
                                   annotated_model: DataModel) -> None:
        """验证偏差列 DEV = actual - target (V2)."""
        annotations = annotated_model.get_annotations_for_slot(4, 0)
        wide = ExportController.build_wide_table(narrow_df, annotations, 4, 0)
        assert "C_DEV_mA" in wide.columns
        # uptime=0: 998.5 - 1000.0 = -1.5
        assert abs(wide.loc[0, "C_DEV_mA"] - (-1.5)) < 0.01
        # uptime=1: 997.0 - 1000.0 = -3.0
        assert abs(wide.loc[1, "C_DEV_mA"] - (-3.0)) < 0.01

    def test_pd_pwr_column_v2(self, narrow_df: pd.DataFrame,
                                annotated_model: DataModel) -> None:
        """验证 PD_PWR_mW 列始终存在且全为 NaN (V2)."""
        annotations = annotated_model.get_annotations_for_slot(4, 0)
        wide = ExportController.build_wide_table(narrow_df, annotations, 4, 0)
        pd_pwr_col = f"{PD_PWR_NAME}_{PD_PWR_UNIT}"
        assert pd_pwr_col in wide.columns
        assert wide[pd_pwr_col].isna().all()

    def test_sort_by_uptime_v2(self, narrow_df: pd.DataFrame,
                                 annotated_model: DataModel) -> None:
        """验证输出按 uptime 排序 (V2)."""
        annotations = annotated_model.get_annotations_for_slot(4, 0)
        wide = ExportController.build_wide_table(narrow_df, annotations, 4, 0)
        assert list(wide["uptime"]) == sorted(wide["uptime"])

    def test_node_id_column_v2(self, narrow_df: pd.DataFrame,
                                 annotated_model: DataModel) -> None:
        """验证输出包含 node_id 列 (V2)."""
        annotations = annotated_model.get_annotations_for_slot(4, 0)
        wide = ExportController.build_wide_table(narrow_df, annotations, 4, 0)
        assert "node_id" in wide.columns
        assert all(wide["node_id"] == 4)

    def test_filter_rptregs(self) -> None:
        """验证 build_wide_table 过滤 RPTREGS 行 (V2)."""
        # 构造含 RPTREGS 的数据
        df = pd.DataFrame({
            "uptime": [0, 0],
            "node_id": [4, 4],
            "slot": [0, 0],
            "func": ["RPTCURR", "RPTREGS"],  # 混合
            "tp": [8, 100],
            "val_float": [998.5, 999.0],
        })
        annotations = {
            ("RPTCURR", 8): Annotation(
                node_id=4, slot=0, func_group="RPTCURR", tp=8,
                name="C_ACTUAL", unit="mA", data_type=DataType.ACTUAL,
            ),
        }
        wide = ExportController.build_wide_table(df, annotations, 4, 0)
        assert wide is not None
        # RPTREGS 行应被过滤，只剩 RPTCURR 行
        assert "C_ACTUAL_mA" in wide.columns

    def test_target_forward_fill_v2(self) -> None:
        """验证目标值的前向填充 (V2)."""
        df = pd.DataFrame({
            "uptime": [0, 1, 2],
            "node_id": [2, 2, 2],
            "slot": [0, 0, 0],
            "func": ["RPTTEMP", "RPTTEMP", "RPTTEMP"],
            "tp": [21, 21, 21],  # 每个时间点都有 tp=21
            "val_float": [25.0, 25.5, 26.0],
        })
        annotations = {
            ("RPTTEMP", 21): Annotation(
                node_id=2, slot=0, func_group="RPTTEMP", tp=21,
                name="T1_ACTUAL", unit="C", data_type=DataType.ACTUAL,
            ),
        }
        wide = ExportController.build_wide_table(df, annotations, 2, 0)
        assert wide is not None
        assert "T1_ACTUAL_C" in wide.columns

    def test_empty_slot_returns_none_v2(self) -> None:
        """验证空数据返回 None (V2)."""
        df = pd.DataFrame(columns=["uptime", "node_id", "slot", "func", "tp", "val_float"])
        result = ExportController.build_wide_table(df, {}, 0, 0)
        assert result is None
