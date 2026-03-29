"""Office转换器 - 使用 win32com 调用本地 Office/WPS 进行高保真转换"""
import os
import threading
import pythoncom
from utils.logger import logger, log_conversion

# Office COM 调用必须串行：多线程并发创建多个 Word/PPT 实例会导致 COM 竞态错误
_office_lock = threading.Lock()


def _get_word_app():
    """尝试获取 Word COM 对象，优先 Office，其次 WPS
    使用 DispatchEx 始终创建新进程，避免连接到正在关闭中的老实例（ROT 竞态）"""
    try:
        import win32com.client
        word = win32com.client.DispatchEx('Word.Application')
        word.Visible = False
        word.DisplayAlerts = False
        return word, 'Office'
    except Exception:
        pass
    try:
        import win32com.client
        word = win32com.client.DispatchEx('kwps.Application')
        word.Visible = False
        word.DisplayAlerts = False
        return word, 'WPS'
    except Exception:
        pass
    return None, None


def _get_ppt_app():
    """尝试获取 PowerPoint COM 对象，优先 Office，其次 WPS
    使用 DispatchEx 始终创建新进程，避免连接到正在关闭中的老实例（ROT 竞态）"""
    try:
        import win32com.client
        ppt = win32com.client.DispatchEx('PowerPoint.Application')
        return ppt, 'Office'
    except Exception:
        pass
    try:
        import win32com.client
        ppt = win32com.client.DispatchEx('kwpp.Application')
        return ppt, 'WPS'
    except Exception:
        pass
    return None, None


def check_office_available() -> tuple:
    """检查是否安装了 Office 或 WPS，返回 (可用, 类型名)"""
    pythoncom.CoInitialize()
    try:
        word, name = _get_word_app()
        if word:
            try:
                word.Quit()
            except Exception:
                pass
            return True, name
        return False, None
    finally:
        pythoncom.CoUninitialize()


def word_to_pdf(input_path: str, output_path: str) -> str:
    """Word 文档转 PDF"""
    with _office_lock:
        pythoncom.CoInitialize()
        word = None
        doc = None
        try:
            word, app_name = _get_word_app()
            if not word:
                raise RuntimeError('未检测到 Office 或 WPS，请先安装')

            abs_input = os.path.abspath(input_path)
            abs_output = os.path.abspath(output_path)

            doc = word.Documents.Open(abs_input, ReadOnly=True)
            # wdFormatPDF = 17
            doc.SaveAs(abs_output, FileFormat=17)
            try:
                doc.Close(False)
            except Exception:
                pass
            doc = None

            log_conversion(input_path, output_path, True)
            return output_path
        except RuntimeError:
            raise
        except Exception as e:
            error_msg = f'Word转PDF失败: {str(e)}'
            log_conversion(input_path, output_path, False, error_msg)
            raise RuntimeError('转换失败，请检查文件是否损坏或被占用') from e
        finally:
            if doc:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()


def ppt_to_pdf(input_path: str, output_path: str) -> str:
    """PPT 文档转 PDF"""
    with _office_lock:
        pythoncom.CoInitialize()
        ppt = None
        presentation = None
        try:
            ppt, app_name = _get_ppt_app()
            if not ppt:
                raise RuntimeError('未检测到 Office 或 WPS，请先安装')

            abs_input = os.path.abspath(input_path)
            abs_output = os.path.abspath(output_path)

            # ppOpen = 2 (read-only)
            presentation = ppt.Presentations.Open(abs_input, ReadOnly=True, WithWindow=False)
            # ppSaveAsPDF = 32
            presentation.SaveAs(abs_output, 32)
            try:
                presentation.Close()
            except Exception:
                pass
            presentation = None

            log_conversion(input_path, output_path, True)
            return output_path
        except RuntimeError:
            raise
        except Exception as e:
            error_msg = f'PPT转PDF失败: {str(e)}'
            log_conversion(input_path, output_path, False, error_msg)
            raise RuntimeError('转换失败，请检查文件是否损坏或被占用') from e
        finally:
            if presentation:
                try:
                    presentation.Close()
                except Exception:
                    pass
            if ppt:
                try:
                    ppt.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
