#!/usr/bin/env bash
# ============================================================================
# DocFlow - Linux 打包脚本
#
# 将 DocFlow + 便携式 LibreOffice + 中文字体 打包为可分发的 Linux 应用
#
# 前提条件:
#   1. 已运行 scripts/setup_portable_libreoffice.sh (下载 LibreOffice + 字体)
#   2. 已安装 Python 虚拟环境及依赖
#
# 用法:
#   chmod +x scripts/pack_linux.sh
#   ./scripts/pack_linux.sh
#
# 输出:
#   dist/DocFlow/          - 完整的便携式应用目录
#   dist/DocFlow.tar.gz    - 压缩包，可直接分发
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
err()   { echo -e "\033[1;31m[ERROR]\033[0m $*"; exit 1; }

# ── 检查前置条件 ──────────────────────────────────────────────────────────────

if [ ! -d "libreoffice_portable" ]; then
    err "未找到 libreoffice_portable/ 目录。请先运行:\n  ./scripts/setup_portable_libreoffice.sh"
fi

if [ ! -d "fonts" ] || ! ls fonts/*.tt[cf] fonts/*.otf &>/dev/null 2>&1; then
    err "未找到字体文件。请先运行:\n  ./scripts/setup_portable_libreoffice.sh"
fi

if [ ! -f "fontconfig/fonts.conf" ]; then
    err "未找到 fontconfig/fonts.conf。请先运行:\n  ./scripts/setup_portable_libreoffice.sh"
fi

# 激活虚拟环境（如存在）
if [ -f ".venv/bin/activate" ]; then
    info "激活 Python 虚拟环境..."
    source .venv/bin/activate
fi

# 检查 pyinstaller
command -v pyinstaller &>/dev/null || err "未找到 pyinstaller，请运行: pip install pyinstaller"

# ── PyInstaller 打包（onedir 模式）─────────────────────────────────────────────

info "正在使用 PyInstaller 打包 DocFlow（onedir 模式）..."

pyinstaller \
    --noconfirm \
    --clean \
    --name DocFlow \
    --onedir \
    --add-data "resources:resources" \
    --add-data "doc/image:doc/image" \
    --hidden-import fitz \
    --hidden-import fitz.utils \
    --hidden-import pdf2docx \
    --hidden-import pptx \
    --hidden-import pptx.util \
    --hidden-import "pptx.enum.text" \
    --hidden-import docx \
    --hidden-import docx.shared \
    --hidden-import PIL \
    --hidden-import PIL.Image \
    --hidden-import PIL.ImageOps \
    --hidden-import core \
    --hidden-import core.task_manager \
    --hidden-import core.converter \
    --hidden-import core.converter.pdf_converter \
    --hidden-import core.converter.image_converter \
    --hidden-import core.converter.office_converter \
    --hidden-import core.converter._office_unix \
    --hidden-import ui \
    --hidden-import ui.main_window \
    --hidden-import ui.widgets \
    --hidden-import ui.widgets.drop_zone \
    --hidden-import utils \
    --hidden-import utils.file_utils \
    --hidden-import utils.logger \
    --hidden-import utils.libreoffice_manager \
    --exclude-module tkinter \
    --exclude-module _tkinter \
    --exclude-module win32com \
    --exclude-module pythoncom \
    --exclude-module pywintypes \
    main.py

ok "PyInstaller 打包完成"

# ── 复制便携式 LibreOffice + 字体 + fontconfig ─────────────────────────────────

DIST_DIR="dist/DocFlow"

info "正在复制便携式 LibreOffice 到发布目录..."
cp -a libreoffice_portable "$DIST_DIR/libreoffice_portable"

info "正在复制中文字体到发布目录..."
cp -a fonts "$DIST_DIR/fonts"

info "正在复制 fontconfig 配置到发布目录..."
cp -a fontconfig "$DIST_DIR/fontconfig"

# ── 创建启动脚本 ──────────────────────────────────────────────────────────────

info "正在生成启动脚本..."

cat > "$DIST_DIR/run_docflow.sh" << 'LAUNCHER_EOF'
#!/usr/bin/env bash
# DocFlow 启动脚本 - 自动配置便携式 LibreOffice 和字体环境
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 配置 fontconfig 使用便携字体
export FONTCONFIG_PATH="$SCRIPT_DIR/fontconfig"
export FONTCONFIG_FILE="$SCRIPT_DIR/fontconfig/fonts.conf"

# 确保字体缓存目录存在
mkdir -p /tmp/docflow-fontcache

exec "$SCRIPT_DIR/DocFlow" "$@"
LAUNCHER_EOF

chmod +x "$DIST_DIR/run_docflow.sh"
chmod +x "$DIST_DIR/DocFlow"

ok "启动脚本已生成: $DIST_DIR/run_docflow.sh"

# ── 打包为 tar.gz ─────────────────────────────────────────────────────────────

info "正在压缩为 tar.gz..."
cd dist
tar czf DocFlow-linux-portable.tar.gz DocFlow/
cd "$PROJECT_ROOT"

ARCHIVE_SIZE=$(du -sh dist/DocFlow-linux-portable.tar.gz | cut -f1)
ok "打包完成: dist/DocFlow-linux-portable.tar.gz ($ARCHIVE_SIZE)"

echo
ok "======================================"
ok " 打包完成！"
ok ""
ok " 发布目录: dist/DocFlow/"
ok " 压缩包:   dist/DocFlow-linux-portable.tar.gz"
ok ""
ok " 用户使用方式:"
ok "   tar xzf DocFlow-linux-portable.tar.gz"
ok "   cd DocFlow"
ok "   ./run_docflow.sh"
ok "======================================"
