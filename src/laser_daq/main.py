"""应用入口点 — 创建 QApplication 并显示 MainWindow."""  # 模块文档字符串

from __future__ import annotations  # 延迟注解求值

import sys  # 系统参数
from pathlib import Path  # 路径类型

from PyQt6.QtWidgets import QApplication  # Qt 应用
from PyQt6.QtCore import Qt  # Qt 常量
from PyQt6.QtGui import QFont  # 字体

from laser_daq.views.main_window import MainWindow  # 主窗口
from laser_daq.constants import APP_NAME, APP_ORG, get_qt_cjk_fonts  # 应用元数据 + 跨平台字体


def main() -> None:
    """应用主入口函数.

    创建 QApplication 实例，设置样式，显示主窗口，进入事件循环.
    """  # 函数文档
    # 启用高 DPI 缩放（Qt6 中默认启用，此处显式声明）
    QApplication.setHighDpiScaleFactorRoundingPolicy(  # 高 DPI 策略
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough  # 透传缩放
    )  # 高 DPI

    app = QApplication(sys.argv)  # 创建 QApplication
    app.setApplicationName(APP_NAME)  # 设置应用名
    app.setOrganizationName(APP_ORG)  # 设置组织名

    # 设置默认字体（跨平台：根据操作系统自动选择最佳 CJK 字体）
    cjk_fonts = get_qt_cjk_fonts()  # 获取当前平台字体列表
    font = QFont(cjk_fonts[0], 10)  # 首选字体，如 "Microsoft YaHei" / "PingFang SC" / "Noto Sans CJK SC"
    font.setStyleHint(QFont.StyleHint.SansSerif)  # 无此字体时回退到系统无衬线字体
    app.setFont(font)  # 全局字体

    # 全局样式表
    app.setStyleSheet("""  # Qt 样式表
        QMainWindow { background-color: #fafafa; }
        QGroupBox { font-weight: bold; padding-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
    """)  # 简洁样式

    # 创建并显示主窗口
    window = MainWindow()  # 实例化主窗口
    window.show()  # 显示窗口

    sys.exit(app.exec())  # 进入事件循环，退出时返回状态码


if __name__ == "__main__":  # 作为脚本直接执行
    main()  # 启动应用
