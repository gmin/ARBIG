"""
日志工具模块
提供统一的日志记录功能
"""

import logging
import os
from datetime import datetime

# 全局logger缓存，避免重复创建handlers
_logger_cache = {}

# 系统日志的当前日期跟踪
_current_system_log_date = None

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

# 创建默认日志记录器 - 支持按日期自动切换
def get_logger(name='gold_arbitrage'):
    """
    获取默认日志记录器 - 支持按日期自动切换文件

    Args:
        name: 日志记录器名称

    Returns:
        logger: 配置好的日志记录器
    """
    global _current_system_log_date

    # 获取当前日期
    today = datetime.now().strftime("%Y%m%d")

    # 如果日期变化，清理缓存强制重新创建
    if _current_system_log_date != today:
        # 清理旧的logger缓存
        if name in _logger_cache:
            old_logger = _logger_cache[name]
            # 关闭所有handlers
            for handler in old_logger.handlers[:]:
                handler.close()
                old_logger.removeHandler(handler)
            # 从缓存中移除
            del _logger_cache[name]

        _current_system_log_date = today
        print(f"📅 [系统日志] 切换到新日期: {today}")

    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(
        log_dir,
        f'gold_arbitrage_{today}.log'
    )

    return setup_logger(name, log_file)

def clear_logger_cache():
    """清理logger缓存（用于测试或重启）"""
    global _logger_cache
    _logger_cache.clear()
