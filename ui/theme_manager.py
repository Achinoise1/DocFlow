"""主题管理器 - 封装 QSS 加载与系统主题跟随逻辑"""
import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

# 主题名 → QSS 文件名映射
_QSS_FILES = {
    'dark':  'styles.qss',
    'light': 'styles_light.qss',
}


class ThemeManager:
    """管理应用主题的加载，自动跟随系统外观（深色/浅色）。

    使用方：
        manager = ThemeManager()
        manager.apply_system_theme()           # 应用当前系统主题
        # 监听系统主题变化
        QGuiApplication.styleHints().colorSchemeChanged.connect(
            lambda _: manager.apply_system_theme()
        )
    """

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def get_system_theme(self) -> str:
        """返回当前系统主题名（'dark' 或 'light'）。"""
        scheme = QGuiApplication.styleHints().colorScheme()
        return 'dark' if scheme == Qt.ColorScheme.Dark else 'light'

    def apply_system_theme(self) -> None:
        """检测系统外观并应用对应 QSS 到当前 QApplication。"""
        self.apply(self.get_system_theme())

    def apply(self, theme_name: str) -> None:
        """加载对应 QSS 并应用到当前 QApplication。

        Args:
            theme_name: 'light' 或 'dark'
        """
        base_dir = self._get_base_dir()
        qss_filename = _QSS_FILES.get(theme_name, _QSS_FILES['light'])
        qss_file = os.path.join(base_dir, 'resources', qss_filename)

        if os.path.exists(qss_file):
            with open(qss_file, 'r', encoding='utf-8') as f:
                qss_content = f.read()
            # PyInstaller 打包后 CWD 不包含 resources/，需将 url() 相对路径转为绝对路径
            if getattr(sys, 'frozen', False):
                resources_dir = os.path.join(base_dir, 'resources').replace('\\', '/')
                qss_content = qss_content.replace('url(resources/', f'url({resources_dir}/')
            QApplication.instance().setStyleSheet(qss_content)

    # ------------------------------------------------------------------
    # 私有辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _get_base_dir() -> str:
        """返回项目根目录（开发模式）或 _internal 目录（PyInstaller 打包模式）。"""
        if getattr(sys, 'frozen', False):
            # PyInstaller 6.x onedir: sys._MEIPASS 指向 _internal/ 目录
            return sys._MEIPASS
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
