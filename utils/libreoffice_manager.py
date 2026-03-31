"""LibreOffice 自动检测与安装管理器（macOS / Linux 专用）

在 Windows 上本模块不会被调用，仅作为占位。
"""
import os
import sys
import shutil
import subprocess
import threading
import platform
from pathlib import Path

# LibreOffice 稳定版版本号（可在新版发布后手动更新）
_LO_VERSION = '24.8.5'

# ── 取消安装机制 ──────────────────────────────────────────────────────────────

_current_proc: subprocess.Popen | None = None
_cancel_event = threading.Event()


def cancel_install() -> None:
    """取消当前正在进行的安装（终止子进程并设置取消标志）"""
    global _current_proc
    _cancel_event.set()
    if _current_proc and _current_proc.poll() is None:
        try:
            _current_proc.terminate()
        except Exception:
            pass


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


def get_available_auto_install_method() -> str | None:
    """检测当前平台可用的免 sudo 自动安装方法，返回方法名或 None"""
    if sys.platform == 'darwin':
        return 'brew' if shutil.which('brew') else 'dmg'
    # Linux
    for method in ('snap', 'flatpak', 'apt', 'dnf', 'yum'):
        if method == 'apt' and shutil.which('apt-get') and shutil.which('pkexec'):
            return 'apt'
        if method in ('dnf', 'yum') and shutil.which(method) and shutil.which('pkexec'):
            return method
        if method in ('snap', 'flatpak') and shutil.which(method):
            return method
    return None


# ── 安装入口 ──────────────────────────────────────────────────────────────────


def install_auto(progress_callback=None) -> tuple[bool, str]:
    """
    尝试自动安装 LibreOffice。

    Args:
        progress_callback: 接受一个 str 参数的回调，用于实时更新进度文本

    Returns:
        (success: bool, message: str)
    """
    _cancel_event.clear()

    def emit(msg: str):
        if progress_callback:
            progress_callback(msg)

    if sys.platform == 'darwin':
        return _install_macos(emit)
    else:
        return _install_linux(emit)


# ── macOS ─────────────────────────────────────────────────────────────────────


