# DocFlow 打包说明

## 环境准备

激活虚拟环境（每次打包前执行）：

```powershell
.venv\Scripts\Activate.ps1
```

## 一次性配置（首次打包时）

Python 3.10.0 存在字节码解析 bug，需对 PyInstaller 打补丁，否则打包报 `IndexError`：

打开文件 `.venv\lib\site-packages\PyInstaller\lib\modulegraph\util.py`，将：

```python
yield from (i for i in dis.get_instructions(code_object) if i.opname != "EXTENDED_ARG")
```

替换为：

```python
try:
    yield from (i for i in dis.get_instructions(code_object) if i.opname != "EXTENDED_ARG")
except (IndexError, Exception):
    pass
```

## 打包命令

```powershell
pyinstaller main.spec --clean -y
```

- `--clean`：清除上次构建缓存
- `-y`：自动覆盖旧输出，无需手动确认

打包完成后，输出文件在 `dist\DocFlow.exe`。

## 打包模式说明

当前使用 **onefile 模式**（单个 exe），修改模式需编辑 `main.spec`：

| 模式 | 优点 | 缺点 |
|------|------|------|
| onefile（当前）| 单文件，直接发给别人 | 首次启动慢 5-10 秒 |
| onedir | 启动快 | 需整个文件夹一起发送 |

切换回 onedir 模式，将 `main.spec` 中 `EXE()` 的参数改为 `exclude_binaries=True`，并在末尾添加 `COLLECT()` 块（参考 git 历史）。

<details>
   <summary>onedir</summary>

   ```python
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

   ```
</details>

<details>
   <summary>onefile</summary>

   ```python
    # -*- mode: python ; coding: utf-8 -*-
    # DocFlow - PyInstaller 打包配置
    # 使用 onefile 模式（单个 exe，启动时解压到临时目录）
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
    )

   ```
</details>

## 常见问题

**样式丢失**：`resources/` 目录未打包进去。检查 `main.spec` 中 `datas` 是否包含：
```python
datas=[('resources', 'resources')]
```

**复选框图标不显示**：已在 `ui/main_window.py` 的 `_apply_theme()` 中处理，打包时将 QSS 里的相对 `url()` 路径自动替换为绝对路径，无需手动干预。

**PDF 转 PPT 报错**：该功能依赖 [Poppler](https://github.com/oschwartz10612/poppler-windows/releases)，需用户自行安装并将 `bin/` 目录加入系统 PATH。
