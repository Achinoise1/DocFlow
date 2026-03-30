"""转换路由调度器 - 将转换类型字符串分派到对应的 converter 函数"""
import os

from utils.file_utils import get_file_ext, get_output_path
from core.converter.office_converter import word_to_pdf, ppt_to_pdf
from core.converter.pdf_converter import pdf_to_word, pdf_to_ppt, pdf_to_images
from core.converter.image_converter import images_to_pdf, images_to_word


def dispatch(conversion_type: str, input_path: str, output_dir: str,
             options: dict = None) -> str:
    """
    单文件转换路由。

    Args:
        conversion_type: 转换类型 id，如 'word_to_pdf'
        input_path:      源文件绝对路径
        output_dir:      输出目录绝对路径
        options:         可选参数字典（当前仅 pdf_to_image 使用 format/dpi）

    Returns:
        输出文件（或目录）的绝对路径

    Raises:
        RuntimeError: 遇到不支持的类型或文件格式
    """
    if options is None:
        options = {}

    ext = get_file_ext(input_path)

    if conversion_type == 'to_pdf':
        # 兼容旧调用：根据扩展名自动选择转换函数
        return _convert_to_pdf(input_path, ext, output_dir)

    elif conversion_type == 'word_to_pdf':
        output = get_output_path(input_path, '.pdf', output_dir)
        return word_to_pdf(input_path, output)

    elif conversion_type == 'ppt_to_pdf':
        output = get_output_path(input_path, '.pdf', output_dir)
        return ppt_to_pdf(input_path, output)

    elif conversion_type == 'pdf_to_word':
        output = get_output_path(input_path, '.docx', output_dir)
        return pdf_to_word(input_path, output)

    elif conversion_type == 'pdf_to_ppt':
        output = get_output_path(input_path, '.pptx', output_dir)
        return pdf_to_ppt(input_path, output)

    elif conversion_type == 'pdf_to_image':
        fmt = options.get('format', 'png')
        dpi = options.get('dpi', 200)
        results = pdf_to_images(input_path, output_dir, fmt, dpi)
        if not results:
            return ''
        # 多页时返回子目录路径（方便直接用 Explorer 打开），单页返回文件路径
        return os.path.dirname(results[0]) if len(results) > 1 else results[0]

    elif conversion_type == 'image_to_pdf':
        output = get_output_path(input_path, '.pdf', output_dir)
        return images_to_pdf([input_path], output)

    elif conversion_type == 'image_to_word':
        output = get_output_path(input_path, '.docx', output_dir)
        return images_to_word([input_path], output)

    else:
        raise RuntimeError(f'不支持的转换类型: {conversion_type}')


def dispatch_batch(conversion_type: str, image_paths: list,
                   output_path: str) -> str:
    """
    批量图片合并路由（多图合一）。

    Args:
        conversion_type: 转换类型 id，如 'images_to_pdf'
        image_paths:     源图片绝对路径列表（有序）
        output_path:     输出文件绝对路径

    Returns:
        输出文件的绝对路径

    Raises:
        RuntimeError: 遇到不支持的类型
    """
    if conversion_type == 'images_to_pdf':
        images_to_pdf(image_paths, output_path)
    elif conversion_type == 'images_to_word':
        images_to_word(image_paths, output_path)
    else:
        raise RuntimeError(f'不支持的批量转换类型: {conversion_type}')

    return output_path


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _convert_to_pdf(input_path: str, ext: str, output_dir: str) -> str:
    """兼容旧 to_pdf 类型：根据扩展名决定调用哪个 converter。"""
    output = get_output_path(input_path, '.pdf', output_dir)
    if ext in ('.doc', '.docx'):
        return word_to_pdf(input_path, output)
    elif ext in ('.ppt', '.pptx'):
        return ppt_to_pdf(input_path, output)
    else:
        raise RuntimeError(f'文件格式不支持转换为PDF: {ext}')
