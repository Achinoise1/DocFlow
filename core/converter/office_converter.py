"""Office 转换器 - 平台路由层

根据运行平台自动选择转换后端：
  Windows          → win32com 调用本地 Office / WPS（_office_win.py）
  macOS / Linux    → LibreOffice headless subprocess（_office_unix.py）
"""
import sys

if sys.platform == 'win32':
    from core.converter._office_win import (   # noqa: F401
        word_to_pdf, ppt_to_pdf, check_office_available,
    )
else:
    from core.converter._office_unix import (  # noqa: F401
        word_to_pdf, ppt_to_pdf, check_office_available,
    )

__all__ = ['word_to_pdf', 'ppt_to_pdf', 'check_office_available']


