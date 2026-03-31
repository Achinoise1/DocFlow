# -*- mode: python ; coding: utf-8 -*-
# DocFlow - PyInstaller 打包配置（Linux / macOS）
# 使用 onedir 模式，不内置 LibreOffice / 字体，依赖系统安装。
#
# 用法（在 Linux/macOS 上执行）：
#   pyinstaller main_unix.spec

import sys

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('doc/image', 'doc/image'),
    ],
    hiddenimports=[
        # PyMuPDF
        'fitz',
        'fitz.utils',
        # pdf2docx
        'pdf2docx',
        # python-pptx
        'pptx',
        'pptx.util',
        'pptx.enum.text',
        # python-docx
        'docx',
        'docx.shared',
        # Pillow
        'PIL',
        'PIL.Image',
        'PIL.ImageOps',
        # 项目内部模块（防止动态导入遗漏）
        'core',
        'core.task_manager',
        'core.converter',
        'core.converter.pdf_converter',
        'core.converter.image_converter',
        'core.converter.office_converter',
        'core.converter._office_unix',
        'ui',
        'ui.main_window',
        'ui.widgets',
        'ui.widgets.drop_zone',
        'utils',
        'utils.file_utils',
        'utils.logger',
        'utils.libreoffice_manager',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        '_tkinter',
        # Windows 专属，Unix 不需要
        'win32com',
        'win32com.client',
        'win32com.server',
        'pythoncom',
        'pywintypes',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# onedir 模式：不传入 a.binaries / a.datas 到 EXE，而是放进 COLLECT
exe = EXE(
    pyz,
    a.scripts,
    [],
    name='DocFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # Linux strip/upx 可能破坏 Qt 库，建议关闭
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,   # macOS：True 会拦截文件关联参数，保持 False
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app_icon.png',  # macOS/Linux 用 png；若无可删此行
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='DocFlow',         # dist/DocFlow/
)
