"""应用全局常量、枚举和查找表 — 所有其他模块的基础."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值
from enum import Enum  # 枚举基类
from typing import ClassVar  # 类变量类型注解

# =============================================================================
# 应用元数据
# =============================================================================

APP_NAME: str = "Laser DAQ Annotation Tool"  # 应用显示名称
APP_VERSION: str = "0.1.0"  # 应用版本号
APP_ORG: str = "LaserDAQ"  # 组织名称（用于 QSettings）

# =============================================================================
# CSV 导入配置
# =============================================================================

REQUIRED_COLUMNS: list[str] = ["uptime", "node_id", "slot", "tc", "val"]  # 窄表必须包含的 5 列
PREVIEW_ROW_LIMIT: int = 100  # 预览表格默认显示行数

# =============================================================================
# 数据类型枚举
# =============================================================================

class DataType(Enum):
    """测量值在控制回路中的角色分类."""  # 枚举文档

    ACTUAL = "actual"    # 实际测量值（传感器读数）
    TARGET = "target"    # 目标值/设定值（指令值）
    OTHER = "other"      # 辅助量（如 TEC PWM 占空比、状态值）

# =============================================================================
# 已知物理量定义
# =============================================================================

class KnownQuantity:
    """固件已知会发出的 typecode 描述."""  # 类文档

    __slots__ = ("tc", "default_name", "default_unit", "default_type",
                 "func_group", "description")  # 固定属性集，节省内存

    def __init__(
        self, tc: int, default_name: str, default_unit: str,
        default_type: DataType, func_group: str, description: str = "",
    ) -> None:
        """初始化已知物理量条目.

        Args:
            tc: typecode 值（固件协议中的类型编码）
            default_name: 默认物理量名称（如 "C_ACTUAL"）
            default_unit: 默认单位（如 "mA"）
            default_type: 数据类型（ACTUAL/TARGET/OTHER）
            func_group: 所属功能组（"RPTCURR" 或 "RPTTEMP"）
            description: 中文描述
        """  # 参数文档
        self.tc = tc  # typecode 值
        self.default_name = default_name  # 默认物理量名称
        self.default_unit = default_unit  # 默认单位
        self.default_type = default_type  # 数据类型
        self.func_group = func_group  # 功能组
        self.description = description  # 描述

# 主物理量目录 — 以 typecode 为键索引
KNOWN_QUANTITIES: dict[int, KnownQuantity] = {
    1:  KnownQuantity(1,  "C_TARGET",   "mA",  DataType.TARGET, "RPTCURR", "电流目标值"),  # 电流目标
    2:  KnownQuantity(2,  "C_ACTUAL",   "mA",  DataType.ACTUAL, "RPTCURR", "电流实际值"),  # 电流实际
    3:  KnownQuantity(3,  "V_ACTUAL",   "mV",  DataType.ACTUAL, "RPTCURR", "LD电压"),      # LD 电压
    4:  KnownQuantity(4,  "PWR_mW",     "mW",  DataType.ACTUAL, "RPTCURR", "LD光功率"),    # LD 光功率
    5:  KnownQuantity(5,  "TEC_PWM",    "",    DataType.OTHER,  "RPTTEMP", "TEC PWM占空比"), # TEC PWM
    21: KnownQuantity(21, "T_ACTUAL_1", "C",   DataType.ACTUAL, "RPTTEMP", "温度传感器1"),  # 温度1
    24: KnownQuantity(24, "T_TEC",      "C",   DataType.OTHER,  "RPTTEMP", "TEC温度"),     # TEC 温度
    31: KnownQuantity(31, "LD_CURR",    "mA",  DataType.ACTUAL, "RPTCURR", "LD电流监测"),  # LD 电流监测
    32: KnownQuantity(32, "LD_VOLT",    "mV",  DataType.ACTUAL, "RPTCURR", "LD电压监测"),  # LD 电压监测
    33: KnownQuantity(33, "LD_POWER",   "mW",  DataType.ACTUAL, "RPTCURR", "LD功率监测"),  # LD 功率监测
}

# =============================================================================
# PD 功率预留
# =============================================================================

PD_PWR_NAME: str = "PD_PWR"  # PD 功率物理量名（固件尚未实现）
PD_PWR_UNIT: str = "mW"  # PD 功率单位

# =============================================================================
# 设备类型签名
# =============================================================================

# 键 = 设备所有 slot 的 tc 值并集（frozenset）
# 值 = (显示名称, 描述)
DEVICE_SIGNATURES: dict[frozenset[int], tuple[str, str]] = {
    frozenset({2, 5, 24}):   ("S001_Seed_Source",   "种子源（温度+TEC）"),  # 种子源
    frozenset({2, 3, 4}):    ("BC01_Current_Board",  "电流板（电流+电压+功率）"),  # 电流板
    frozenset({1, 2, 3, 4}): ("BC01_Current_Board",  "电流板（含目标电流）"),  # 带目标电流的电流板
}

# =============================================================================
# 单位选项
# =============================================================================

# 标注面板下拉列表中可选的单位
UNIT_OPTIONS: list[str] = ["mA", "mV", "mW", "C", ""]  # 空字符串表示无量纲

# =============================================================================
# 模板系统
# =============================================================================

TEMPLATE_DIR_NAME: str = ".laser_daq"  # 模板目录（用户主目录下）
TEMPLATE_SUBDIR: str = "templates"  # 模板子目录
AUTO_MATCH_THRESHOLD: float = 0.8  # 自动匹配阈值（签名重叠率）
