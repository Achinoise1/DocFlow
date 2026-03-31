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

from ui.main_window import MainWindow
from utils.logger import logger


def _check_unix_dependencies() -> None:
    """Linux/macOS 首次运行时检测 LibreOffice 与中文字体，在 stderr 打印提示。"""
    if sys.platform == 'win32':
        return
    try:
        from utils.libreoffice_manager import check_dependencies_and_warn
        check_dependencies_and_warn()
    except Exception:
        pass  # 检测本身不应阻断启动


def main():
    logger.info('DocFlow 启动')
    _check_unix_dependencies()

    app = QApplication(sys.argv)
    app.setApplicationName('DocFlow')
    app.setApplicationDisplayName('DocFlow - 文档转换工具')

    window = MainWindow()
    window.show()

    logger.info('主窗口已显示')
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
