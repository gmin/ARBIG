"""
配置文件
包含系统运行所需的各种参数配置
"""

CONFIG = {
    # 数据源配置
    'shfe': {
        'gateway_name': 'CTP',
        'host': '',           # CTP服务器地址
        'port': 0,            # CTP服务器端口
        'user': '242407',           # 用户名
        'password': '1234%^&*QWE',       # 密码
        'broker_id': '9999',      # 经纪商代码
        'app_id': '',         # 应用ID
        'auth_code': '',      # 认证码
        'symbol': 'AU2508',   # 合约代码
    },
    
    
    'mt5': {
        'server': '',         # MT5服务器地址
        'port': 0,            # MT5服务器端口
        'login': 0,           # 账号
        'password': '',       # 密码
        'symbol': 'XAUUSD',   # 合约代码
    },
    
    # 数据更新配置
    'data': {
        'update_interval': 1,     # 数据更新间隔（秒）
        'max_delay': 5,           # 最大允许延迟（秒）
        'retry_interval': 1,      # 重试间隔（秒）
        'max_retries': 3,         # 最大重试次数
    },
    
    # 基差套利阈值配置（元/克）
    'spread_arbitrage': {
        # 核心阈值
        'entry_threshold': 0.8,      # 开仓阈值：基差超过此值时开仓
        'exit_threshold': 0.2,       # 平仓阈值：基差回归到此值时平仓
        
        # 交易成本
        'transaction_cost': 0.1,       # 单次交易成本（手续费+滑点）
        'min_profit': 0.3,             # 最小利润要求
        
        # 持仓管理
        'max_hold_time': 3600,         # 最大持仓时间（秒）
    },
    
    # 基差阈值（元/克）- 保留向后兼容
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
    
    # 交易时间
    'trading_hours': {
        'start': '09:00:00',
        'end': '15:30:00'
    },
    
    # 数据存储配置
    'storage': {
        'mongodb': {
            'host': 'localhost',
            'port': 27017,
            'database': 'gold_arbitrage',
            'collections': {
                'tick_data': 'ticks',
                'trade_data': 'trades',
                'position_data': 'positions'
            }
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'db': 0
        }
    }
}
