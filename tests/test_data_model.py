"""测试 DataModel (V2) — 核心状态容器."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型

import pandas as pd  # 数据处理
import pytest  # 测试框架

from laser_daq.models.data_model import DataModel  # 被测模块
from laser_daq.models.annotation import Annotation  # 标注
from laser_daq.constants import DataType  # 数据类型


class TestDataModelValidation:  # 验证方法测试组
    """测试 validate_columns 和 deduplicate 静态方法 (V2)."""  # 类文档

    def test_validate_good_columns_v2(self) -> None:
        """验证包含所有 V2 必需列时不报错."""
        df = pd.DataFrame(columns=["uptime", "node_id", "slot", "func", "tp", "val_float"])
        missing = DataModel.validate_columns(df)
        assert len(missing) == 0

    def test_validate_missing_columns_v2(self) -> None:
        """验证 V2 缺少列时正确报告."""
        df = pd.DataFrame(columns=["uptime", "node_id"])  # 仅两列
        missing = DataModel.validate_columns(df)
        assert len(missing) == 4  # 缺少 slot, func, tp, val_float

    def test_deduplicate_removes_dupes(self) -> None:
        """验证去重逻辑 — 删除完全重复行."""
        df = pd.DataFrame({
            "uptime": [1, 1, 2],
            "node_id": [2, 2, 2],
            "slot": [0, 0, 0],
            "func": ["RPTTEMP", "RPTTEMP", "RPTTEMP"],
            "tp": [21, 21, 24],
            "val_float": [25.1, 25.1, 0.75],
        })
        result = DataModel.deduplicate(df)
        assert len(result) == 2  # 应剩余 2 行


class TestDataModelMutators:  # 变更方法测试组 (V2)
    """测试 set_raw_data 和 set_annotation."""  # 类文档

    def test_set_raw_data_resets_state(self) -> None:
        """验证 set_raw_data 清除旧的 device_types 和 annotations."""
        model = DataModel()
        df = pd.DataFrame({
            "uptime": [0], "node_id": [2], "slot": [0],
            "func": ["RPTTEMP"], "tp": [21], "val_float": [25.0],
        })
        model.set_raw_data(df, Path("/tmp/test.csv"))
        assert model.is_loaded
        assert model.source_path == Path("/tmp/test.csv")

    def test_set_annotation_v2(self) -> None:
        """验证 V2 标注的存储和检索 (含 func_group)."""
        model = DataModel()
        ann = Annotation(
            node_id=2, slot=0, func_group="RPTTEMP", tp=21,
            name="T1_ACTUAL", unit="C", data_type=DataType.ACTUAL,
        )
        model.set_annotation(2, 0, "RPTTEMP", 21, ann)
        retrieved = model.get_annotation(2, 0, "RPTTEMP", 21)
        assert retrieved is not None
        assert retrieved.name == "T1_ACTUAL"
        assert retrieved.func_group == "RPTTEMP"
        assert retrieved.tp == 21

    def test_get_nonexistent_annotation(self) -> None:
        """验证不存在的标注返回 None."""
        model = DataModel()
        assert model.get_annotation(99, 0, "RPTCURR", 8) is None


class TestDataModelQueries:  # 查询方法测试组 (V2)
    """测试 get_slot_data 和 get_unique_combinations."""  # 类文档

    def test_get_slot_data(self, narrow_df: pd.DataFrame) -> None:
        """验证按 node_id, slot 筛选数据 (V2)."""
        model = DataModel()
        model.set_raw_data(narrow_df, Path("/tmp/test.csv"))
        slot_data = model.get_slot_data(4, 0)
        assert len(slot_data) == 6  # 应有 6 行
        assert all(slot_data["node_id"] == 4)
        assert all(slot_data["slot"] == 0)

    def test_get_slot_data_filtered_by_func(self, narrow_df: pd.DataFrame) -> None:
        """验证 V2 可选按 func_group 筛选."""
        model = DataModel()
        model.set_raw_data(narrow_df, Path("/tmp/test.csv"))
        slot_data = model.get_slot_data(4, 0, func_group="RPTCURR")
        assert all(slot_data["func"] == "RPTCURR")

    def test_get_unique_combinations_v2(self, narrow_df: pd.DataFrame) -> None:
        """验证 V2 唯一组合统计 (含 func 列)."""
        model = DataModel()
        model.set_raw_data(narrow_df, Path("/tmp/test.csv"))
        combos = model.get_unique_combinations()
        assert "func" in combos.columns  # V2: func 列
        assert "tp" in combos.columns  # V2: tp 列
        assert len(combos) == 3  # (RPTCURR,14), (RPTCURR,8), (RPTCURR,9)

    def test_get_annotations_for_slot_v2(self, annotated_model: DataModel) -> None:
        """验证按 slot 获取所有标注 (V2: 键为 (func,tp))."""
        anns = annotated_model.get_annotations_for_slot(4, 0)
        assert len(anns) == 3
        assert ("RPTCURR", 14) in anns
        assert anns[("RPTCURR", 14)].name == "C_TARGET"

    def test_get_tp_signature_v2(self, sample_dataframe: pd.DataFrame) -> None:
        """验证 V2 (func, tp) 签名."""
        model = DataModel()
        model.set_raw_data(sample_dataframe, Path("/tmp/test.csv"))
        sig = model.get_tp_signature(2)  # node 2 是种子源
        assert ("RPTTEMP", 21) in sig
        assert ("RPTTEMP", 24) in sig

    def test_get_grouped_devices(self, sample_dataframe: pd.DataFrame) -> None:
        """验证按设备类型分组 (V2)."""
        from laser_daq.models.device_type import TypeDetector
        model = DataModel()
        model.set_raw_data(sample_dataframe, Path("/tmp/test.csv"))
        dts = TypeDetector.discover(sample_dataframe)
        model.set_device_types(dts)
        grouped = model.get_grouped_devices()
        assert "S001_Seed_Source" in grouped
        assert "BC01_Current_Board" in grouped
