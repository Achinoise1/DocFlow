# -*- mode: python ; coding: utf-8 -*-
# DocFlow - PyInstaller 打包配置
# 使用 onefile 模式（单个 exe，启动时解压到临时目录）
#
# 注意：pdf_to_ppt / pdf_to_images 使用 PyMuPDF (fitz) 渲染，已内置于 exe，无需安装 Poppler。

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
    a.binaries,
    a.datas,
    [],
    name='DocFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app_icon.ico',
)
