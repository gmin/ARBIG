"""
配置文件
包含系统运行所需的各种参数配置
"""

CONFIG = {
    # 主力合约配置
    'main_contract': {
        'symbol': 'au2510',
        'name': '黄金主力',
        'exchange': 'SHFE',
        'description': '上海期货交易所黄金主力合约'
    },

    # 支持的合约列表
    'supported_contracts': [
        {'symbol': 'au2510', 'name': '黄金主力', 'exchange': 'SHFE', 'category': '贵金属', 'is_main': True},
        {'symbol': 'ag2510', 'name': '白银主力', 'exchange': 'SHFE', 'category': '贵金属', 'is_main': False},
        {'symbol': 'cu2510', 'name': '铜主力', 'exchange': 'SHFE', 'category': '有色金属', 'is_main': False}
    ],

    # 自动订阅的合约
    'auto_subscribe_contracts': ['au2510'],

    # 数据源配置 (保留兼容性)
    'shfe': {
        'gateway_name': 'CTP',
        'host': '',           # CTP服务器地址
        'port': 0,            # CTP服务器端口
        'user': '242407',           # 用户名
        'password': '1234%^&*QWE',       # 密码
        'broker_id': '9999',      # 经纪商代码
        'app_id': '',         # 应用ID
        'auth_code': '',      # 认证码
    },
    
    

    
    # 数据更新配置
    'data': {
        'update_interval': 1,     # 数据更新间隔（秒）
        'max_delay': 5,           # 最大允许延迟（秒）
        'retry_interval': 1,      # 重试间隔（秒）
        'max_retries': 3,         # 最大重试次数
    },
    
    # SHFE量化策略配置
    'shfe_quant': {
        # 价格阈值
        'price_threshold_high': 450,   # 高价阈值：价格超过此值时卖出
        'price_threshold_low': 440,    # 低价阈值：价格低于此值时买入

        # 交易成本
        'transaction_cost': 0.1,       # 单次交易成本（手续费+滑点）
        'min_profit': 0.3,             # 最小利润要求

        # 持仓管理
        'max_hold_time': 3600,         # 最大持仓时间（秒）
    },
    
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
        }
    }
}

# 配置工具函数
def get_main_contract():
    """获取主力合约配置"""
    return CONFIG['main_contract']

def get_supported_contracts():
    """获取支持的合约列表"""
    return CONFIG['supported_contracts']

def get_auto_subscribe_contracts():
    """获取自动订阅的合约列表"""
    return CONFIG['auto_subscribe_contracts']

def get_main_contract_symbol():
    """获取主力合约代码"""
    return CONFIG['main_contract']['symbol']
