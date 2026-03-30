"""文件工具模块 - 文件类型识别、路径处理等"""
import os

from core.conversion_registry import get_file_type_from_ext, get_all_input_exts


def get_file_type(file_path: str) -> str:
    """根据扩展名判断文件类型（word/ppt/pdf/image/unknown）"""
    ext = os.path.splitext(file_path)[1].lower()
    return get_file_type_from_ext(ext)


def is_supported_file(file_path: str) -> bool:
    """判断文件是否被支持"""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in get_all_input_exts()


def get_output_path(input_path: str, output_ext: str, output_dir: str = None) -> str:
    """生成输出文件路径，避免覆盖已有文件"""
    dir_name = output_dir or os.path.dirname(input_path)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(dir_name, f'{base_name}{output_ext}')

    # 如果文件存在，添加序号
    counter = 1
    while os.path.exists(output_path):
        output_path = os.path.join(dir_name, f'{base_name}_{counter}{output_ext}')
        counter += 1

    return output_path


def get_friendly_size(file_path: str) -> str:
    """返回友好的文件大小字符串"""
    try:
        size = os.path.getsize(file_path)
    except OSError:
        return '未知'

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TB'


def get_file_ext(file_path: str) -> str:
    """获取小写扩展名"""
    return os.path.splitext(file_path)[1].lower()
