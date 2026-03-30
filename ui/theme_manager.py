"""主题管理器 - 封装 QSS 加载、主题持久化与切换逻辑"""
import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

# 主题名 → QSS 文件名映射
_QSS_FILES = {
    'dark':  'styles.qss',
    'light': 'styles_light.qss',
}

# 主题名 → 按钮图标字符映射
_ICONS = {
    'light': '🌙',
    'dark':  '☀️',
}


class ThemeManager:
    """管理应用主题的加载、切换与持久化。

    使用方：
        manager = ThemeManager(settings)
        current = manager.load_saved_theme()   # 读取上次保存的主题
        manager.apply(current)                 # 应用主题
        new_theme = manager.toggle(current)    # 点击切换按钮时调用
        icon = manager.get_button_icon(new_theme)
    """

    def __init__(self, settings: QSettings):
        self._settings = settings

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def load_saved_theme(self) -> str:
        """从 QSettings 读取上次保存的主题名，默认返回 'light'。"""
        return self._settings.value('theme', 'light')

    def apply(self, theme_name: str) -> None:
        """加载对应 QSS 并应用到当前 QApplication，同时持久化主题名。

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

        self._settings.setValue('theme', theme_name)

    def toggle(self, current_theme: str) -> str:
        """返回切换后的主题名（不执行 apply，调用方决定何时应用）。

        Args:
            current_theme: 当前主题名

        Returns:
            切换后的主题名
        """
        return 'dark' if current_theme == 'light' else 'light'

    def get_button_icon(self, theme_name: str) -> str:
        """返回主题切换按钮的图标字符。

        Args:
            theme_name: 当前主题名

        Returns:
            'light' → '🌙'（点击将切换到深色）
            'dark'  → '☀️'（点击将切换到浅色）
        """
        return _ICONS.get(theme_name, '🌙')

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
