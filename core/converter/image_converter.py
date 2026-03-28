"""图片转换器 - 图片与PDF/Word之间的转换"""
import os
from PIL import Image
from utils.logger import logger, log_conversion


def images_to_pdf(image_paths: list, output_path: str) -> str:
    """多张图片合并为一个PDF，每张图片一页"""
    try:
        if not image_paths:
            raise ValueError('没有选择图片文件')

        img_list = []
        first_img = None

        for path in image_paths:
            img = Image.open(path).convert('RGB')
            if first_img is None:
                first_img = img
            else:
                img_list.append(img)

        first_img.save(output_path, 'PDF', save_all=True, append_images=img_list)

        # 关闭图片
        if first_img:
            first_img.close()
        for img in img_list:
            img.close()

        log_conversion(str(image_paths), output_path, True)
        return output_path
    except ValueError:
        raise
    except Exception as e:
        error_msg = str(e)
        log_conversion(str(image_paths), output_path, False, error_msg)
        raise RuntimeError('图片转PDF失败，请检查图片文件是否损坏') from e


def images_to_word(image_paths: list, output_path: str) -> str:
    """多张图片插入到Word文档"""
    try:
        from docx import Document
        from docx.shared import Inches

        if not image_paths:
            raise ValueError('没有选择图片文件')

        doc = Document()

        for i, path in enumerate(image_paths):
            doc.add_picture(path, width=Inches(6))
            if i < len(image_paths) - 1:
                doc.add_page_break()

        doc.save(output_path)

        log_conversion(str(image_paths), output_path, True)
        return output_path
    except ValueError:
        raise
    except Exception as e:
        error_msg = str(e)
        log_conversion(str(image_paths), output_path, False, error_msg)
        raise RuntimeError('图片转Word失败，请检查图片文件是否损坏') from e
