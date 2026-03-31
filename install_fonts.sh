#!/usr/bin/env bash
# install_fonts.sh — 在 Linux / macOS 上安装 Noto CJK 中文字体
# 用法：bash install_fonts.sh
set -euo pipefail

echo "[DocFlow] 开始安装中文字体（Noto CJK）..."

FONT_DIR="$HOME/.local/share/fonts/noto-cjk"

if [[ "$OSTYPE" == "darwin"* ]]; then
    # ── macOS ──────────────────────────────────────────────────────────────
    FONT_DIR="$HOME/Library/Fonts/noto-cjk"
    if command -v brew &>/dev/null; then
        echo "  通过 brew 安装 font-noto-sans-cjk..."
        brew tap homebrew/cask-fonts 2>/dev/null || true
        brew install --cask font-noto-sans-cjk
        echo "[DocFlow] 字体安装完成（macOS 会自动刷新字体缓存）。"
        exit 0
    fi
    # brew 不可用时回退到手动下载
fi

# ── Linux / macOS 无 brew：手动下载 ────────────────────────────────────────
# 尝试通过包管理器安装
if command -v apt-get &>/dev/null; then
    echo "  通过 apt 安装 fonts-noto-cjk（需要管理员密码）..."
    sudo apt-get install -y fonts-noto-cjk
    fc-cache -fv
    echo "[DocFlow] 字体安装完成。"
    exit 0
elif command -v dnf &>/dev/null; then
    echo "  通过 dnf 安装 google-noto-sans-cjk-fonts（需要管理员密码）..."
    sudo dnf install -y google-noto-sans-cjk-fonts
    fc-cache -fv
    echo "[DocFlow] 字体安装完成。"
    exit 0
elif command -v pacman &>/dev/null; then
    echo "  通过 pacman 安装 noto-fonts-cjk（需要管理员密码）..."
    sudo pacman -Sy --noconfirm noto-fonts-cjk
    fc-cache -fv
    echo "[DocFlow] 字体安装完成。"
    exit 0
fi

# 包管理器均不可用时，直接下载字体文件到用户目录
echo "  未找到受支持的包管理器，将直接下载字体文件到 $FONT_DIR ..."
mkdir -p "$FONT_DIR"

# Noto Sans CJK SC (Regular) — 约 16 MB
FONT_URL="https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
FONT_FILE="$FONT_DIR/NotoSansCJKsc-Regular.otf"

if command -v curl &>/dev/null; then
    curl -L --progress-bar -o "$FONT_FILE" "$FONT_URL"
elif command -v wget &>/dev/null; then
    wget -q --show-progress -O "$FONT_FILE" "$FONT_URL"
else
    echo "  错误：需要 curl 或 wget 才能下载字体。请手动安装中文字体。"
    exit 1
fi

# 刷新字体缓存
if command -v fc-cache &>/dev/null; then
    echo "  刷新字体缓存..."
    fc-cache -fv "$FONT_DIR"
fi

echo "[DocFlow] 中文字体安装完成：$FONT_FILE"
