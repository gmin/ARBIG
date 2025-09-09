"""
日志工具模块
提供统一的日志记录功能
"""

import logging
import os
from datetime import datetime

# 全局logger缓存，避免重复创建handlers
_logger_cache = {}

def setup_logger(name, log_file, level=logging.INFO):
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        log_file: 日志文件路径
        level: 日志级别

    Returns:
        logger: 配置好的日志记录器
    """
    # 检查是否已经创建过该logger
    if name in _logger_cache:
        return _logger_cache[name]

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 🔧 防止重复添加handlers
    if logger.handlers:
        logger.handlers.clear()

    # 创建文件处理器
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 🔧 防止向父logger传播，避免重复输出
    logger.propagate = False

    # 缓存logger
    _logger_cache[name] = logger

    return logger

# 创建默认日志记录器
def get_logger(name='gold_arbitrage'):
    """
    获取默认日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logger: 配置好的日志记录器
    """
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(
        log_dir,
        f'gold_arbitrage_{datetime.now().strftime("%Y%m%d")}.log'
    )

    return setup_logger(name, log_file)

def clear_logger_cache():
    """清理logger缓存（用于测试或重启）"""
    global _logger_cache
    _logger_cache.clear()
