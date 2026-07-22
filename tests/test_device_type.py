"""测试 TypeDetector (V2) — (func, tp) 设备类型分类."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

import pandas as pd  # 数据处理
import pytest  # 测试框架

from laser_daq.models.device_type import DeviceType, TypeDetector  # 被测模块


class TestTypeDetectorClassifyV2:  # 分类方法测试组 (V2)
    """测试 TypeDetector.classify 方法 (V2: (func,tp) 签名)."""  # 类文档

    def test_classify_seed_source_v2(self) -> None:
        """验证种子源 (RPTTEMP,21) + (RPTTEMP,24) 被正确识别."""
        result = TypeDetector.classify(2, frozenset({
            ("RPTTEMP", 21), ("RPTTEMP", 24),
        }))
        assert result.name == "S001_Seed_Source"

    def test_classify_current_board_v2(self) -> None:
        """验证电流板 (RPTCURR,8)+(RPTCURR,9)+(RPTCURR,10) 被正确识别."""
        result = TypeDetector.classify(4, frozenset({
            ("RPTCURR", 8), ("RPTCURR", 9), ("RPTCURR", 10),
        }))
        assert result.name == "BC01_Current_Board"

    def test_classify_current_board_with_target(self) -> None:
        """验证带目标电流的电流板."""
        result = TypeDetector.classify(4, frozenset({
            ("RPTCURR", 8), ("RPTCURR", 9), ("RPTCURR", 10), ("RPTCURR", 14),
        }))
        assert result.name == "BC01_Current_Board"

    def test_classify_current_board_with_ld_power(self) -> None:
        """验证带 LD 光功率的电流板 (V2 新签名)."""
        result = TypeDetector.classify(4, frozenset({
            ("RPTCURR", 8), ("RPTCURR", 9), ("RPTCURR", 10),
            ("RPTCURR", 11), ("RPTCURR", 14),
        }))
        assert result.name == "BC01_Current_Board"

    def test_classify_unknown_device_v2(self) -> None:
        """验证未知签名返回 Unknown_Device."""
        result = TypeDetector.classify(99, frozenset({
            ("RPTCURR", 99), ("RPTTEMP", 100),
        }))
        assert "Unknown" in result.name

    def test_classify_empty_signature(self) -> None:
        """验证空签名返回 Empty_Device."""
        result = TypeDetector.classify(5, frozenset())
        assert result.name == "Empty_Device"

    def test_classify_partial_match_v2(self) -> None:
        """验证子集匹配 — 额外 (func,tp) 对不影响匹配."""
        result = TypeDetector.classify(7, frozenset({
            ("RPTCURR", 8), ("RPTCURR", 9), ("RPTCURR", 10),
            ("RPTCURR", 99),  # 多余的未知 TP
        }))
        assert result.name == "BC01_Current_Board"


class TestTypeDetectorDiscoverV2:  # 发现方法测试组 (V2)
    """测试 TypeDetector.discover 方法 (V2: 过滤 RPTREGS)."""  # 类文档

    def test_discover_single_device_v2(self) -> None:
        """验证单设备发现 (V2)."""
        df = pd.DataFrame({
            "node_id": [2, 2],
            "slot": [0, 0],
            "func": ["RPTTEMP", "RPTTEMP"],
            "tp": [21, 24],
        })
        devices = TypeDetector.discover(df)
        assert len(devices) == 1
        assert devices[2].name == "S001_Seed_Source"

    def test_discover_filters_rptregs(self) -> None:
        """验证 RPTREGS 行被过滤 (V2)."""
        df = pd.DataFrame({
            "node_id": [2, 2, 2],
            "slot": [0, 0, 0],
            "func": ["RPTTEMP", "RPTTEMP", "RPTREGS"],  # 含 RPTREGS
            "tp": [21, 24, 100],
        })
        devices = TypeDetector.discover(df)
        # RPTREGS 行应被过滤，签名只含 (RPTTEMP,21) + (RPTTEMP,24)
        assert devices[2].name == "S001_Seed_Source"

    def test_discover_multiple_devices_v2(self) -> None:
        """验证多设备发现 (V2)."""
        df = pd.DataFrame({
            "node_id": [2, 2, 4, 4, 4],
            "slot": [0, 0, 0, 0, 0],
            "func": ["RPTTEMP", "RPTTEMP", "RPTCURR", "RPTCURR", "RPTCURR"],
            "tp": [21, 24, 8, 9, 10],
        })
        devices = TypeDetector.discover(df)
        assert len(devices) == 2
        assert 2 in devices
        assert 4 in devices

    def test_discover_empty_dataframe(self) -> None:
        """验证空 DataFrame 返回空字典."""
        df = pd.DataFrame(columns=["node_id", "slot", "func", "tp"])
        devices = TypeDetector.discover(df)
        assert len(devices) == 0

    def test_device_type_slots_preserved_v2(self) -> None:
        """验证 DeviceType 的 slots 属性包含实际 slot 值 (V2)."""
        df = pd.DataFrame({
            "node_id": [2, 2, 2],
            "slot": [0, 0, 3],  # slot 0 和 slot 3
            "func": ["RPTTEMP", "RPTTEMP", "RPTTEMP"],
            "tp": [21, 24, 21],
        })
        devices = TypeDetector.discover(df)
        assert devices[2].slots == frozenset({0, 3})
