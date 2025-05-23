"""
黄金跨市场套利策略
"""
from datetime import datetime
from typing import Dict, Optional
from loguru import logger

from vnpy.trader.utility import BarGenerator, ArrayManager
from vnpy.trader.object import TickData, BarData, OrderData, TradeData
from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData
)

from ..config import STRATEGY_PARAMS


class GoldArbitrageStrategy(CtaTemplate):
    """
    黄金跨市场套利策略
    """
    author = "ARBIG"

    # 策略参数
    base_spread_threshold = STRATEGY_PARAMS["base_spread_threshold"]
    max_position = STRATEGY_PARAMS["max_position"]
    min_profit = STRATEGY_PARAMS["min_profit"]
    max_loss = STRATEGY_PARAMS["max_loss"]
    order_timeout = STRATEGY_PARAMS["order_timeout"]

    # 策略变量
    spread = 0.0  # 当前价差
    sh_position = 0  # 上海市场持仓
    hk_position = 0  # 香港市场持仓
    last_trade_time = None  # 上次交易时间

    # 参数列表
    parameters = [
        "base_spread_threshold",
        "max_position",
        "min_profit",
        "max_loss",
        "order_timeout"
    ]

    # 变量列表
    variables = [
        "spread",
        "sh_position",
        "hk_position",
        "last_trade_time"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbols, setting):
        """
        初始化策略
        """
        super().__init__(cta_engine, strategy_name, vt_symbols, setting)

        # 创建K线生成器对象
        self.bg_sh = BarGenerator(self.on_bar)
        self.bg_hk = BarGenerator(self.on_bar)

        # 创建技术指标计算对象
        self.am_sh = ArrayManager()
        self.am_hk = ArrayManager()

        # 订单字典
        self.orders: Dict[str, OrderData] = {}

    def on_init(self):
        """
        策略初始化完成后的回调函数
        """
        self.write_log("策略初始化完成")
        self.load_bar(10)  # 加载10天的历史数据用于初始化

    def on_start(self):
        """
        策略启动完成后的回调函数
        """
        self.write_log("策略启动完成")

    def on_stop(self):
        """
        策略停止后的回调函数
        """
        self.write_log("策略停止完成")

    def on_tick(self, tick: TickData):
        """
        行情数据更新回调函数
        """
        # 更新K线生成器
        if tick.vt_symbol == self.vt_symbols[0]:  # 上海市场
            self.bg_sh.update_tick(tick)
        else:  # 香港市场
            self.bg_hk.update_tick(tick)

        # 计算价差
        self.calculate_spread()

        # 检查交易信号
        self.check_trading_signals()

    def on_bar(self, bar: BarData):
        """
        K线数据更新回调函数
        """
        # 更新技术指标
        if bar.vt_symbol == self.vt_symbols[0]:  # 上海市场
            self.am_sh.update_bar(bar)
        else:  # 香港市场
            self.am_hk.update_bar(bar)

        # 计算价差
        self.calculate_spread()

        # 检查交易信号
        self.check_trading_signals()

    def calculate_spread(self):
        """
        计算两个市场的价差
        """
        if not self.am_sh.inited or not self.am_hk.inited:
            return

        # 获取最新价格
        sh_price = self.am_sh.close[-1]
        hk_price = self.am_hk.close[-1]

        # 计算价差（考虑汇率因素）
        self.spread = hk_price - sh_price

    def check_trading_signals(self):
        """
        检查交易信号
        """
        if not self.am_sh.inited or not self.am_hk.inited:
            return

        # 检查是否达到开仓条件
        if abs(self.spread) >= self.base_spread_threshold:
            if self.spread > 0:  # 香港价格高于上海价格
                self.open_arbitrage_long()
            else:  # 上海价格高于香港价格
                self.open_arbitrage_short()

        # 检查是否达到平仓条件
        self.check_close_signals()

    def open_arbitrage_long(self):
        """
        开仓做多套利（买入上海，卖出香港）
        """
        if self.sh_position >= self.max_position or self.hk_position <= -self.max_position:
            return

        # 发送开仓订单
        self.buy(self.vt_symbols[0], self.am_sh.close[-1], 1)  # 买入上海
        self.short(self.vt_symbols[1], self.am_hk.close[-1], 1)  # 卖出香港

    def open_arbitrage_short(self):
        """
        开仓做空套利（买入香港，卖出上海）
        """
        if self.sh_position <= -self.max_position or self.hk_position >= self.max_position:
            return

        # 发送开仓订单
        self.buy(self.vt_symbols[1], self.am_hk.close[-1], 1)  # 买入香港
        self.short(self.vt_symbols[0], self.am_sh.close[-1], 1)  # 卖出上海

    def check_close_signals(self):
        """
        检查平仓信号
        """
        # 检查是否达到止损条件
        if abs(self.spread) >= self.max_loss:
            self.close_all_positions()
            return

        # 检查是否达到止盈条件
        if abs(self.spread) <= self.min_profit:
            self.close_all_positions()

    def close_all_positions(self):
        """
        平掉所有持仓
        """
        if self.sh_position > 0:
            self.sell(self.vt_symbols[0], self.am_sh.close[-1], abs(self.sh_position))
        elif self.sh_position < 0:
            self.cover(self.vt_symbols[0], self.am_sh.close[-1], abs(self.sh_position))

        if self.hk_position > 0:
            self.sell(self.vt_symbols[1], self.am_hk.close[-1], abs(self.hk_position))
        elif self.hk_position < 0:
            self.cover(self.vt_symbols[1], self.am_hk.close[-1], abs(self.hk_position))

    def on_order(self, order: OrderData):
        """
        订单更新回调函数
        """
        self.orders[order.vt_orderid] = order

    def on_trade(self, trade: TradeData):
        """
        成交更新回调函数
        """
        # 更新持仓
        if trade.vt_symbol == self.vt_symbols[0]:  # 上海市场
            if trade.direction == "多":
                self.sh_position += trade.volume
            else:
                self.sh_position -= trade.volume
        else:  # 香港市场
            if trade.direction == "多":
                self.hk_position += trade.volume
            else:
                self.hk_position -= trade.volume

        # 更新最后交易时间
        self.last_trade_time = datetime.now()

        # 输出成交信息
        self.write_log(
            f"成交: {trade.vt_symbol}, 方向: {trade.direction}, "
            f"价格: {trade.price}, 数量: {trade.volume}"
        ) 
