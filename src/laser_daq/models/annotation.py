"""标注数据模型 — 用户为每个 (node, slot, tc) 分配的元数据."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from dataclasses import dataclass  # 数据类装饰器
from typing import Optional  # 可选类型

from laser_daq.constants import DataType, KNOWN_QUANTITIES, PD_PWR_NAME, PD_PWR_UNIT  # 导入常量


@dataclass
class Annotation:
    """用户为单个 typecode 定义的解释.

    Attributes:
        node_id: 设备节点 ID
        slot: 槽位索引
        tc: typecode 值
        name: 物理量名称（如 "C_ACTUAL"）
        unit: 测量单位（如 "mA", "C", ""）
        data_type: 控制回路中的角色（ACTUAL/TARGET/OTHER）
        include_in_training: 是否作为训练特征列
    """  # 数据类文档

    node_id: int  # 设备节点 ID
    slot: int  # 槽位索引
    tc: int  # typecode 值
    name: str = ""  # 物理量名称，默认为空
    unit: str = ""  # 测量单位，默认为空
    data_type: DataType = DataType.OTHER  # 数据类型，默认为 OTHER
    include_in_training: bool = True  # 默认纳入训练特征


class QuantityCatalog:
    """标注表单下拉选项的提供者.

    提供固件已知的默认值和用户可自定义的标签选项.
    所有方法均为静态方法，无需实例化.
    """  # 工具类文档

    @staticmethod
    def get_default_annotation(tc: int) -> Annotation:
        """根据 typecode 从 KNOWN_QUANTITIES 返回预填的 Annotation.

        node_id 和 slot 字段留为 0，由调用方填充.
        如果 tc 不在已知目录中，返回一个空的默认 Annotation.
        """  # 方法文档
        if tc in KNOWN_QUANTITIES:  # 查找已知物理量
            kq = KNOWN_QUANTITIES[tc]  # 获取 KnownQuantity 对象
            return Annotation(  # 构造 Annotation
                node_id=0,  # 调用方填充
                slot=0,  # 调用方填充
                tc=tc,  # typecode 值
                name=kq.default_name,  # 默认物理量名称
                unit=kq.default_unit,  # 默认单位
                data_type=kq.default_type,  # 默认数据类型
                include_in_training=True,  # 默认纳入训练
            )
        return Annotation(node_id=0, slot=0, tc=tc)  # 未知 tc，返回空标注

    @staticmethod
    def all_names() -> list[str]:
        """返回所有已知物理量名称列表，供下拉菜单使用.

        包含 KNOWN_QUANTITIES 中的名称 + 预留的 PD_PWR.
        """  # 方法文档
        names: list[str] = [kq.default_name for kq in KNOWN_QUANTITIES.values()]  # 收集所有已知名称
        names.append(PD_PWR_NAME)  # 添加 PD 功率预留名称
        return sorted(set(names))  # 去重排序后返回

    @staticmethod
    def units_for(name: str) -> list[str]:
        """返回给定物理量名称可用的单位选项列表.

        Args:
            name: 物理量名称（如 "C_ACTUAL"）

        Returns:
            单位字符串列表（如 ["mA", "A", "uA"]）
        """  # 方法文档
        # 按名称查找已知物理量
        for kq in KNOWN_QUANTITIES.values():  # 遍历所有已知物理量
            if kq.default_name == name:  # 名称匹配
                base_unit = kq.default_unit  # 获取默认单位
                # 根据默认单位返回合理的备选单位
                if base_unit == "mA":  # 电流类
                    return ["mA", "A", "uA"]  # 毫安/安/微安
                elif base_unit == "mV":  # 电压类
                    return ["mV", "V", "uV"]  # 毫伏/伏/微伏
                elif base_unit == "mW":  # 功率类
                    return ["mW", "W", "uW"]  # 毫瓦/瓦/微瓦
                elif base_unit == "C":  # 温度类
                    return ["C", "K", "F"]  # 摄氏/开尔文/华氏
                else:  # 其他
                    return [base_unit, ""]  # 返回默认单位和无量纲选项
        return ["mA", "mV", "mW", "C", ""]  # 未知名称，返回通用单位列表

    @staticmethod
    def target_for_actual(actual_name: str) -> Optional[str]:
        """给定一个 ACTUAL 物理量名，返回对应的 TARGET 物理量名.

        映射规则：名称中的 "ACTUAL" 替换为 "TARGET".
        例如 "C_ACTUAL" -> "C_TARGET", "T_ACTUAL_1" -> "T_TARGET_1".

        Args:
            actual_name: 实际值物理量名称

        Returns:
            对应的目标值名称，无匹配时返回 None
        """  # 方法文档
        if "ACTUAL" in actual_name:  # 名称中包含 ACTUAL
            return actual_name.replace("ACTUAL", "TARGET")  # 替换为 TARGET
        return None  # 无匹配
