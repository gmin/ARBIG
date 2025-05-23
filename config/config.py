"""
配置文件
包含系统运行所需的各种参数配置
"""

CONFIG = {
    # 基差阈值（元/克）
    'spread_threshold': 0.5,
    
    # 交易参数
    'max_position': 1000,     # 最大持仓（克）
    'max_loss': 10000,        # 最大亏损（元）
    'trade_interval': 1,      # 交易间隔（秒）
    
    # 日志配置
    'log_level': 'INFO',      # 日志级别
    'log_file': 'gold_arbitrage.log',  # 日志文件名
    
    # 风控参数
    'max_drawdown': 0.1,      # 最大回撤
    'position_limit': 0.8,    # 仓位限制（占总资金比例）
    
    # 交易时间（预留）
    'trading_hours': {
        'start': '09:00:00',
        'end': '15:30:00'
    }
}
