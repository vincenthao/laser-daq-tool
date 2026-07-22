"""测试 DataModel — 核心状态容器."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from pathlib import Path  # 路径类型

import pandas as pd  # 数据处理
import pytest  # 测试框架

from laser_daq.models.data_model import DataModel  # 被测模块
from laser_daq.models.annotation import Annotation  # 标注
from laser_daq.constants import DataType  # 数据类型


class TestDataModelValidation:  # 验证方法测试组
    """测试 validate_columns 和 deduplicate 静态方法."""  # 类文档

    def test_validate_good_columns(self) -> None:
        """验证包含所有必需列时不报错."""
        df = pd.DataFrame(columns=["uptime", "node_id", "slot", "tc", "val"])  # 完整列
        missing = DataModel.validate_columns(df)  # 验证
        assert len(missing) == 0  # 应无缺失

    def test_validate_missing_columns(self) -> None:
        """验证缺少列时正确报告."""
        df = pd.DataFrame(columns=["uptime", "node_id"])  # 仅两列
        missing = DataModel.validate_columns(df)  # 验证
        assert "slot" in missing  # 缺少 slot
        assert "tc" in missing  # 缺少 tc
        assert "val" in missing  # 缺少 val
        assert len(missing) == 3  # 共缺少 3 列

    def test_deduplicate_removes_dupes(self) -> None:
        """验证去重逻辑 — 删除完全重复行."""
        df = pd.DataFrame({  # 含重复行的数据
            "uptime": [1, 1, 2],  # 第1、2行完全相同
            "node_id": [2, 2, 2],
            "slot": [0, 0, 0],
            "tc": [2, 2, 5],
            "val": [25.1, 25.1, 0.75],
        })  # 构建数据
        result = DataModel.deduplicate(df)  # 去重
        assert len(result) == 2  # 应剩余 2 行


class TestDataModelMutators:  # 变更方法测试组
    """测试 set_raw_data 和 set_annotation."""  # 类文档

    def test_set_raw_data_resets_state(self) -> None:
        """验证 set_raw_data 清除旧的 device_types 和 annotations."""
        model = DataModel()  # 创建实例
        df = pd.DataFrame({  # 基础数据
            "uptime": [0], "node_id": [2], "slot": [0], "tc": [2], "val": [25.0],
        })  # 一行数据
        model.set_raw_data(df, Path("/tmp/test.csv"))  # 设置数据
        assert model.is_loaded  # 应标记为已加载
        assert model.source_path == Path("/tmp/test.csv")  # 源路径应正确

    def test_set_annotation_and_retrieve(self) -> None:
        """验证标注的存储和检索."""
        model = DataModel()  # 创建实例
        ann = Annotation(  # 创建标注
            node_id=2, slot=0, tc=2, name="C_ACTUAL",
            unit="mA", data_type=DataType.ACTUAL,
        )  # 实际电流标注
        model.set_annotation(2, 0, 2, ann)  # 存储标注
        retrieved = model.get_annotation(2, 0, 2)  # 检索标注
        assert retrieved is not None  # 应存在
        assert retrieved.name == "C_ACTUAL"  # 名称应匹配
        assert retrieved.unit == "mA"  # 单位应匹配
        assert retrieved.data_type == DataType.ACTUAL  # 类型应匹配

    def test_get_nonexistent_annotation(self) -> None:
        """验证不存在的标注返回 None."""
        model = DataModel()  # 创建空实例
        assert model.get_annotation(99, 0, 1) is None  # 应返回 None


class TestDataModelQueries:  # 查询方法测试组
    """测试 get_slot_data 和 get_unique_combinations."""  # 类文档

    def test_get_slot_data(self, narrow_df: pd.DataFrame) -> None:
        """验证按 node_id, slot 筛选数据."""
        model = DataModel()  # 创建实例
        model.set_raw_data(narrow_df, Path("/tmp/test.csv"))  # 设置数据
        slot_data = model.get_slot_data(4, 0)  # 获取 slot 数据
        assert len(slot_data) == 6  # 应有 6 行
        assert all(slot_data["node_id"] == 4)  # 所有行 node_id 应为 4
        assert all(slot_data["slot"] == 0)  # 所有行 slot 应为 0

    def test_get_unique_combinations(self, narrow_df: pd.DataFrame) -> None:
        """验证唯一组合统计."""
        model = DataModel()  # 创建实例
        model.set_raw_data(narrow_df, Path("/tmp/test.csv"))  # 设置数据
        combos = model.get_unique_combinations()  # 获取组合
        assert len(combos) == 3  # tc=1,2,3 共 3 个组合
        # 验证 count 列存在
        assert "count" in combos.columns  # 应有 count 列

    def test_get_annotations_for_slot(self, annotated_model: DataModel) -> None:
        """验证按 slot 获取所有标注."""
        anns = annotated_model.get_annotations_for_slot(4, 0)  # 获取 slot 0 的标注
        assert len(anns) == 3  # tc=1,2,3 共 3 个标注
        assert 1 in anns  # tc=1 应存在
        assert anns[1].name == "C_TARGET"  # tc=1 应为 C_TARGET

    def test_get_grouped_devices(self, sample_dataframe: pd.DataFrame) -> None:
        """验证按设备类型分组."""
        from laser_daq.models.device_type import TypeDetector  # 设备类型检测
        model = DataModel()  # 创建实例
        model.set_raw_data(sample_dataframe, Path("/tmp/test.csv"))  # 设置数据
        dts = TypeDetector.discover(sample_dataframe)  # 发现设备
        model.set_device_types(dts)  # 设置设备类型
        grouped = model.get_grouped_devices()  # 获取分组
        assert "S001_Seed_Source" in grouped  # 应有种子源
        assert "BC01_Current_Board" in grouped  # 应有电流板
