"""设备类型发现 — 从原始数据分析识别设备类型."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

from PyQt6.QtCore import QObject, pyqtSignal  # Qt 基类和信号

from laser_daq.models.data_model import DataModel  # 数据模型
from laser_daq.models.device_type import DeviceType, TypeDetector  # 设备类型相关


class DiscoveryController(QObject):
    """分析已加载数据以识别设备类型.

    Signals:
        discovery_finished(device_types_dict)
    """  # 类文档

    discovery_finished = pyqtSignal(object)  # dict[int, DeviceType]

    def __init__(self, parent: QObject = None) -> None:
        """初始化 DiscoveryController.

        Args:
            parent: Qt 父对象
        """  # 构造函数文档
        super().__init__(parent)  # 调用基类构造

    def discover(self, data_model: DataModel) -> dict[int, DeviceType]:
        """对已加载数据运行设备类型检测.

        原地修改 data_model 并返回设备类型映射.

        Args:
            data_model: 已加载的 DataModel 实例

        Returns:
            node_id -> DeviceType 映射
        """  # 方法文档
        device_types: dict[int, DeviceType] = TypeDetector.discover(  # 调用静态发现方法
            data_model.raw_df,  # 传入原始 DataFrame
        )  # 获取设备类型映射
        data_model.set_device_types(device_types)  # 更新 DataModel
        self.discovery_finished.emit(device_types)  # 发射完成信号
        return device_types  # 返回结果
