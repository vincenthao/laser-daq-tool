# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 将激光数据标注工具打包为独立可执行文件.

构建命令:
    pyinstaller laser_daq.spec          # 当前平台
    pyinstaller --windowed laser_daq.spec  # Windows 无控制台窗口

输出:
    dist/laser-daq-tool/laser-daq-tool[.exe] — 单文件可执行
"""  # 模块文档

import sys  # 系统模块
from pathlib import Path  # 路径处理

# ---- 项目根目录 ----
PROJECT_ROOT = Path('.')  # spec 文件所在目录

# ---- 隐藏导入（PyInstaller 可能无法自动检测的依赖）----
hidden_imports = [  # 需要显式声明的导入
    # PyQt6 平台插件
    'PyQt6.QtCore',  # Qt 核心
    'PyQt6.QtGui',  # Qt GUI
    'PyQt6.QtWidgets',  # Qt 控件

    # matplotlib 后端
    'matplotlib.backends.backend_qtagg',  # Qt6 Agg 后端
    'matplotlib.backends.backend_svg',  # SVG 后端（备用）

    # pandas 引擎
    'pandas._libs',  # pandas C 扩展
    'pandas.io',  # pandas I/O

    # 标准库（某些平台可能需要）
    'encodings',  # 编码支持
    'encodings.utf_8',  # UTF-8 编码（Windows 打包时需要）
    'encodings.gbk',  # GBK 编码（Windows 中文环境）
    'json',  # JSON 模板
]

# ---- 排除的模块（不打包以减小体积）----
excluded_modules = [  # 不需要打包的模块
    'tkinter',  # Tk GUI（只用 PyQt6）
    'PyQt5',  # Qt5（只用 Qt6）
    'IPython',  # 交互式解释器
    'jupyter',  # Jupyter
    'notebook',  # Jupyter Notebook
    'scipy',  # 科学计算（项目未使用）
    'numba',  # JIT 编译（未使用）
]

# ---- 数据文件（随 exe 一起打包）----
datas = [  # (源路径, 目标路径)
    (str(PROJECT_ROOT / 'src' / 'laser_daq' / 'constants.py'),
     'laser_daq'),  # 常量定义（运行时可能需要）
]

a = Analysis(  # 分析阶段
    # 入口脚本
    ['src/laser_daq/main.py'],  # 主入口

    # 路径搜索
    pathex=[str(PROJECT_ROOT / 'src')],  # 源码目录
    binaries=[],  # 额外的二进制文件（无需）
    datas=datas,  # 数据文件
    hiddenimports=hidden_imports,  # 隐藏导入
    hookspath=[],  # 自定义钩子路径
    hooksconfig={},  # 钩子配置
    runtime_hooks=[],  # 运行时钩子
    excludes=excluded_modules,  # 排除模块
    noarchive=False,  # 允许归档
    optimize=0,  # 不优化（保持可调试）
)

pyz = PYZ(a.pure)  # 编译字节码归档

# ---- EXE 配置 ----
exe = EXE(  # 可执行文件
    pyz,  # 字节码归档
    a.scripts,  # 脚本
    a.binaries,  # 二进制
    a.datas,  # 数据
    [],
    name='laser-daq-tool',  # 输出文件名（Windows 自动加 .exe）
    debug=False,  # 不含调试符号
    bootloader_ignore_signals=False,  # 正常处理信号
    strip=False,  # 保留符号信息
    upx=True,  # 启用 UPX 压缩（如果已安装）
    upx_exclude=[],  # 不排除任何文件
    runtime_tmpdir=None,  # 使用默认临时目录
    console=True,  # 显示控制台窗口（跨平台调试用，Windows 正式发布可改为 False）
    disable_windowed_traceback=False,  # 保留错误输出
    argv_emulation=False,  # macOS 用
    target_arch=None,  # 自动检测架构
    codesign_identity=None,  # 不签名
    entitlements_file=None,  # macOS 权限文件
    icon=None,  # 可设置应用图标路径
)
