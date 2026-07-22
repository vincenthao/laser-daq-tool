"""测试 TypeDetector — 设备类型分类."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

import pandas as pd  # 数据处理
import pytest  # 测试框架

from laser_daq.models.device_type import DeviceType, TypeDetector  # 被测模块


class TestTypeDetectorClassify:  # 分类方法测试组
    """测试 TypeDetector.classify 方法."""  # 类文档

    def test_classify_seed_source(self) -> None:
        """验证种子源签名 {2, 5, 24} 被正确识别."""
        result = TypeDetector.classify(2, frozenset({2, 5, 24}))  # 分类
        assert result.name == "S001_Seed_Source"  # 应为种子源
        assert "种子源" in result.description  # 描述应包含种子源

    def test_classify_current_board(self) -> None:
        """验证电流板签名 {2, 3, 4} 被正确识别."""
        result = TypeDetector.classify(4, frozenset({2, 3, 4}))  # 分类
        assert result.name == "BC01_Current_Board"  # 应为电流板
        assert "电流板" in result.description  # 描述应包含电流板

    def test_classify_current_board_with_target(self) -> None:
        """验证带目标电流的电流板签名 {1, 2, 3, 4} 被正确识别."""
        result = TypeDetector.classify(4, frozenset({1, 2, 3, 4}))  # 分类
        assert result.name == "BC01_Current_Board"  # 应为电流板

    def test_classify_unknown_device(self) -> None:
        """验证未知签名返回 Unknown_Device."""
        result = TypeDetector.classify(99, frozenset({99, 100}))  # 未知签名
        assert "Unknown" in result.name  # 应包含 Unknown

    def test_classify_empty_signature(self) -> None:
        """验证空签名返回 Empty_Device."""
        result = TypeDetector.classify(5, frozenset())  # 空签名
        assert result.name == "Empty_Device"  # 应为空设备

    def test_classify_partial_match(self) -> None:
        """验证子集匹配 — 额外 TC 不影响匹配."""
        # {2, 3, 4, 99} 包含电流板签名 {2,3,4} 的子集
        result = TypeDetector.classify(7, frozenset({2, 3, 4, 99}))  # 部分匹配
        assert result.name == "BC01_Current_Board"  # 应识别为电流板


class TestTypeDetectorDiscover:  # 发现方法测试组
    """测试 TypeDetector.discover 方法."""  # 类文档

    def test_discover_single_device(self) -> None:
        """验证单设备发现."""
        df = pd.DataFrame({  # 种子源数据
            "node_id": [2, 2, 2],
            "slot": [0, 0, 0],
            "tc": [2, 5, 24],
        })  # 三行
        devices = TypeDetector.discover(df)  # 发现
        assert len(devices) == 1  # 应发现 1 个设备
        assert 2 in devices  # node 2 应存在
        assert devices[2].name == "S001_Seed_Source"  # 应为种子源

    def test_discover_multiple_devices(self) -> None:
        """验证多设备发现."""
        df = pd.DataFrame({  # 两个设备的数据
            "node_id": [2, 2, 4, 4, 4],
            "slot": [0, 0, 0, 0, 0],
            "tc": [2, 5, 2, 3, 4],  # node 2 只有 tc=2,5; node 4 有 tc=2,3,4
        })  # 构建数据
        devices = TypeDetector.discover(df)  # 发现
        assert len(devices) == 2  # 应发现 2 个设备
        assert 2 in devices  # node 2 应存在
        assert 4 in devices  # node 4 应存在

    def test_discover_empty_dataframe(self) -> None:
        """验证空 DataFrame 返回空字典."""
        df = pd.DataFrame(columns=["node_id", "slot", "tc"])  # 空数据
        devices = TypeDetector.discover(df)  # 发现
        assert len(devices) == 0  # 应返回空结果

    def test_device_type_slots_preserved(self) -> None:
        """验证 DeviceType 的 slots 属性包含实际数据中的 slot 值."""
        df = pd.DataFrame({  # 多 slot 设备
            "node_id": [2, 2, 2],
            "slot": [0, 0, 3],  # slot 0 和 slot 3
            "tc": [2, 5, 24],
        })  # 数据
        devices = TypeDetector.discover(df)  # 发现
        assert devices[2].slots == frozenset({0, 3})  # slots 应为 {0, 3}
