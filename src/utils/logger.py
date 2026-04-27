import logging
import os
from datetime import datetime

def setup_logger(name="AimBot"):
    """
    配置并返回一个标准的 logger 实例。
    日志将同时输出到控制台（INFO级别）和文件（DEBUG级别）。
    """
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回（防止重复添加 handler）
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.DEBUG)

    # 创建一个格式化器
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. 控制台输出处理器 (INFO 级别)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. 文件输出处理器 (DEBUG 级别)
    # 确保 logs 目录存在
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, f"aimbot_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# 创建一个全局的 default logger，方便其他模块直接导入
logger = setup_logger()
