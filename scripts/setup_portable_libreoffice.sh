#!/usr/bin/env bash
# ============================================================================
# DocFlow - 便携式 LibreOffice + 中文字体 下载/安装脚本（Linux 专用）
#
# 功能:
#   1. 下载 LibreOffice AppImage 并解压到 libreoffice_portable/
#   2. 下载 Noto Sans CJK 字体到 fonts/
#   3. 生成 fontconfig 配置文件
#
# 用法:
#   chmod +x scripts/setup_portable_libreoffice.sh
#   ./scripts/setup_portable_libreoffice.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LO_VERSION="24.8.5"
LO_MAJOR="${LO_VERSION%%.*}"   # 24

# 目标目录
LO_DIR="$PROJECT_ROOT/libreoffice_portable"
FONTS_DIR="$PROJECT_ROOT/fonts"
FONTCONFIG_DIR="$PROJECT_ROOT/fontconfig"

# ── 工具函数 ──────────────────────────────────────────────────────────────────

info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
err()   { echo -e "\033[1;31m[ERROR]\033[0m $*"; exit 1; }

require_cmd() {
    command -v "$1" &>/dev/null || err "需要命令 '$1'，请先安装。"
}

# ── 检查依赖 ──────────────────────────────────────────────────────────────────

require_cmd wget
require_cmd chmod

# ── 1. 下载并解压 LibreOffice AppImage ────────────────────────────────────────

setup_libreoffice() {
    if [ -d "$LO_DIR" ] && [ -x "$LO_DIR/squashfs-root/AppRun" ]; then
        ok "LibreOffice 便携版已存在于 $LO_DIR，跳过下载。"
        return
    fi

    info "正在下载 LibreOffice ${LO_VERSION} AppImage..."

    ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64)  LO_ARCH="x86_64" ;;
        aarch64) LO_ARCH="aarch64" ;;
        *)       err "不支持的架构: $ARCH" ;;
    esac

    APPIMAGE_NAME="LibreOffice-${LO_VERSION}-${LO_ARCH}.AppImage"
    # TDF 官方 AppImage 下载地址（基础版 basic 即可覆盖 Writer / Impress / Calc）
    APPIMAGE_URL="https://download.documentfoundation.org/libreoffice/stable/${LO_VERSION}/deb/${LO_ARCH}/LibreOffice_${LO_VERSION}_Linux_${LO_ARCH}_deb.tar.gz"

    # LibreOffice 也提供 AppImage（由社区维护），但官方稳定包更可靠
    # 这里使用 deb 包解压方式，因为 AppImage 版本可能不总是最新
    APPIMAGE_URL="https://appimages.libreitalia.org/LibreOffice-still.standard-${LO_ARCH}.AppImage"

    TMPDIR_DL="$(mktemp -d)"
    APPIMAGE_PATH="$TMPDIR_DL/$APPIMAGE_NAME"

    info "下载地址: $APPIMAGE_URL"
    wget -q --show-progress -O "$APPIMAGE_PATH" "$APPIMAGE_URL" || {
        # 如果社区 AppImage 下载失败，回退到官方 deb 包方式
        warn "AppImage 下载失败，尝试使用官方 deb 包方式..."
        setup_libreoffice_from_deb "$TMPDIR_DL"
        return
    }

    chmod +x "$APPIMAGE_PATH"

    info "正在解压 AppImage（约 1~2 分钟）..."
    mkdir -p "$LO_DIR"
    cd "$LO_DIR"
    "$APPIMAGE_PATH" --appimage-extract >/dev/null 2>&1
    cd "$PROJECT_ROOT"

    rm -rf "$TMPDIR_DL"

    if [ -x "$LO_DIR/squashfs-root/AppRun" ]; then
        ok "LibreOffice 便携版已安装到 $LO_DIR/squashfs-root/"
    else
        err "AppImage 解压后未找到 AppRun，请检查下载文件。"
    fi
}

