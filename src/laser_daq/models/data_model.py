"""核心状态容器 (V2) — 持有原始数据、标注和设别元数据.

本模块不导入任何 PyQt6 模块。所有方法均为纯 Python / pandas 操作。
控制器负责序列化所有变更，因此 V0.2 无需线程锁。
"""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from dataclasses import dataclass, field  # 数据类工具
from pathlib import Path  # 路径类型
from typing import Optional  # 可选类型

import pandas as pd  # 数据处理库

from laser_daq.constants import REQUIRED_COLUMNS, EXCLUDED_FUNC_GROUPS  # 必需列
from laser_daq.models.device_type import DeviceType  # 设备类型
from laser_daq.models.annotation import Annotation  # 标注


@dataclass
class DataModel:
    """应用状态根 — 所有控制器读写此单一实例.

    Attributes:
        source_path: 原始 CSV 文件路径（用于显示和重新导入）
        raw_df: 窄表 DataFrame (列: uptime, node_id, slot, func, tp, val_float)
        device_types: node_id -> DeviceType 映射
        annotations: (node_id, slot, func_group, tp) -> Annotation 映射 (V2 新增 func_group)
        template_applied: 自动填充标注的模板名称（如有）
    """  # 数据类文档

    source_path: Optional[Path] = None  # 源文件路径
    raw_df: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())  # 原始数据
    device_types: dict[int, DeviceType] = field(default_factory=dict)  # 设备类型
    annotations: dict[tuple[int, int, str, int], Annotation] = field(default_factory=dict)  # 标注 (V2 key)
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

    def set_annotation(self, node_id: int, slot: int, func_group: str, tp: int,
                       annotation: Annotation) -> None:
        """设置单个 (node_id, slot, func_group, tp) 的标注.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            func_group: 功能组 ("RPTCURR", "RPTTEMP")
            tp: 类型码值
            annotation: 标注对象
        """  # 方法文档
        key = (node_id, slot, func_group, tp)  # V2 四元组键
        self.annotations[key] = annotation  # 存入字典

    def set_annotations(self, annotations: dict[tuple[int, int, str, int],
                                                 Annotation]) -> None:
        """批量设置标注（用于模板自动匹配）.

        Args:
            annotations: (node_id, slot, func_group, tp) -> Annotation 映射
        """  # 方法文档
        self.annotations.update(annotations)  # 合并到现有字典

    # =========================================================================
    # 查询方法（由视图和控制器调用）
    # =========================================================================

    def get_annotation(self, node_id: int, slot: int, func_group: str, tp: int
                       ) -> Optional[Annotation]:
        """获取单个标注.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            func_group: 功能组
            tp: 类型码值

        Returns:
            Annotation 对象，不存在时返回 None
        """  # 方法文档
        return self.annotations.get((node_id, slot, func_group, tp))  # 字典查找

    def get_annotations_for_slot(self, node_id: int, slot: int
                                 ) -> dict[tuple[str, int], Annotation]:
        """获取指定 slot 的所有标注，键为 (func_group, tp).

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引

        Returns:
            (func_group, tp) -> Annotation 映射
        """  # 方法文档
        result: dict[tuple[str, int], Annotation] = {}  # 结果字典
        for (n, s, func, tp), ann in self.annotations.items():  # 遍历所有标注
            if n == node_id and s == slot:  # 匹配 node 和 slot
                result[(func, tp)] = ann  # 添加到结果
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

    def get_tp_signature(self, node_id: int) -> frozenset[tuple[str, int]]:
        """返回指定设备所有 slot 的 (func, tp) 对并集 (V2).

        自动过滤 RPTREGS 等非测量功能组.

        Args:
            node_id: 设备节点 ID

        Returns:
            (func, tp) 对 frozenset
        """  # 方法文档
        if self.raw_df.empty:  # 无数据
            return frozenset()  # 返回空集合
        mask = (self.raw_df["node_id"] == node_id)  # 筛选该 node 的行
        active_df = self.raw_df.loc[mask]  # 复制子集
        active_df = active_df[~active_df["func"].isin(EXCLUDED_FUNC_GROUPS)]  # 过滤 RPTREGS
        tp_pairs = list(zip(active_df["func"], active_df["tp"]))  # (func, tp) 对
        return frozenset(tp_pairs)  # 返回不可变签名

    def get_unique_combinations(self) -> pd.DataFrame:
        """返回 (node_id, slot, func, tp) 去重组合及其行数统计 (V2).

        Returns:
            包含 node_id, slot, func, tp, count 列的 DataFrame
        """  # 方法文档
        if self.raw_df.empty:  # 无数据
            return pd.DataFrame(columns=["node_id", "slot", "func", "tp", "count"])
        return (
            self.raw_df.groupby(["node_id", "slot", "func", "tp"])  # V2: 四列分组
            .size()
            .reset_index(name="count")
        )

    def get_slot_data(self, node_id: int, slot: int, func_group: Optional[str] = None
                      ) -> pd.DataFrame:
        """返回指定 (node_id, slot) 的所有行数据副本 (V2).

        自动过滤 RPTREGS 行. 可选按 func_group 进一步筛选.

        Args:
            node_id: 设备节点 ID
            slot: 槽位索引
            func_group: 可选的功能组筛选 ("RPTCURR" / "RPTTEMP")

        Returns:
            筛选后的 DataFrame 副本
        """  # 方法文档
        if self.raw_df.empty:  # 无数据
            return pd.DataFrame()
        mask = (self.raw_df["node_id"] == node_id) & (self.raw_df["slot"] == slot)  # 基本筛选
        # 过滤 RPTREGS
        mask &= ~self.raw_df["func"].isin(EXCLUDED_FUNC_GROUPS)  # 排除非测量数据
        if func_group:  # 指定了功能组
            mask &= self.raw_df["func"] == func_group  # 进一步筛选
        return self.raw_df.loc[mask].copy()  # 返回副本

    # =========================================================================
    # 验证方法
    # =========================================================================

    @staticmethod
    def validate_columns(df: pd.DataFrame) -> list[str]:
        """检查 DataFrame 是否包含所有必需列 (V2: 6 列).

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
