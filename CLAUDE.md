## 项目说明

Laser DAQ Annotation Tool — 激光数据采集标注与训练集导出工具。
从 MCXN947 固件采集的 CSV 导入数据，标注物理量含义，导出为机器学习训练用的宽表 CSV。

### 硬件架构

- MCXN947 采集板，通过 K64 主动上报数据
- 一个激光器包含多个设备（node_id），每个设备有多个槽位（slot）
- node_id 区分不同的电路板（种子源、放大级等），slot 区分同一板上的不同通道
- 同一 (func, tp) 在不同 node_id 或 slot 下**物理含义不同**，需独立标注

### 数据格式 (V2)

CSV 表头：`uptime, node_id, slot, func, tp, tp_name, opcode, val_float, val_hex`

必需列（6 列）：`uptime, node_id, slot, func, tp, val_float`

func 功能组：
- `RPTCURR` — 电流主动上报（tp=8: I_ACT, tp=14: I_TGT）
- `RPTTEMP` — 温度主动上报（tp=21: T1, tp=22: T2, tp=23: T3, tp=24: TEC_DUTY）
- `RPTREGS` — 寄存器读响应（**非测量数据，全流程过滤**）

val_float：IEEE 754 单精度浮点，hex 转 float 时用大端字节序。

### 架构

MVC 三层：
```
src/laser_daq/
├── main.py              # QApplication 入口，跨平台字体配置
├── constants.py         # 全局常量、枚举、KNOWN_QUANTITIES、DEVICE_SIGNATURES
├── models/              # 纯 Python，不依赖 Qt
│   ├── data_model.py    # DataModel — 核心状态容器
│   ├── annotation.py    # Annotation + QuantityCatalog
│   └── device_type.py   # DeviceType + TypeDetector（签名匹配）
├── views/               # Qt 控件
│   ├── main_window.py   # 顶层窗口，信号接线中枢
│   ├── import_panel.py  # 拖拽区 + 浏览按钮
│   ├── device_tree.py   # 三级树：Device → Slot → (func, tp)
│   ├── preview_table.py # PandasModel → QTableView
│   ├── annotation_panel.py  # 标注表单
│   ├── chart_view.py    # matplotlib 嵌入式图表
│   ├── stats_panel.py   # 统计摘要表格
│   └── export_dialog.py # 导出设置对话框
├── controllers/         # 业务逻辑，线程管理
│   ├── import_controller.py
│   ├── discovery_controller.py
│   ├── annotation_controller.py
│   └── export_controller.py
└── workers/             # QThread 工作对象
    ├── import_worker.py
    └── export_worker.py
```

### DataModel 引用同步

DataModel 是单一实例，在 MainWindow 构造时创建，所有视图/控制器持有引用。
**导入完成后必须通过 `set_data_model()` 同步所有组件的引用**，否则会指向旧空模型。

当前已实现 `set_data_model()` 的组件：
- `ChartView`
- `StatsPanel`
- `AnnotationPanel`
- `ExportController`

### 设备类型识别

`TypeDetector.classify()` 基于 `(func, tp)` 签名匹配 `DEVICE_SIGNATURES`。
- 先精确匹配，再子集匹配（重叠 >= 2）
- 过滤 RPTREGS 后计算签名
- 当前已知签名：`S001_Seed_Source`、`BC01_Current_Board`（3 种变体）、`Laser`（v2 固件）

### 批量标注范围

"应用到本设备所有相同 (func, tp)" 按钮限定**当前 node_id** 范围内，不跨设备。
因为同一 (func, tp) 在不同 node_id 下对应不同物理量（如种子源 LD 电流 vs 放大级 LD 电流）。

## 编码规范

保持一致的代码风格，代码编写标准。

每行代码后面添加注释。

## 跨平台注意事项

- 字体：`constants.py` 中 `get_qt_cjk_fonts()` / `get_mpl_cjk_fonts()` / `try_register_mpl_font()` 自动适配 Windows/macOS/Linux
- 编码：CSV 读写统一使用 `encoding="utf-8"`
- 路径：统一使用 `pathlib.Path`
- PyInstaller：`laser_daq.spec` 中 `hidden_imports` 需包含 `encodings.utf_8`、`encodings.gbk`

## 任务处理规范

不进行任何代码修改，给出意见后，由主人确认后再修改代码。

修改完代码需要编译验证，打包生成可执行文件。

每次回复，最后面加上喵。
