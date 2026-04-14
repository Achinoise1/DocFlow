---
name: docflow-setup
description: "Setup and run DocFlow after cloning the repo. Use when: setting up the development environment, installing dependencies, running the app from source, or packaging it as an executable. Covers Python venv, pip install, platform-specific requirements (Office/WPS on Windows, LibreOffice on macOS/Linux), Chinese font installation, and PyInstaller packaging."
argument-hint: "platform (windows | macos | linux) or task (run | package | deps)"
---

# DocFlow Setup

DocFlow is a local offline document format conversion tool (Word ↔ PDF ↔ PPT ↔ Image). It uses PySide6 for the GUI and relies on platform-specific Office automation for `.doc`/`.docx`/`.ppt`/`.pptx` → PDF conversion.

This skill assumes the repository has already been cloned and the current working directory is the repository root.

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | Required by PySide6 6.5 |
| pip | latest | `python -m pip install --upgrade pip` |
| **Windows only**: Microsoft Office or WPS Office | any | Required for Word/PPT → PDF via COM |
| **macOS/Linux only**: LibreOffice | 7.x+ | Required for Word/PPT → PDF |
| **macOS/Linux only**: Noto CJK fonts | any | Required for correct Chinese rendering in LibreOffice |

---

## Step-by-Step Setup

### 1. Create and Activate a Virtual Environment

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**What gets installed:**

| Package | Purpose |
|---|---|
| `PySide6>=6.5.0` | Qt6 GUI framework |
| `pywin32>=306` *(Windows only)* | COM automation — drives Office/WPS for conversion |
| `pdf2docx>=0.5.8` | PDF → Word (`.docx`) |
| `Pillow>=10.0.0` | Image processing (Image → PDF/Word) |
| `python-docx>=1.1.0` | Read/write `.docx` files |
| `python-pptx>=0.6.23` | Read/write `.pptx` files |
| `PyMuPDF>=1.24.0` | PDF rendering — PDF → Image, PDF → PPT |
| `pyinstaller>=6.19.0` | Packaging only (not needed at runtime) |

> `pywin32` is gated by `sys_platform == "win32"` in `requirements.txt` and will not install on macOS/Linux.

### 3. Platform-Specific System Dependencies

#### Windows

Ensure **Microsoft Office** (Word/PowerPoint) **or WPS Office** is installed and activated.  
The converter uses `win32com` to automate the Office application — no extra steps needed after `pip install`.

#### macOS

```bash
# Option A: Homebrew (recommended)
brew install --cask libreoffice
brew tap homebrew/cask-fonts && brew install --cask font-noto-sans-cjk

# Option B: provided scripts
bash install_libreoffice.sh
bash install_fonts.sh
```

#### Linux

```bash
# Provided scripts handle snap / flatpak / apt / dnf / yum / pacman automatically
bash install_libreoffice.sh
bash install_fonts.sh
```

Or manually with your package manager, e.g. on Debian/Ubuntu:
```bash
sudo apt-get install -y libreoffice fonts-noto-cjk
```

---

## Running the App

```bash
# Activate venv first, then:
python main.py
```

On first launch on macOS/Linux, the app prints warnings to stderr if LibreOffice or Chinese fonts are missing but will still start.

---

## Packaging as an Executable

### Windows → single `.exe`

```bat
scripts\pack.bat
# Output: dist\DocFlow.exe
```

Or manually:
```powershell
pyinstaller main.spec --clean -y
```

### macOS / Linux → folder bundle

```bash
pyinstaller main_unix.spec --clean -y
# Output: dist/main/
```

> `main_unix.spec` uses `onedir` mode (not `onefile`) and does **not** bundle LibreOffice — it must be installed on the target system.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `ImportError: No module named 'win32com'` | `pywin32` not installed | Re-run `pip install -r requirements.txt` on Windows |
| Word/PPT → PDF fails on Windows | Office/WPS not installed or not activated | Install and activate Office or WPS |
| Word/PPT → PDF fails on macOS/Linux | LibreOffice not found | Run `bash install_libreoffice.sh` |
| Garbled characters in converted PDF | No Chinese fonts | Run `bash install_fonts.sh` |
| `PySide6` install fails | Python version < 3.8 | Upgrade to Python 3.10+ |
| `PyMuPDF` install fails on Linux | Missing build tools | `sudo apt-get install -y python3-dev build-essential` |
