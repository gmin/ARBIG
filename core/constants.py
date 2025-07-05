"""
常量定义
定义系统中使用的各种常量
"""

# 事件类型
TICK_EVENT = "TICK_EVENT"           # Tick行情事件
BAR_EVENT = "BAR_EVENT"             # K线事件
SIGNAL_EVENT = "SIGNAL_EVENT"       # 策略信号事件
ORDER_EVENT = "ORDER_EVENT"         # 订单事件
TRADE_EVENT = "TRADE_EVENT"         # 成交事件
ACCOUNT_EVENT = "ACCOUNT_EVENT"     # 账户事件
POSITION_EVENT = "POSITION_EVENT"   # 持仓事件
RISK_EVENT = "RISK_EVENT"           # 风险事件
SERVICE_EVENT = "SERVICE_EVENT"     # 服务事件
SPREAD_EVENT = "SPREAD_EVENT"       # 基差事件
LOG_EVENT = "LOG_EVENT"             # 日志事件
ERROR_EVENT = "ERROR_EVENT"         # 错误事件

# 服务名称
SERVICE_MARKET_DATA = "market_data"
SERVICE_ACCOUNT = "account"
SERVICE_TRADING = "trading"
SERVICE_RISK = "risk"

# 交易所代码
EXCHANGE_SHFE = "SHFE"  # 上海期货交易所

# 合约代码
SYMBOL_AU_MAIN = "AU2509"  # 黄金主力合约
SYMBOL_AU_NEXT = "AU2512"  # 黄金次主力合约

# 风险级别
RISK_LEVEL_LOW = "LOW"
RISK_LEVEL_MEDIUM = "MEDIUM"
RISK_LEVEL_HIGH = "HIGH"
RISK_LEVEL_CRITICAL = "CRITICAL"

# 订单状态映射
ORDER_STATUS_MAP = {
    "0": "SUBMITTING",    # 正在提交
    "1": "NOTTRADED",     # 未成交
    "2": "PARTTRADED",    # 部分成交
    "3": "ALLTRADED",     # 全部成交
    "4": "CANCELLED",     # 已撤销
    "5": "REJECTED"       # 已拒绝
}

# 方向映射
DIRECTION_MAP = {
    "0": "LONG",   # 多头
    "1": "SHORT"   # 空头
}

# 开平仓映射
OFFSET_MAP = {
    "0": "OPEN",        # 开仓
    "1": "CLOSE",       # 平仓
    "2": "CLOSETODAY",  # 平今
    "3": "CLOSEYESTERDAY"  # 平昨
}