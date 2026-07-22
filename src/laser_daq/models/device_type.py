"""设备类型识别 — 从 TC 签名推断设备类型."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from dataclasses import dataclass, field  # 数据类工具
from typing import Optional  # 可选类型

import pandas as pd  # 数据处理库

from laser_daq.constants import DEVICE_SIGNATURES  # 设备签名表


@dataclass(frozen=True)
class DeviceType:
    """标识一个物理设备（CSV 中的一个 node_id）.

    Attributes:
        node_id: 设备地址（来自 CSV）
        name: 人类可读的类型名（如 "S001_Seed_Source"）
        description: 简短中文描述
        slots: 数据中出现的 slot 索引集合
    """  # 数据类文档

    node_id: int  # 设备节点 ID
    name: str = "Unknown_Device"  # 未知设备默认名
    description: str = ""  # 描述
    slots: frozenset[int] = field(default_factory=frozenset)  # slot 集合（不可变）


class TypeDetector:
    """启发式分类器 — 将 TC 值集合映射到设备类型.

    使用设备签名表（DEVICE_SIGNATURES）进行最佳匹配.
    签名是基于一个设备所有 slot 的 TC 值并集.
    """  # 分类器文档

    # 空签名的设备将被标记为此名称
    UNKNOWN_NAME: str = "Unknown_Device"  # 未知设备常量

    @staticmethod
    def classify(node_id: int, tc_signature: frozenset[int]) -> DeviceType:
        """根据 TC 签名返回对应的 DeviceType.

        匹配策略：
        1. 精确匹配 DEVICE_SIGNATURES 中的签名
        2. 子集匹配 — 如果签名包含已知签名的所有 TC（可能还有额外 TC）
        3. 都不匹配则返回 "Unknown_Device"

        Args:
            node_id: 设备节点 ID
            tc_signature: 该设备所有 slot 的 TC 值并集

        Returns:
            包含分类结果的 DeviceType 实例
        """  # 方法文档
        if not tc_signature:  # 空签名（设备无数据）
            return DeviceType(node_id=node_id, name="Empty_Device",
                            description="无数据设备")  # 返回空设备标记

        # 步骤1：精确匹配
        if tc_signature in DEVICE_SIGNATURES:  # 精确命中
            name, desc = DEVICE_SIGNATURES[tc_signature]  # 获取名称和描述
            return DeviceType(node_id=node_id, name=name, description=desc)  # 返回分类结果

        # 步骤2：子集匹配 — 找最佳匹配
        best_match: Optional[tuple[str, str]] = None  # 最佳匹配（名称, 描述）
        best_overlap: int = 0  # 最佳重叠 TC 数量
        for sig, (name, desc) in DEVICE_SIGNATURES.items():  # 遍历所有已知签名
            overlap = len(sig & tc_signature)  # 计算交集大小
            if overlap > best_overlap:  # 更新最佳匹配
                best_overlap = overlap  # 新的最佳重叠数
                best_match = (name, desc)  # 新的最佳匹配

        if best_match and best_overlap >= 2:  # 至少 2 个 TC 匹配才算有效
            return DeviceType(node_id=node_id,
                            name=best_match[0],
                            description=best_match[1])  # 返回子集匹配结果

        # 步骤3：无匹配
        return DeviceType(  # 返回未知设备
            node_id=node_id,
            name=f"Unknown_Device_n{node_id}",  # 带 node_id 的唯一名称
            description=f"未知设备 (TC签名: {sorted(tc_signature)})",  # 包含签名信息帮助诊断
        )

    @staticmethod
    def discover(df: pd.DataFrame) -> dict[int, DeviceType]:
        """对 DataFrame 执行完整的设备发现流程.

        按 node_id 分组，为每个设备计算 TC 签名并调用 classify().

        Args:
            df: 包含 node_id, slot, tc 列的 DataFrame

        Returns:
            node_id -> DeviceType 的映射字典
        """  # 方法文档
        if df.empty:  # 空 DataFrame
            return {}  # 返回空字典

        device_types: dict[int, DeviceType] = {}  # 结果字典

        # 按 node_id 分组
        for node_id, group in df.groupby("node_id"):  # 遍历每个设备
            node_id_int = int(node_id)  # 确保 node_id 为 int 类型
            tc_set = frozenset(group["tc"].unique())  # 该设备所有唯一 TC 值
            slots = frozenset(group["slot"].unique())  # 该设备所有唯一 slot
            dtype = TypeDetector.classify(node_id_int, tc_set)  # 分类
            # 用实际 slots 替换分类结果中的 slots
            dtype = DeviceType(  # 创建新实例（frozen dataclass 需要替换）
                node_id=dtype.node_id,
                name=dtype.name,
                description=dtype.description,
                slots=slots,  # 使用数据中实际观察到的 slots
            )
            device_types[node_id_int] = dtype  # 存入映射

        return device_types  # 返回发现结果