setup_libreoffice_from_deb() {
    local TMPDIR_DL="$1"
    ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64)  DEB_ARCH="x86_64" ;;
        aarch64) DEB_ARCH="aarch64" ;;
        *)       err "不支持的架构: $ARCH" ;;
    esac

    DEB_URL="https://download.documentfoundation.org/libreoffice/stable/${LO_VERSION}/deb/${DEB_ARCH}/LibreOffice_${LO_VERSION}_Linux_${DEB_ARCH}_deb.tar.gz"

    info "下载地址: $DEB_URL"
    DEB_TAR="$TMPDIR_DL/libreoffice_deb.tar.gz"
    wget -q --show-progress -O "$DEB_TAR" "$DEB_URL" || err "官方 deb 包下载也失败了，请检查网络。"

    info "正在解压 deb 包..."
    tar xzf "$DEB_TAR" -C "$TMPDIR_DL"

    mkdir -p "$LO_DIR/usr"

    # 解压所有 deb 包到目标目录
    require_cmd dpkg-deb
    for deb_file in "$TMPDIR_DL"/LibreOffice_*/DEBS/*.deb; do
        dpkg-deb -x "$deb_file" "$LO_DIR" 2>/dev/null || true
    done

    rm -rf "$TMPDIR_DL"

    # 查找 soffice 可执行文件
    SOFFICE="$(find "$LO_DIR" -name 'soffice' -type f 2>/dev/null | head -1)"
    if [ -n "$SOFFICE" ] && [ -x "$SOFFICE" ]; then
        ok "LibreOffice 便携版（deb 解压）已安装到 $LO_DIR"
    else
        err "deb 包解压后未找到 soffice 可执行文件。"
    fi
}

# ── 2. 下载中文字体 ──────────────────────────────────────────────────────────

setup_fonts() {
    if [ -d "$FONTS_DIR" ] && ls "$FONTS_DIR"/*.tt[cf] "$FONTS_DIR"/*.otf &>/dev/null 2>&1; then
        ok "字体目录已存在且包含字体文件，跳过下载。"
        return
    fi

    info "正在下载 Noto Sans CJK 字体..."
    mkdir -p "$FONTS_DIR"

    # Google Noto Sans CJK - 从 GitHub releases 下载
    NOTO_URL="https://github.com/notofonts/noto-cjk/releases/download/Sans2.004/03_NotoSansCJK-OTC.zip"

    TMPDIR_FONT="$(mktemp -d)"
    FONT_ZIP="$TMPDIR_FONT/NotoSansCJK.zip"

    wget -q --show-progress -O "$FONT_ZIP" "$NOTO_URL" || {
        warn "Noto Sans CJK OTC 下载失败，尝试下载 TTC 版本..."
        NOTO_URL_ALT="https://github.com/notofonts/noto-cjk/releases/download/Sans2.004/01_NotoSansCJK-TC.zip"
        wget -q --show-progress -O "$FONT_ZIP" "$NOTO_URL_ALT" || err "字体下载失败，请手动下载 Noto Sans CJK 字体放入 $FONTS_DIR"
    }

    require_cmd unzip
    info "正在解压字体文件..."
    unzip -q -o "$FONT_ZIP" -d "$TMPDIR_FONT/extracted"

    # 移动所有字体文件到 fonts/
    find "$TMPDIR_FONT/extracted" \( -name '*.ttf' -o -name '*.ttc' -o -name '*.otf' \) \
        -exec cp {} "$FONTS_DIR/" \;

    rm -rf "$TMPDIR_FONT"

    FONT_COUNT=$(find "$FONTS_DIR" \( -name '*.ttf' -o -name '*.ttc' -o -name '*.otf' \) | wc -l)
    ok "已安装 ${FONT_COUNT} 个字体文件到 $FONTS_DIR"
}

# ── 3. 生成 fontconfig 配置 ──────────────────────────────────────────────────

setup_fontconfig() {
    FONTS_CONF="$FONTCONFIG_DIR/fonts.conf"
    if [ -f "$FONTS_CONF" ]; then
        ok "fontconfig 配置已存在，跳过。"
        return
    fi

    info "正在生成 fontconfig/fonts.conf..."
    mkdir -p "$FONTCONFIG_DIR"

    cat > "$FONTS_CONF" << 'FONTCONFIG_EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<!--
  DocFlow 便携式字体配置
  - 优先使用 fonts/ 目录中的嵌入字体
  - 同时保留对系统字体的回退访问
-->
<fontconfig>
  <!-- 嵌入字体目录（相对于 FONTCONFIG_PATH 的上级目录） -->
  <dir prefix="default">../fonts</dir>

  <!-- 同时扫描系统字体作为回退 -->
  <dir>/usr/share/fonts</dir>
  <dir>/usr/local/share/fonts</dir>

  <!-- 缓存目录：使用临时目录避免权限问题 -->
  <cachedir prefix="xdg">fontconfig</cachedir>
  <cachedir>/tmp/docflow-fontcache</cachedir>

  <!-- 中文字体别名映射 -->
  <alias>
    <family>sans-serif</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>Noto Sans CJK TC</family>
      <family>Noto Sans CJK JP</family>
    </prefer>
  </alias>

  <alias>
    <family>serif</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
    </prefer>
  </alias>

  <alias>
    <family>monospace</family>
    <prefer>
      <family>Noto Sans Mono CJK SC</family>
    </prefer>
  </alias>

  <!-- 常见中文字体名称替换 -->
  <alias>
    <family>SimSun</family>
    <prefer><family>Noto Sans CJK SC</family></prefer>
  </alias>
  <alias>
    <family>宋体</family>
    <prefer><family>Noto Sans CJK SC</family></prefer>
  </alias>
  <alias>
    <family>SimHei</family>
    <prefer><family>Noto Sans CJK SC</family></prefer>
  </alias>
  <alias>
    <family>黑体</family>
    <prefer><family>Noto Sans CJK SC</family></prefer>
  </alias>
  <alias>
    <family>Microsoft YaHei</family>
    <prefer><family>Noto Sans CJK SC</family></prefer>
  </alias>
  <alias>
    <family>微软雅黑</family>
    <prefer><family>Noto Sans CJK SC</family></prefer>
  </alias>
  <alias>
    <family>KaiTi</family>
    <prefer><family>Noto Sans CJK SC</family></prefer>
  </alias>
  <alias>
    <family>楷体</family>
    <prefer><family>Noto Sans CJK SC</family></prefer>
  </alias>
  <alias>
    <family>FangSong</family>
    <prefer><family>Noto Sans CJK SC</family></prefer>
  </alias>
  <alias>
    <family>仿宋</family>
    <prefer><family>Noto Sans CJK SC</family></prefer>
  </alias>
</fontconfig>
FONTCONFIG_EOF

    ok "fontconfig 配置已生成: $FONTS_CONF"
}

# ── 主流程 ────────────────────────────────────────────────────────────────────

main() {
    info "======================================"
    info " DocFlow 便携式 LibreOffice 安装脚本"
    info "======================================"
    echo

    setup_libreoffice
    echo
    setup_fonts
    echo
    setup_fontconfig
    echo

    ok "======================================"
    ok " 安装完成！"
    ok ""
    ok " LibreOffice: $LO_DIR"
    ok " 字体目录:    $FONTS_DIR"
    ok " 字体配置:    $FONTCONFIG_DIR/fonts.conf"
    ok "======================================"
}

main "$@"
