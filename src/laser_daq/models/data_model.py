"""核心状态容器 — 持有原始数据、标注和设别元数据.

本模块不导入任何 PyQt6 模块。 所有方法均为纯 Python / pandas 操作。
控制器负责序列化所有变更，因此 V0.1 无需线程锁。
"""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from dataclasses import dataclass, field  # 数据类工具
from pathlib import Path  # 路径类型
from typing import Optional  # 可选类型

import pandas as pd  # 数据处理库

from laser_daq.constants import REQUIRED_COLUMNS  # 必需列
from laser_daq.models.device_type import DeviceType  # 设备类型
from laser_daq.models.annotation import Annotation  # 标注


@dataclass
class DataModel:
    """应用状态根 — 所有控制器读写此单一实例.

    Attributes:
        source_path: 原始 CSV 文件路径（用于显示和重新导入）
        raw_df: 窄表 DataFrame（列: uptime, node_id, slot, tc, val）
        device_types: node_id -> DeviceType 映射
        annotations: (node_id, slot, tc) -> Annotation 映射
        template_applied: 自动填充标注的模板名称（如有）
    """  # 数据类文档

    source_path: Optional[Path] = None  # 源文件路径
    raw_df: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())  # 原始数据
    device_types: dict[int, DeviceType] = field(default_factory=dict)  # 设备类型
    annotations: dict[tuple[int, int, int], Annotation] = field(default_factory=dict)  # 标注
    template_applied: Optional[str] = None  # 应用的模板名

    # =========================================================================
    # 变更方法（由控制器调用）
    # =========================================================================

    def set_raw_data(self, df: pd.DataFrame, source: Path) -> None:
        """替换原始数据集.

        重置所有派生状态（device_types, annotations），因为上游数据已变更.

        Args:
            df: 已验证和去重后的 DataFrame
            source: 源文件路径
        """  # 方法文档
        self.source_path = source  # 记录源文件路径
        self.raw_df = df.copy()  # 复制数据以防外部修改
        self.device_types.clear()  # 清除旧设备类型
        self.annotations.clear()  # 清除旧标注
        self.template_applied = None  # 清除模板标记

    def set_device_types(self, types: dict[int, DeviceType]) -> None:
        """替换设备类型映射.

        Args:
            types: node_id -> DeviceType 映射字典
        """  # 方法文档
        self.device_types = dict(types)  # 复制字典

    def set_annotation(self, node_id: int, slot: int, tc: int,
                       annotation: Annotation) -> None:
        """设置单个 (node_id, slot, tc) 的标注.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            tc: typecode 值
            annotation: 标注对象
        """  # 方法文档
        key = (node_id, slot, tc)  # 构造键
        self.annotations[key] = annotation  # 存入字典

    def set_annotations(self, annotations: dict[tuple[int, int, int],
                                                 Annotation]) -> None:
        """批量设置标注（用于模板自动匹配）.

        Args:
            annotations: (node_id, slot, tc) -> Annotation 映射
        """  # 方法文档
        self.annotations.update(annotations)  # 合并到现有字典

    # =========================================================================
    # 查询方法（由视图和控制器调用）
    # =========================================================================

    def get_annotation(self, node_id: int, slot: int, tc: int
                       ) -> Optional[Annotation]:
        """获取单个标注.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            tc: typecode 值

        Returns:
            Annotation 对象，不存在时返回 None
        """  # 方法文档
        return self.annotations.get((node_id, slot, tc))  # 字典查找

    def get_annotations_for_slot(self, node_id: int, slot: int
                                 ) -> dict[int, Annotation]:
        """获取指定 slot 的所有标注，键为 tc.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引

        Returns:
            tc -> Annotation 映射
        """  # 方法文档
        result: dict[int, Annotation] = {}  # 结果字典
        for (n, s, tc), ann in self.annotations.items():  # 遍历所有标注
            if n == node_id and s == slot:  # 匹配 node 和 slot
                result[tc] = ann  # 添加到结果
        return result  # 返回结果

    def get_grouped_devices(self) -> dict[str, list[DeviceType]]:
        """按设备类型名称分组，用于导出.

        Returns:
            device_type_name -> [DeviceType, ...] 映射
        """  # 方法文档
        grouped: dict[str, list[DeviceType]] = {}  # 分组结果
        for dt in self.device_types.values():  # 遍历所有设备类型
            grouped.setdefault(dt.name, []).append(dt)  # 按名称分组
        return grouped  # 返回分组结果

    def get_tc_signature(self, node_id: int) -> frozenset[int]:
        """返回指定设备所有 slot 的 TC 值并集.

        用于模板匹配.

        Args:
            node_id: 设备节点 ID

        Returns:
            TC 值 frozenset
        """  # 方法文档
        if self.raw_df.empty:  # 无数据
            return frozenset()  # 返回空集合
        mask = self.raw_df["node_id"] == node_id  # 筛选该 node 的行
        return frozenset(self.raw_df.loc[mask, "tc"].unique())  # 返回唯一 TC 值集合

    def get_unique_combinations(self) -> pd.DataFrame:
        """返回 (node_id, slot, tc) 去重组合及其行数统计.

        Returns:
            包含 node_id, slot, tc, count 列的 DataFrame
        """  # 方法文档
        if self.raw_df.empty:  # 无数据
            return pd.DataFrame(columns=["node_id", "slot", "tc", "count"])  # 返回空 DataFrame
        return (  # 聚合统计
            self.raw_df.groupby(["node_id", "slot", "tc"])  # 按三列分组
            .size()  # 计算每组行数
            .reset_index(name="count")  # 重置索引并命名 count 列
        )

    def get_slot_data(self, node_id: int, slot: int) -> pd.DataFrame:
        """返回指定 (node_id, slot) 的所有行数据副本.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引

        Returns:
            筛选后的 DataFrame 副本
        """  # 方法文档
        if self.raw_df.empty:  # 无数据
            return pd.DataFrame()  # 返回空 DataFrame
        mask = (self.raw_df["node_id"] == node_id) & (self.raw_df["slot"] == slot)  # 筛选条件
        return self.raw_df.loc[mask].copy()  # 返回副本

    # =========================================================================
    # 验证方法
    # =========================================================================

    @staticmethod
    def validate_columns(df: pd.DataFrame) -> list[str]:
        """检查 DataFrame 是否包含所有必需列.

        Args:
            df: 待验证的 DataFrame

        Returns:
            缺失的列名列表（空列表表示验证通过）
        """  # 方法文档
        return [c for c in REQUIRED_COLUMNS if c not in df.columns]  # 检查缺失列

    @staticmethod
    def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
        """删除完全重复的行，保留首次出现.

        Args:
            df: 待去重的 DataFrame

        Returns:
            去重后的 DataFrame
        """  # 方法文档
        return df.drop_duplicates(keep="first")  # 保留首次出现

    # =========================================================================
    # 状态查询
    # =========================================================================

    @property
    def is_loaded(self) -> bool:
        """数据是否已加载（raw_df 非空）."""
        return not self.raw_df.empty  # 检查 DataFrame 是否非空
