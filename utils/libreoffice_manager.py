"""LibreOffice 检测工具（macOS / Linux 专用）

在 Windows 上本模块不会被调用，仅作为占位。
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# ── 检测 ─────────────────────────────────────────────────────────────────────


def find_soffice() -> str | None:
    """查找 LibreOffice soffice 可执行文件，返回绝对路径，未找到返回 None"""
    if sys.platform == 'darwin':
        candidates = [
            '/Applications/LibreOffice.app/Contents/MacOS/soffice',
            str(Path.home() / 'Applications' / 'LibreOffice.app'
                / 'Contents' / 'MacOS' / 'soffice'),
            shutil.which('soffice'),
            shutil.which('libreoffice'),
        ]
    else:  # Linux
        candidates = [
            shutil.which('libreoffice'),
            shutil.which('soffice'),
            '/usr/bin/libreoffice',
            '/usr/bin/soffice',
            '/usr/local/bin/libreoffice',
            '/snap/bin/libreoffice',
            str(Path.home() / '.local' / 'bin' / 'libreoffice'),
        ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def is_installed() -> bool:
    """返回 LibreOffice 是否已安装"""
    return find_soffice() is not None


# ── 中文字体检测 ──────────────────────────────────────────────────────────────

# 用于 fc-list 搜索的中文字体关键词
_CHINESE_FONT_KEYWORDS = (
    'CJK', 'Noto Sans CJK', 'Noto Serif CJK',
    'WenQuanYi', 'Source Han', 'SimSun', 'SimHei',
    'Microsoft YaHei', 'PingFang', 'Songti', 'Heiti',
    'STSong', 'STHeiti', 'STFangsong', 'STKaiti',
    'AR PL', 'TW-MOE',
)


def has_chinese_font() -> bool:
    """检测系统是否安装了中文字体（通过 fc-list 查询）。

    Returns:
        True 表示找到至少一个中文字体；False 表示未找到或 fc-list 不可用。
    """
    if sys.platform == 'win32':
        # Windows 通常自带中文字体，此函数不应被调用
        return True

    fc_list = shutil.which('fc-list')
    if not fc_list:
        # 无法检测，保守起见返回 True（不误报）
        return True

    try:
        result = subprocess.run(
            [fc_list, ':lang=zh'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return bool(result.stdout.strip())
    except Exception:
        return True  # 检测失败时不误报


def _get_script_dir() -> Path:
    """返回安装脚本所在目录（PyInstaller frozen 与普通运行均兼容）。"""
    if getattr(sys, 'frozen', False):
        # onedir: sys.executable 在 dist/DocFlow/DocFlow，脚本在同级目录
        return Path(sys.executable).parent
    # 开发模式：脚本在项目根目录
    return Path(__file__).parent.parent


def check_dependencies_and_warn() -> dict[str, bool]:
    """检测 LibreOffice 与中文字体，在控制台打印友好提示。

    Returns:
        {'libreoffice': bool, 'chinese_font': bool}
    """
    if sys.platform == 'win32':
        return {'libreoffice': True, 'chinese_font': True}

    script_dir = _get_script_dir()
    result: dict[str, bool] = {}

    lo_ok = is_installed()
    result['libreoffice'] = lo_ok
    if not lo_ok:
        lo_script = script_dir / 'install_libreoffice.sh'
        print(
            '\n[DocFlow] 未检测到 LibreOffice。\n'
            '  请先安装 LibreOffice，再启动本程序。\n'
            f'  快速安装方式：  bash "{lo_script}"\n'
            '  或访问 https://www.libreoffice.org/download/ 手动下载安装。\n',
            file=sys.stderr,
        )

    font_ok = has_chinese_font()
    result['chinese_font'] = font_ok
    if not font_ok:
        font_script = script_dir / 'install_fonts.sh'
        print(
            '\n[DocFlow] 未检测到中文字体，文档中文字符可能显示为方块（□）。\n'
            f'  快速安装中文字体：  bash "{font_script}"\n',
            file=sys.stderr,
        )

    return result
