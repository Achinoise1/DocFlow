"""文件工具模块 - 文件类型识别、路径处理等"""
import os

# 支持的文件扩展名映射
SUPPORTED_EXTENSIONS = {
    'word': ['.doc', '.docx'],
    'ppt': ['.ppt', '.pptx'],
    'pdf': ['.pdf'],
    'image': ['.jpg', '.jpeg', '.png'],
}

# 转换类型映射
CONVERSION_MAP = {
    'word_to_pdf': {'input': ['.doc', '.docx'], 'output': '.pdf'},
    'ppt_to_pdf': {'input': ['.ppt', '.pptx'], 'output': '.pdf'},
    'pdf_to_word': {'input': ['.pdf'], 'output': '.docx'},
    'pdf_to_ppt': {'input': ['.pdf'], 'output': '.pptx'},
    'image_to_pdf': {'input': ['.jpg', '.jpeg', '.png'], 'output': '.pdf'},
    'image_to_word': {'input': ['.jpg', '.jpeg', '.png'], 'output': '.docx'},
    'pdf_to_image': {'input': ['.pdf'], 'output': '.png'},
}


def get_file_type(file_path: str) -> str:
    """根据扩展名判断文件类型"""
    ext = os.path.splitext(file_path)[1].lower()
    for file_type, extensions in SUPPORTED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    return 'unknown'


def is_supported_file(file_path: str) -> bool:
    """判断文件是否被支持"""
    return get_file_type(file_path) != 'unknown'


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
