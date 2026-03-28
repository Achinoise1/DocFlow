"""DocFlow - 本地离线文档转换工具"""
import sys
import os

# 确保项目根目录在 sys.path 中
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from utils.logger import logger


def load_stylesheet() -> str:
    """加载QSS样式表"""
    qss_path = os.path.join(BASE_DIR, 'resources', 'styles.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''


def main():
    logger.info('DocFlow 启动')

    # 高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName('DocFlow')
    app.setApplicationDisplayName('DocFlow - 文档转换工具')

    # 加载样式
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    window = MainWindow()
    window.show()

    logger.info('主窗口已显示')
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
