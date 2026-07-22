# 激光数据标注与训练集生成工具

MCXN947 采集数据的上位机标注工具——导入窄表 CSV、人工标注物理量含义、按设备类型分组导出 ML 训练用宽表 CSV。

## 功能

- **CSV 导入** — 拖拽或浏览，自动验证列结构，去重
- **设备自动发现** — 扫描 TC 签名，识别 S001 种子源 / BC01 电流板
- **物理量标注** — 名称/单位/数据类型/是否纳入训练特征
- **模板系统** — JSON 模板保存/加载/自动匹配 (V0.2+)
- **宽表导出** — 按设备类型分组，自动计算偏差，PD 功率预留
- **时序图表** — matplotlib 嵌入，实际值/目标值/偏差对比 (V0.3+)

## 快速开始

### 环境要求

- Python ≥ 3.10
- 依赖安装：

```bash
git clone <repo-url>
cd laser-daq-tool
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
# .venv\Scripts\activate     # Windows
pip install -e .
```

### 启动

```bash
laser-daq            # 终端命令
# 或
python -m laser_daq   # 模块方式
```

### 运行测试

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### 打包

```bash
# Linux
pip install pyinstaller
python -m PyInstaller laser_daq.spec --clean --noconfirm
# 产物: dist/laser-daq-tool

# Windows
scripts\build.bat
# 产物: dist\laser-daq-tool.exe
```

## 项目结构

```
src/laser_daq/
├── models/          # 纯 Python 数据模型（零 Qt 依赖）
├── controllers/     # QObject 业务逻辑
├── views/           # PyQt6 控件
└── workers/         # QThread 阻塞 I/O
tests/               # pytest 测试
resources/           # 样本数据
```

## 开发阶段

| 版本 | 功能 | 状态 |
|------|------|:--:|
| V0.1 | CSV 导入 + 表格预览 + 手动标注 + 宽表导出 | ✅ |
| V0.2 | 模板保存/加载/自动匹配 | 🔜 |
| V0.3 | 时序图表 + 统计摘要 | 🔜 |
| V0.4 | PD 功率列预留 + 多模板管理 | 🔜 |
| V1.0 | 打包 + 安装包 + 用户文档 | 🔜 |

## 技术栈

| 层 | 技术 |
|----|------|
| GUI | PyQt6 |
| 数据处理 | pandas |
| 图表 | matplotlib |
| 模板存储 | JSON |
| 打包分发 | PyInstaller |

## 许可证

MIT