def _install_macos(emit) -> tuple[bool, str]:
    global _current_proc
    brew = shutil.which('brew')
    if brew:
        emit('检测到 Homebrew，正在安装 LibreOffice（约 400 MB，请耐心等待）...')
        try:
            proc = subprocess.Popen(
                [brew, 'install', '--cask', 'libreoffice'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            _current_proc = proc
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    emit(line)
            proc.wait(timeout=600)
            _current_proc = None
            if _cancel_event.is_set():
                return False, '已取消'
            if proc.returncode == 0:
                return True, 'LibreOffice 安装成功'
            return False, f'brew 安装失败（退出码 {proc.returncode}），请尝试手动安装'
        except subprocess.TimeoutExpired:
            _current_proc = None
            return False, '安装超时（>600s），请检查网络连接'
        except Exception as e:
            _current_proc = None
            if _cancel_event.is_set():
                return False, '已取消'
            emit(f'brew 执行异常: {e}')
    else:
        emit('未检测到 Homebrew，将通过下载 DMG 安装...')

    if _cancel_event.is_set():
        return False, '已取消'
    return _install_macos_dmg(emit)


def _install_macos_dmg(emit) -> tuple[bool, str]:
    """下载 LibreOffice DMG 并安装到 ~/Applications（无需管理员权限）"""
    import urllib.request
    import tempfile

    machine = platform.machine()
    arch = 'aarch64' if machine in ('arm64', 'aarch64') else 'x86_64'
    ver = _LO_VERSION
    url = (
        f'https://download.documentfoundation.org/libreoffice/stable/'
        f'{ver}/mac/{arch}/LibreOffice_{ver}_MacOS_{arch}.dmg'
    )

    emit(f'正在下载 LibreOffice {ver}（macOS {arch}，约 400 MB）...')
    emit(f'来源：{url}')

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.dmg', delete=False) as tmp:
            tmp_path = tmp.name

        last_pct = [-1]

        def _reporthook(block_num, block_size, total_size):
            if _cancel_event.is_set():
                raise RuntimeError('已取消')
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 // total_size)
                if pct != last_pct[0] and pct % 5 == 0:
                    last_pct[0] = pct
                    dl_mb = downloaded / 1024 / 1024
                    tot_mb = total_size / 1024 / 1024
                    emit(f'下载中 {dl_mb:.0f} / {tot_mb:.0f} MB  ({pct}%)')

        urllib.request.urlretrieve(url, tmp_path, _reporthook)
        emit('✅ 下载完成，正在挂载镜像...')

        # Mount DMG
        mount_result = subprocess.run(
            ['hdiutil', 'attach', '-quiet', '-nobrowse', tmp_path],
            capture_output=True, text=True, timeout=60,
        )
        if mount_result.returncode != 0:
            return False, f'DMG 挂载失败：{mount_result.stderr.strip()}'

        # 查找挂载点（自动搜索 /Volumes 下 LibreOffice.app）
        app_src = None
        mount_point = None
        for vol_name in os.listdir('/Volumes'):
            candidate = f'/Volumes/{vol_name}/LibreOffice.app'
            if os.path.exists(candidate):
                app_src = candidate
                mount_point = f'/Volumes/{vol_name}'
                break

        if not app_src:
            subprocess.run(['hdiutil', 'detach', '-quiet',
                           mount_point or '/Volumes/LibreOffice'],
                           capture_output=True)
            return False, '在 DMG 中未找到 LibreOffice.app，下载文件可能已损坏'

        emit(f'正在安装到 ~/Applications（约 400 MB，请稍候）...')
        if _cancel_event.is_set():
            subprocess.run(['hdiutil', 'detach', mount_point, '-quiet'], capture_output=True)
            raise RuntimeError('已取消')
        user_apps = str(Path.home() / 'Applications')
        os.makedirs(user_apps, exist_ok=True)
        app_dst = os.path.join(user_apps, 'LibreOffice.app')

        if os.path.exists(app_dst):
            emit('正在替换旧版本...')
            shutil.rmtree(app_dst)

        shutil.copytree(app_src, app_dst)
        emit('正在卸载镜像...')
        subprocess.run(['hdiutil', 'detach', mount_point, '-quiet'],
                       capture_output=True, timeout=30)
        os.unlink(tmp_path)

        return True, f'LibreOffice 已安装至 {app_dst}'

    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        if _cancel_event.is_set() or str(e) == '已取消':
            return False, '已取消'
        return False, f'安装失败：{e}'


# ── Linux ─────────────────────────────────────────────────────────────────────


def _install_linux(emit) -> tuple[bool, str]:
    """依次尝试 snap → flatpak → apt (pkexec) → dnf/yum (pkexec)"""

    # 1. snap（无需 sudo）
    if shutil.which('snap'):
        emit('📦 通过 snap 安装 LibreOffice...')
        ok, msg = _run_with_log(['snap', 'install', 'libreoffice'], emit, timeout=300)
        if ok:
            return True, 'LibreOffice 已通过 snap 安装'
        emit(f'snap 安装失败：{msg}')

    # 2. flatpak（无需 sudo）
    if shutil.which('flatpak'):
        emit('📦 通过 flatpak 安装 LibreOffice...')
        ok, msg = _run_with_log(
            ['flatpak', 'install', '-y', '--noninteractive',
             'flathub', 'org.libreoffice.LibreOffice'],
            emit, timeout=300
        )
        if ok:
            # flatpak 的 libreoffice 包装脚本位置
            return True, 'LibreOffice 已通过 flatpak 安装'
        emit(f'flatpak 安装失败：{msg}')

    # 3. apt with pkexec（需要用户通过 GUI 授权管理员权限）
    if shutil.which('apt-get') and shutil.which('pkexec'):
        emit('🔐 通过 apt 安装 LibreOffice（将弹出管理员授权对话框）...')
        # 先更新包索引
        subprocess.run(['pkexec', 'apt-get', 'update', '-qq'],
                       timeout=120, capture_output=True)
        ok, msg = _run_with_log(
            ['pkexec', 'apt-get', 'install', '-y', '--no-install-recommends',
             'libreoffice-writer', 'libreoffice-impress'],
            emit, timeout=300
        )
        if ok:
            return True, 'LibreOffice 已通过 apt 安装'
        emit(f'apt 安装失败：{msg}')

    # 4. dnf / yum with pkexec
    for pkg_mgr in ('dnf', 'yum'):
        if shutil.which(pkg_mgr) and shutil.which('pkexec'):
            emit(f'🔐 通过 {pkg_mgr} 安装 LibreOffice（将弹出管理员授权对话框）...')
            ok, msg = _run_with_log(
                ['pkexec', pkg_mgr, 'install', '-y', 'libreoffice'],
                emit, timeout=300
            )
            if ok:
                return True, f'LibreOffice 已通过 {pkg_mgr} 安装'
            emit(f'{pkg_mgr} 安装失败：{msg}')
            break

    return False, '所有自动安装方法均失败，请手动安装 LibreOffice'


def _run_with_log(cmd: list, emit, timeout: int) -> tuple[bool, str]:
    """运行命令并将 stdout/stderr 实时输出到 emit，返回 (success, last_stderr)"""
    global _current_proc
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _current_proc = proc
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                emit(line)
        proc.wait(timeout=timeout)
        _current_proc = None
        if _cancel_event.is_set():
            return False, '已取消'
        return proc.returncode == 0, f'退出码 {proc.returncode}'
    except subprocess.TimeoutExpired:
        _current_proc = None
        return False, f'超时（>{timeout}s）'
    except Exception as e:
        _current_proc = None
        if _cancel_event.is_set():
            return False, '已取消'
        return False, str(e)
