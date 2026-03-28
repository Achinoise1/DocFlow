"""日志模块 - 记录转换时间、文件路径、错误原因"""
import logging
import os
import sys
from datetime import datetime


def setup_logger():
    """初始化日志系统，输出到本地 log.txt"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    log_path = os.path.join(base_dir, 'log.txt')

    logger = logging.getLogger('DocFlow')
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


def log_conversion(source: str, target: str, success: bool, error_msg: str = ''):
    """记录一次转换操作"""
    if success:
        logger.info(f'转换成功: {source} -> {target}')
    else:
        logger.error(f'转换失败: {source} -> {target} | 原因: {error_msg}')
