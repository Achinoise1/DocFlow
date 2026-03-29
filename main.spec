# -*- mode: python ; coding: utf-8 -*-
# DocFlow - PyInstaller 打包配置
# 使用 onedir 模式（比 onefile 更稳定，尤其是 PySide6）
#
# 注意：pdf_to_ppt 功能依赖 poppler（pdf2image 所需），
#       需单独安装并将 poppler/bin 加入系统 PATH，或手动添加到 binaries。
#       下载地址：https://github.com/oschwartz10612/poppler-windows/releases

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources', 'resources'),
    ],
    hiddenimports=[
        # PyMuPDF
        'fitz',
        'fitz.utils',
        # pdf2docx
        'pdf2docx',
        # pdf2image
        'pdf2image',
        'pdf2image.exceptions',
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
        # pywin32
        'win32com',
        'win32com.client',
        'win32com.server',
        'win32com.server.register',
        'pythoncom',
        'pywintypes',
        # 项目内部模块（防止动态导入遗漏）
        'core',
        'core.task_manager',
        'core.converter',
        'core.converter.pdf_converter',
        'core.converter.image_converter',
        'core.converter.office_converter',
        'ui',
        'ui.main_window',
        'ui.widgets',
        'ui.widgets.drop_zone',
        'utils',
        'utils.file_utils',
        'utils.logger',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        '_tkinter',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DocFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DocFlow',
)
