"""应用全局常量、枚举和查找表 — 所有其他模块的基础."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值
from enum import Enum  # 枚举基类
from typing import ClassVar  # 类变量类型注解
import platform  # 操作系统检测
from pathlib import Path  # 路径类型（字体文件查找）

# =============================================================================
# 跨平台配置
# =============================================================================

def get_qt_cjk_fonts() -> list[str]:
    """返回当前平台适合 QFont 使用的 CJK 字体名称列表.

    按优先级排序，Qt 会自动回退到列表中的下一个可用字体.

    Returns:
        字体名称列表，第一个为最佳选择
    """  # 函数文档
    system = platform.system()  # 检测操作系统
    if system == "Windows":  # Windows 平台
        return ["Microsoft YaHei", "SimHei", "SimSun", "sans-serif"]  # 微软雅黑 > 黑体 > 宋体
    elif system == "Darwin":  # macOS 平台
        return ["PingFang SC", "Heiti SC", "STHeiti", "sans-serif"]  # 苹方 > 黑体 > 华文黑体
    else:  # Linux 及其他平台
        return ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "DejaVu Sans", "sans-serif"]  # 思源 > 文泉驿


def get_mpl_cjk_fonts() -> list[str]:
    """返回当前平台适合 matplotlib rcParams 使用的 CJK 字体列表.

    按优先级排序.

    Returns:
        字体名称列表
    """  # 函数文档
    system = platform.system()  # 检测操作系统
    if system == "Windows":  # Windows 平台
        return ["Microsoft YaHei", "SimHei", "DejaVu Sans", "sans-serif"]  # 微软雅黑 > 黑体
    elif system == "Darwin":  # macOS 平台
        return ["PingFang SC", "Heiti SC", "DejaVu Sans", "sans-serif"]  # 苹方 > 黑体
    else:  # Linux 及其他平台
        return ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "DejaVu Sans", "sans-serif"]  # 思源 > 文泉驿


def try_register_mpl_font() -> bool:
    """尝试向 matplotlib 注册系统 CJK 字体文件.

    Linux 上 Noto Sans CJK 需要手动注册 .ttc 文件路径，
    Windows/macOS 上系统字体通常已被 matplotlib 自动发现.

    Returns:
        True 表示成功注册了额外字体
    """  # 函数文档
    system = platform.system()  # 检测操作系统
    if system != "Linux":  # Windows/macOS 系统字体自动可用
        return False  # 无需手动注册
    try:  # 尝试导入 matplotlib 字体管理器
        import matplotlib.font_manager as fm  # 字体管理器
        _linux_candidate_paths = [  # Linux 上常见的 Noto CJK 字体路径
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Debian/Ubuntu 默认
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",  # 部分发行版
            "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",  # openSUSE 等
            "/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf",  # 单个 OTF 变体
        ]  # 候选路径列表
        for fp in _linux_candidate_paths:  # 遍历尝试
            if Path(fp).exists():  # 文件存在
                fm.fontManager.addfont(fp)  # 注册到 matplotlib
                return True  # 注册成功
        return False  # 未找到可用字体文件
    except ImportError:  # matplotlib 未安装
        return False  # 无法注册

# =============================================================================
# 应用元数据
# =============================================================================

APP_NAME: str = "Laser DAQ Annotation Tool"  # 应用显示名称
APP_VERSION: str = "0.2.0"  # 应用版本号（V2 CSV 格式适配）
APP_ORG: str = "LaserDAQ"  # 组织名称（用于 QSettings）

# =============================================================================
# CSV 导入配置 (V2 格式 — K64 主动上报)
# =============================================================================

# V2 窄表必须包含的 6 列
# func: 功能组 (RPTCURR=电流主动上报, RPTTEMP=温度主动上报, RPTREGS=寄存器读响应)
# tp:   类型码 (0~27)，与 func 一起唯一确定物理量
# val_float: IEEE 754 单精度浮点值
REQUIRED_COLUMNS: list[str] = ["uptime", "node_id", "slot", "func", "tp", "val_float"]  # V2 格式 6 列
PREVIEW_ROW_LIMIT: int = 100  # 预览表格默认显示行数

# 需要过滤掉的功能组（这些不是测量数据）
EXCLUDED_FUNC_GROUPS: list[str] = ["RPTREGS"]  # 寄存器读响应，不是主动上报数据

# =============================================================================
# 数据类型枚举
# =============================================================================

class DataType(Enum):
    """测量值在控制回路中的角色分类."""  # 枚举文档

    ACTUAL = "actual"    # 实际测量值（传感器读数）
    TARGET = "target"    # 目标值/设定值（指令值）
    OTHER = "other"      # 辅助量（如 TEC PWM 占空比、状态值）

# =============================================================================
# 已知物理量定义 (V2: 用 func+tp 组合键)
# =============================================================================

class KnownQuantity:
    """固件已知会发出的类型码 (func, tp) 描述."""  # 类文档

    __slots__ = ("tp", "default_name", "default_unit", "default_type",
                 "func_group", "description")  # 固定属性集，节省内存

    def __init__(
        self, tp: int, default_name: str, default_unit: str,
        default_type: DataType, func_group: str, description: str = "",
    ) -> None:
        """初始化已知物理量条目.

        Args:
            tp: 类型码值 (0~27，与 func_group 一起唯一确定物理量)
            default_name: 默认物理量名称（如 "C_ACTUAL"）
            default_unit: 默认单位（如 "mA"）
            default_type: 数据类型（ACTUAL/TARGET/OTHER）
            func_group: 所属功能组（"RPTCURR", "RPTTEMP"）
            description: 中文描述
        """  # 参数文档
        self.tp = tp  # 类型码值
        self.default_name = default_name  # 默认物理量名称
        self.default_unit = default_unit  # 默认单位
        self.default_type = default_type  # 数据类型
        self.func_group = func_group  # 功能组
        self.description = description  # 描述

# 主物理量目录 — 以 (func, tp) 为键索引 (V2 格式)
KNOWN_QUANTITIES: dict[tuple[str, int], KnownQuantity] = {
    # ---- RPTCURR (func=RPTCURR) — 电流类主动上报 ----
    ("RPTCURR",  0):  KnownQuantity(0,  "C_RAW",     "mA", DataType.ACTUAL, "RPTCURR", "电流原始值"),    # 电流原始
    ("RPTCURR",  8):  KnownQuantity(8,  "C_ACTUAL",  "mA", DataType.ACTUAL, "RPTCURR", "LD电流采样值"),   # LD 电流
    ("RPTCURR",  9):  KnownQuantity(9,  "V_ACTUAL",  "mV", DataType.ACTUAL, "RPTCURR", "LD电压"),        # LD 电压
    ("RPTCURR", 10):  KnownQuantity(10, "P_SUMP",    "mW", DataType.ACTUAL, "RPTCURR", "功率I×V"),       # I×V 功率
    ("RPTCURR", 11):  KnownQuantity(11, "P_LD",      "mW", DataType.ACTUAL, "RPTCURR", "LD光功率"),      # LD 光功率
    ("RPTCURR", 12):  KnownQuantity(12, "V_DRIVE",   "mV", DataType.ACTUAL, "RPTCURR", "驱动电压"),      # 驱动电压
    ("RPTCURR", 13):  KnownQuantity(13, "V_VCE",     "mV", DataType.ACTUAL, "RPTCURR", "VCE电压"),       # VCE 电压
    ("RPTCURR", 14):  KnownQuantity(14, "C_TARGET",  "mA", DataType.TARGET, "RPTCURR", "电流目标值"),    # 电流目标

    # ---- RPTTEMP (func=RPTTEMP) — 温度类主动上报 ----
    ("RPTTEMP",  0):  KnownQuantity(0,  "T_RAW",     "C",  DataType.ACTUAL, "RPTTEMP", "温度原始值"),    # 温度原始
    ("RPTTEMP", 21):  KnownQuantity(21, "T1_ACTUAL", "C",  DataType.ACTUAL, "RPTTEMP", "T1温度采样值"),  # T1 温度
    ("RPTTEMP", 22):  KnownQuantity(22, "T2_ACTUAL", "C",  DataType.ACTUAL, "RPTTEMP", "T2温度/湿度"),   # T2 温度
    ("RPTTEMP", 23):  KnownQuantity(23, "T3_ACTUAL", "C",  DataType.ACTUAL, "RPTTEMP", "T3温度"),        # T3 温度
    ("RPTTEMP", 24):  KnownQuantity(24, "TEC_PWM",   "",   DataType.OTHER,  "RPTTEMP", "TEC占空比"),     # TEC 占空比
    ("RPTTEMP", 25):  KnownQuantity(25, "TEC_I",     "mA", DataType.ACTUAL, "RPTTEMP", "TEC电流"),       # TEC 电流
    ("RPTTEMP", 26):  KnownQuantity(26, "TEC_V",     "mV", DataType.ACTUAL, "RPTTEMP", "TEC电压"),       # TEC 电压
    ("RPTTEMP", 27):  KnownQuantity(27, "TEC_P",     "mW", DataType.ACTUAL, "RPTTEMP", "TEC功率"),       # TEC 功率
}

# =============================================================================
# PD 功率预留
# =============================================================================

PD_PWR_NAME: str = "PD_PWR"  # PD 功率物理量名（固件尚未实现）
PD_PWR_UNIT: str = "mW"  # PD 功率单位

# =============================================================================
# 设备类型签名 (V2: 用 (func, tp) 对签名)
# =============================================================================

# 键 = 设备所有 slot 的 (func, tp) 对并集（frozenset）
# 值 = (显示名称, 描述)
DEVICE_SIGNATURES: dict[frozenset[tuple[str, int]], tuple[str, str]] = {
    frozenset({("RPTTEMP", 21), ("RPTTEMP", 24)}):
        ("S001_Seed_Source",   "种子源（温度+TEC）"),  # 种子源
    frozenset({("RPTCURR", 8), ("RPTCURR", 9), ("RPTCURR", 10)}):
        ("BC01_Current_Board",  "电流板（电流+电压+功率I×V）"),  # 电流板（无目标值）
    frozenset({("RPTCURR", 8), ("RPTCURR", 9), ("RPTCURR", 10), ("RPTCURR", 14)}):
        ("BC01_Current_Board",  "电流板（含目标电流）"),  # 电流板（含目标电流）
    # 扩展：含 LD 光功率的电流板
    frozenset({("RPTCURR", 8), ("RPTCURR", 9), ("RPTCURR", 10), ("RPTCURR", 11), ("RPTCURR", 14)}):
        ("BC01_Current_Board",  "电流板（含光功率）"),  # 电流板（含 LD 光功率）
    # v2 固件：激光器（电流+T1/T2/T3+TEC）
    frozenset({("RPTCURR", 8), ("RPTCURR", 14),
               ("RPTTEMP", 21), ("RPTTEMP", 22),
               ("RPTTEMP", 23), ("RPTTEMP", 24)}):
        ("Laser",  "激光器（电流+温度+TEC）"),  # 激光器 v2 固件
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
