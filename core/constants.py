"""
事件类型常量定义
"""

# 行情事件
TICK_EVENT = "TICK_EVENT"           # Tick行情事件
BAR_EVENT = "BAR_EVENT"             # K线事件

# 交易事件
ORDER_EVENT = "ORDER_EVENT"         # 订单事件
TRADE_EVENT = "TRADE_EVENT"         # 成交事件
ACCOUNT_EVENT = "ACCOUNT_EVENT"     # 账户事件

# 策略事件
SIGNAL_EVENT = "SIGNAL_EVENT"       # 策略信号事件
SPREAD_EVENT = "SPREAD_EVENT"       # 基差事件

# 系统事件
LOG_EVENT = "LOG_EVENT"             # 日志事件
ERROR_EVENT = "ERROR_EVENT"         # 错误事件 