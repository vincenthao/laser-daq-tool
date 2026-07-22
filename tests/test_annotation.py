"""测试 QuantityCatalog (V2) — 标注下拉选项提供者."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

import pytest  # 测试框架

from laser_daq.models.annotation import Annotation, QuantityCatalog  # 被测模块
from laser_daq.constants import DataType  # 数据类型


class TestQuantityCatalogDefaults:  # 默认值测试组
    """测试 get_default_annotation 方法 (V2: 用 func+tp 查找)."""  # 类文档

    def test_known_rptcurr_returns_default(self) -> None:
        """验证已知 RPTCURR tp=8 返回正确的默认标注."""
        ann = QuantityCatalog.get_default_annotation("RPTCURR", 8)  # (func, tp)
        assert ann.name == "C_ACTUAL"  # 应为电流实际值
        assert ann.unit == "mA"  # 单位毫安
        assert ann.data_type == DataType.ACTUAL  # 类型为实际值

    def test_target_tp_returns_target_type(self) -> None:
        """验证目标值 tp 返回 TARGET 类型 (V2: RPTCURR tp=14)."""
        ann = QuantityCatalog.get_default_annotation("RPTCURR", 14)  # 电流目标值
        assert ann.name == "C_TARGET"
        assert ann.data_type == DataType.TARGET

    def test_other_tp_returns_other_type(self) -> None:
        """验证辅助值 tp 返回 OTHER 类型 (V2: RPTTEMP tp=24)."""
        ann = QuantityCatalog.get_default_annotation("RPTTEMP", 24)  # TEC 占空比
        assert ann.name == "TEC_PWM"
        assert ann.data_type == DataType.OTHER

    def test_unknown_tp_returns_empty(self) -> None:
        """验证未知 (func, tp) 返回空标注."""
        ann = QuantityCatalog.get_default_annotation("RPTCURR", 99)  # 不存在
        assert ann.name == ""
        assert ann.unit == ""

    def test_temperature_tp(self) -> None:
        """验证温度 tp=21 的默认值 (V2: RPTTEMP)."""
        ann = QuantityCatalog.get_default_annotation("RPTTEMP", 21)
        assert ann.name == "T1_ACTUAL"
        assert ann.unit == "C"

    def test_ld_power_tp(self) -> None:
        """验证 LD 光功率 tp=11 (V2 新增)."""
        ann = QuantityCatalog.get_default_annotation("RPTCURR", 11)
        assert ann.name == "P_LD"
        assert ann.unit == "mW"

    def test_tec_tps(self) -> None:
        """验证 TEC 相关 tp (V2 新增: 25,26,27)."""
        ann_i = QuantityCatalog.get_default_annotation("RPTTEMP", 25)
        assert ann_i.name == "TEC_I"
        assert ann_i.unit == "mA"

        ann_v = QuantityCatalog.get_default_annotation("RPTTEMP", 26)
        assert ann_v.name == "TEC_V"
        assert ann_v.unit == "mV"

        ann_p = QuantityCatalog.get_default_annotation("RPTTEMP", 27)
        assert ann_p.name == "TEC_P"
        assert ann_p.unit == "mW"


class TestQuantityCatalogLookups:  # 查找方法测试组
    """测试 all_names, units_for, target_for_actual (V2)."""  # 类文档

    def test_all_names_includes_v2_quantities(self) -> None:
        """验证 all_names 包含 V2 新增的物理量."""
        names = QuantityCatalog.all_names()
        assert "C_ACTUAL" in names
        assert "C_TARGET" in names
        assert "P_SUMP" in names  # V2 新增: 功率 I×V
        assert "P_LD" in names  # V2 新增: LD 光功率
        assert "V_DRIVE" in names  # V2 新增: 驱动电压
        assert "V_VCE" in names  # V2 新增: VCE 电压
        assert "T1_ACTUAL" in names  # V2: 替代 T_ACTUAL_1
        assert "T2_ACTUAL" in names  # V2 新增
        assert "T3_ACTUAL" in names  # V2 新增
        assert "TEC_I" in names  # V2 新增
        assert "TEC_V" in names  # V2 新增
        assert "TEC_P" in names  # V2 新增
        assert "PD_PWR" in names  # 预留

    def test_all_names_no_duplicates(self) -> None:
        """验证 all_names 无重复项."""
        names = QuantityCatalog.all_names()
        assert len(names) == len(set(names))

    def test_target_for_actual_current(self) -> None:
        """验证 C_ACTUAL 对应 C_TARGET."""
        result = QuantityCatalog.target_for_actual("C_ACTUAL")
        assert result == "C_TARGET"

    def test_target_for_actual_no_match(self) -> None:
        """验证无 ACTUAL 的名称返回 None."""
        result = QuantityCatalog.target_for_actual("TEC_PWM")
        assert result is None

    def test_units_for_current(self) -> None:
        """验证电流物理量的单位选项."""
        units = QuantityCatalog.units_for("C_ACTUAL")
        assert "mA" in units
        assert "A" in units
        assert "uA" in units
