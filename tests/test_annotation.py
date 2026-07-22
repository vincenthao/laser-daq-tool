"""测试 QuantityCatalog — 标注下拉选项提供者."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

import pytest  # 测试框架

from laser_daq.models.annotation import Annotation, QuantityCatalog  # 被测模块
from laser_daq.constants import DataType  # 数据类型


class TestQuantityCatalogDefaults:  # 默认值测试组
    """测试 get_default_annotation 方法."""  # 类文档

    def test_known_tc_returns_default(self) -> None:
        """验证已知 tc 返回正确的默认标注."""
        ann = QuantityCatalog.get_default_annotation(2)  # tc=2
        assert ann.name == "C_ACTUAL"  # 应为电流实际值
        assert ann.unit == "mA"  # 单位毫安
        assert ann.data_type == DataType.ACTUAL  # 类型为实际值
        assert ann.include_in_training is True  # 默认纳入训练

    def test_target_tc_returns_target_type(self) -> None:
        """验证目标值 tc 返回 TARGET 类型."""
        ann = QuantityCatalog.get_default_annotation(1)  # tc=1
        assert ann.name == "C_TARGET"  # 应为电流目标值
        assert ann.data_type == DataType.TARGET  # 类型为目标值

    def test_other_tc_returns_other_type(self) -> None:
        """验证辅助值 tc 返回 OTHER 类型."""
        ann = QuantityCatalog.get_default_annotation(5)  # tc=5 (TEC PWM)
        assert ann.name == "TEC_PWM"  # TEC PWM
        assert ann.data_type == DataType.OTHER  # 类型为其他

    def test_unknown_tc_returns_empty(self) -> None:
        """验证未知 tc 返回空标注."""
        ann = QuantityCatalog.get_default_annotation(99)  # 未知 tc
        assert ann.name == ""  # 名称为空
        assert ann.unit == ""  # 单位为空

    def test_temperature_tc(self) -> None:
        """验证温度 tc 的默认值."""
        ann = QuantityCatalog.get_default_annotation(21)  # tc=21 (温度传感器1)
        assert ann.name == "T_ACTUAL_1"  # 温度实际值1
        assert ann.unit == "C"  # 单位摄氏度


class TestQuantityCatalogLookups:  # 查找方法测试组
    """测试 all_names, units_for, target_for_actual."""  # 类文档

    def test_all_names_includes_known(self) -> None:
        """验证 all_names 包含所有已知物理量."""
        names = QuantityCatalog.all_names()  # 获取所有名称
        assert "C_ACTUAL" in names  # 电流实际
        assert "C_TARGET" in names  # 电流目标
        assert "V_ACTUAL" in names  # 电压实际
        assert "PWR_mW" in names  # 光功率
        assert "TEC_PWM" in names  # TEC PWM
        assert "T_ACTUAL_1" in names  # 温度1
        assert "T_TEC" in names  # TEC 温度
        assert "LD_CURR" in names  # LD 电流
        assert "LD_VOLT" in names  # LD 电压
        assert "LD_POWER" in names  # LD 功率

    def test_all_names_includes_pd_pwr(self) -> None:
        """验证 all_names 包含预留的 PD_PWR."""
        names = QuantityCatalog.all_names()  # 获取所有名称
        assert "PD_PWR" in names  # PD 功率应存在

    def test_all_names_no_duplicates(self) -> None:
        """验证 all_names 无重复项."""
        names = QuantityCatalog.all_names()  # 获取所有名称
        assert len(names) == len(set(names))  # 不应有重复

    def test_target_for_actual_current(self) -> None:
        """验证 C_ACTUAL 对应 C_TARGET."""
        result = QuantityCatalog.target_for_actual("C_ACTUAL")  # 查找目标
        assert result == "C_TARGET"  # 应为 C_TARGET

    def test_target_for_actual_temperature(self) -> None:
        """验证 T_ACTUAL_1 对应 T_TARGET_1."""
        result = QuantityCatalog.target_for_actual("T_ACTUAL_1")  # 查找
        assert result == "T_TARGET_1"  # 应替换 ACTUAL -> TARGET

    def test_target_for_actual_no_match(self) -> None:
        """验证无 ACTUAL 的名称返回 None."""
        result = QuantityCatalog.target_for_actual("TEC_PWM")  # 不是 actual
        assert result is None  # 应返回 None

    def test_units_for_current(self) -> None:
        """验证电流物理量的单位选项."""
        units = QuantityCatalog.units_for("C_ACTUAL")  # 获取单位
        assert "mA" in units  # 毫安
        assert "A" in units  # 安
        assert "uA" in units  # 微安
