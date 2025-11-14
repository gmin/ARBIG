"""
日志工具模块
提供统一的日志记录功能 - 支持按日期自动切换日志文件
"""

import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# 全局logger缓存，避免重复创建handlers
_logger_cache = {}


def clear_logger_cache():
    """清理logger缓存，强制重新创建"""
    global _logger_cache

    # 关闭所有现有的handlers
    for name, logger in _logger_cache.items():
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    # 清空缓存
    _logger_cache.clear()
    print("🔄 [日志系统] 强制清理缓存，重新创建logger")


def setup_logger(name, log_file, level=logging.INFO):
    """
    设置日志记录器 - 使用TimedRotatingFileHandler自动按日期切换

    Args:
        name: 日志记录器名称
        log_file: 日志文件路径（基础路径，不含日期）
        level: 日志级别

    Returns:
        logger: 配置好的日志记录器
    """
    # 如果已经存在，直接返回缓存的logger
    if name in _logger_cache:
        return _logger_cache[name]

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 🔧 防止重复添加handlers
    if logger.handlers:
        logger.handlers.clear()

    # 🎯 使用TimedRotatingFileHandler - 每天午夜自动切换日志文件
    # when='midnight': 每天午夜切换
    # interval=1: 每1天切换一次
    # backupCount=30: 保留30天的日志文件
    # encoding='utf-8': 使用UTF-8编码
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setLevel(level)

    # 设置日志文件名后缀格式为日期
    file_handler.suffix = "%Y%m%d"

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


def get_logger(name='gold_arbitrage'):
    """
    获取默认日志记录器 - 使用TimedRotatingFileHandler自动按日期切换

    Args:
        name: 日志记录器名称

    Returns:
        logger: 配置好的日志记录器
    """
    # 如果已经存在，直接返回
    if name in _logger_cache:
        return _logger_cache[name]

    # 创建日志目录
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 基础日志文件名（不含日期，TimedRotatingFileHandler会自动添加）
    log_file = os.path.join(log_dir, 'gold_arbitrage.log')

    logger = setup_logger(name, log_file)
    print(f"📅 [日志系统] 初始化日志记录器: {name} -> {log_file}")
    print(f"📅 [日志系统] 日志文件将在每天午夜自动切换，保留30天历史")

    return logger
