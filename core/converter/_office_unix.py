"""macOS / Linux Office 转换器 - 使用 LibreOffice headless 进行转换

用户需提前安装 LibreOffice，或通过应用内置的自动安装向导安装：
  macOS:  brew install --cask libreoffice
  Ubuntu: sudo apt install libreoffice
  Fedora: sudo dnf install libreoffice

也支持便携式捆绑 LibreOffice + 中文字体（Linux），参见 scripts/setup_portable_libreoffice.sh
"""
import os
import subprocess
import tempfile
import threading
from utils.libreoffice_manager import (
    find_soffice,
    get_bundled_fontconfig_dir,
    get_bundled_fonts_dir,
)
from utils.logger import log_conversion

# LibreOffice 串行调用：并发运行多个 LibreOffice 实例可能竞争同一用户配置目录
_office_lock = threading.Lock()


def check_office_available() -> tuple:
    """检查 LibreOffice 是否可用，返回 (可用, 类型名)"""
    soffice = find_soffice()
    if soffice:
        return True, 'LibreOffice'
    return False, None


def word_to_pdf(input_path: str, output_path: str) -> str:
    """Word 文档转 PDF（LibreOffice headless）"""
    try:
        _convert_via_libreoffice(input_path, output_path)
        log_conversion(input_path, output_path, True)
        return output_path
    except RuntimeError:
        raise
    except Exception as e:
        log_conversion(input_path, output_path, False, str(e))
        raise RuntimeError('Word转PDF失败') from e


def ppt_to_pdf(input_path: str, output_path: str) -> str:
    """PPT 文档转 PDF（LibreOffice headless）"""
    try:
        _convert_via_libreoffice(input_path, output_path)
        log_conversion(input_path, output_path, True)
        return output_path
    except RuntimeError:
        raise
    except Exception as e:
        log_conversion(input_path, output_path, False, str(e))
        raise RuntimeError('PPT转PDF失败') from e


def _convert_via_libreoffice(input_path: str, output_path: str) -> None:
    """调用 LibreOffice headless 将文档转换为 PDF"""
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError(
            '未检测到 LibreOffice，请先安装并确保其在 PATH 中。\n'
            'macOS:  brew install --cask libreoffice\n'
            'Ubuntu: sudo apt install libreoffice'
        )

    abs_input = os.path.abspath(input_path)
    abs_output = os.path.abspath(output_path)
    output_dir = os.path.dirname(abs_output)
    os.makedirs(output_dir, exist_ok=True)

    # 构建环境变量：继承当前环境，叠加便携字体配置
    env = os.environ.copy()
    fc_dir = get_bundled_fontconfig_dir()
    fonts_dir = get_bundled_fonts_dir()
    if fc_dir:
        env['FONTCONFIG_PATH'] = fc_dir
        env['FONTCONFIG_FILE'] = os.path.join(fc_dir, 'fonts.conf')
    if fonts_dir:
        # 将便携字体目录追加到 XDG_DATA_DIRS，LibreOffice 也会扫描该路径
        xdg = env.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share')
        env['XDG_DATA_DIRS'] = fonts_dir + ':' + xdg

    # 使用独立的用户配置目录，避免与系统 LibreOffice 冲突
    lo_profile = os.path.join(tempfile.gettempdir(), 'docflow_lo_profile')
    os.makedirs(lo_profile, exist_ok=True)
    user_install_arg = f'-env:UserInstallation=file://{lo_profile}'

    with _office_lock:
        try:
            result = subprocess.run(
                [soffice, '--headless', '--norestore', user_install_arg,
                 '--convert-to', 'pdf',
                 '--outdir', output_dir, abs_input],
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError('LibreOffice 转换超时（>120s），请检查文件大小') from e
        except OSError as e:
            raise RuntimeError(f'LibreOffice 启动失败: {e}') from e

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f'LibreOffice 转换失败: {detail}')

    # LibreOffice 固定将输出文件命名为 <input_stem>.pdf
    expected_name = os.path.splitext(os.path.basename(abs_input))[0] + '.pdf'
    expected_path = os.path.join(output_dir, expected_name)

    # 若期望路径与实际目标不同则重命名
    if os.path.abspath(expected_path) != abs_output:
        if os.path.exists(expected_path):
            os.replace(expected_path, abs_output)

    if not os.path.exists(abs_output):
        raise RuntimeError('LibreOffice 转换后未找到输出文件，请确认文件格式受支持')
