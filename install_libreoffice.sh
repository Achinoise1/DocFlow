#!/usr/bin/env bash
# install_libreoffice.sh — 在 Linux / macOS 上安装 LibreOffice
# 用法：bash install_libreoffice.sh
set -euo pipefail

echo "[DocFlow] 开始安装 LibreOffice..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # ── macOS ──────────────────────────────────────────────────────────────
    if command -v brew &>/dev/null; then
        echo "  检测到 Homebrew，通过 brew 安装..."
        brew install --cask libreoffice
    else
        echo "  未检测到 Homebrew。"
        echo "  请手动从以下地址下载并安装 LibreOffice："
        echo "    https://www.libreoffice.org/download/"
        exit 1
    fi

else
    # ── Linux ───────────────────────────────────────────────────────────────
    if command -v snap &>/dev/null; then
        echo "  通过 snap 安装（无需 sudo）..."
        snap install libreoffice

    elif command -v flatpak &>/dev/null; then
        echo "  通过 flatpak 安装（无需 sudo）..."
        flatpak install -y --noninteractive flathub org.libreoffice.LibreOffice

    elif command -v apt-get &>/dev/null; then
        echo "  通过 apt 安装（需要管理员密码）..."
        sudo apt-get update -qq
        sudo apt-get install -y libreoffice

    elif command -v dnf &>/dev/null; then
        echo "  通过 dnf 安装（需要管理员密码）..."
        sudo dnf install -y libreoffice

    elif command -v yum &>/dev/null; then
        echo "  通过 yum 安装（需要管理员密码）..."
        sudo yum install -y libreoffice

    elif command -v pacman &>/dev/null; then
        echo "  通过 pacman 安装（需要管理员密码）..."
        sudo pacman -Sy --noconfirm libreoffice-fresh

    else
        echo "  未找到受支持的包管理器（snap / flatpak / apt / dnf / yum / pacman）。"
        echo "  请手动从以下地址下载并安装 LibreOffice："
        echo "    https://www.libreoffice.org/download/"
        exit 1
    fi
fi

echo "[DocFlow] LibreOffice 安装完成。"

# 验证
if command -v soffice &>/dev/null || command -v libreoffice &>/dev/null; then
    echo "  验证：$(soffice --version 2>/dev/null || libreoffice --version 2>/dev/null)"
else
    echo "  注意：soffice 未在 PATH 中找到，可能需要重新打开终端或重启会话。"
fi
