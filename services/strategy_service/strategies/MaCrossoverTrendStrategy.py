"""
双均线策略示例
基于ARBIGCtaTemplate实现的经典双均线交易策略
"""

from typing import Dict, Any
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from vnpy.trader.utility import ArrayManager
from utils.logger import get_logger

logger = get_logger(__name__)

class MaCrossoverTrendStrategy(ARBIGCtaTemplate):
    """
    双均线策略
    
    策略逻辑：
    1. 计算快速均线和慢速均线
    2. 快线上穿慢线时买入开仓
    3. 快线下穿慢线时卖出平仓
    4. 支持止损和止盈
    """
    
    # 策略参数
    parameters = [
        "ma_short",      # 快速均线周期
        "ma_long",       # 慢速均线周期
        "max_position",  # 最大持仓
        "stop_loss",     # 止损比例
        "take_profit"    # 止盈比例
    ]
    
    # 策略变量
    variables = [
        "ma_short_value",    # 快速均线值
        "ma_long_value",     # 慢速均线值
        "ma_trend",          # 均线趋势
        "entry_price",       # 入场价格
        "last_signal"        # 最后信号
    ]
    
    def __init__(self, strategy_name: str, symbol: str, setting: Dict[str, Any], signal_sender):
        """初始化策略"""
        # 默认参数
        self.ma_short = 5        # 快速均线周期
        self.ma_long = 20        # 慢速均线周期
        self.max_position = 1    # 最大持仓（手）
        self.stop_loss = 0.02    # 2%止损
        self.take_profit = 0.04  # 4%止盈
        
        # 策略变量
        self.ma_short_value = 0.0
        self.ma_long_value = 0.0
        self.ma_trend = 0        # 1:多头, -1:空头, 0:震荡
        self.entry_price = 0.0
        self.last_signal = ""
        
        # 调用父类初始化
        super().__init__(strategy_name, symbol, setting, signal_sender)
        
        # 创建数组管理器
        self.am = ArrayManager(size=100)
        
        logger.info(f"双均线策略初始化: {strategy_name} MA({self.ma_short},{self.ma_long})")
    
    def on_init(self) -> None:
        """策略初始化"""
        self.write_log("双均线策略初始化完成")
    
    def on_start(self) -> None:
        """策略启动"""
        self.write_log("双均线策略启动")
    
    def on_stop(self) -> None:
        """策略停止"""
        self.write_log("双均线策略停止")
    
    def on_tick_impl(self, tick: TickData) -> None:
        """Tick数据处理"""
        # 双均线策略基于K线，不处理Tick
        pass
    
    def on_bar_impl(self, bar: BarData) -> None:
        """K线数据处理"""
        # 更新数组管理器
        self.am.update_bar(bar)
        
        # 检查数据是否足够
        if not self.am.inited:
            return
        
        # 计算均线
        self.ma_short_value = self.am.sma(self.ma_short)
        self.ma_long_value = self.am.sma(self.ma_long)
        
        if self.ma_short_value == 0 or self.ma_long_value == 0:
            return
        
        # 判断均线趋势
        cross_over = self.ma_short_value > self.ma_long_value and self.ma_trend <= 0
        cross_under = self.ma_short_value < self.ma_long_value and self.ma_trend >= 0
        
        # 更新趋势状态
        if self.ma_short_value > self.ma_long_value:
            self.ma_trend = 1
        elif self.ma_short_value < self.ma_long_value:
            self.ma_trend = -1
        else:
            self.ma_trend = 0
        
        # 交易逻辑
        current_price = bar.close_price
        
        # 多头信号：快线上穿慢线且无持仓
        if cross_over and self.pos == 0:
            self.buy(current_price, self.max_position)
            self.entry_price = current_price
            self.last_signal = "BUY"
            self.write_log(f"多头开仓: {current_price} MA短:{self.ma_short_value:.2f} MA长:{self.ma_long_value:.2f}")
        
        # 空头信号：快线下穿慢线且无持仓
        elif cross_under and self.pos == 0:
            self.short(current_price, self.max_position)
            self.entry_price = current_price
            self.last_signal = "SHORT"
            self.write_log(f"空头开仓: {current_price} MA短:{self.ma_short_value:.2f} MA长:{self.ma_long_value:.2f}")
        
        # 平仓逻辑
        elif self.pos != 0:
            self._check_exit_conditions(current_price)
        
        # 记录关键信息
        if len(self.bars) % 10 == 0:  # 每10根K线记录一次
            self.write_log(f"价格:{current_price:.2f} MA短:{self.ma_short_value:.2f} "
                          f"MA长:{self.ma_long_value:.2f} 持仓:{self.pos} 趋势:{self.ma_trend}")
    
    def _check_exit_conditions(self, current_price: float) -> None:
        """检查平仓条件"""
        if self.entry_price == 0:
            return
        
        # 计算盈亏比例
        if self.pos > 0:  # 多头持仓
            pnl_ratio = (current_price - self.entry_price) / self.entry_price
            
            # 止损或止盈
            if pnl_ratio <= -self.stop_loss:
                self.sell(current_price, abs(self.pos))
                self.write_log(f"多头止损: {current_price:.2f} 损失:{pnl_ratio:.2%}")
                self._reset_position()
            elif pnl_ratio >= self.take_profit:
                self.sell(current_price, abs(self.pos))
                self.write_log(f"多头止盈: {current_price:.2f} 收益:{pnl_ratio:.2%}")
                self._reset_position()
            # 趋势反转平仓
            elif self.ma_trend == -1 and self.ma_short_value < self.ma_long_value:
                self.sell(current_price, abs(self.pos))
                self.write_log(f"多头趋势反转平仓: {current_price:.2f}")
                self._reset_position()
        
        elif self.pos < 0:  # 空头持仓
            pnl_ratio = (self.entry_price - current_price) / self.entry_price
            
            # 止损或止盈
            if pnl_ratio <= -self.stop_loss:
                self.cover(current_price, abs(self.pos))
                self.write_log(f"空头止损: {current_price:.2f} 损失:{pnl_ratio:.2%}")
                self._reset_position()
            elif pnl_ratio >= self.take_profit:
                self.cover(current_price, abs(self.pos))
                self.write_log(f"空头止盈: {current_price:.2f} 收益:{pnl_ratio:.2%}")
                self._reset_position()
            # 趋势反转平仓
            elif self.ma_trend == 1 and self.ma_short_value > self.ma_long_value:
                self.cover(current_price, abs(self.pos))
                self.write_log(f"空头趋势反转平仓: {current_price:.2f}")
                self._reset_position()
    
    def _reset_position(self) -> None:
        """重置持仓相关变量"""
        self.entry_price = 0.0
        self.last_signal = ""
    
    def on_trade_impl(self, trade) -> None:
        """成交处理"""
        self.write_log(f"策略成交: {trade.direction.value} {trade.volume}手@{trade.price:.2f}")
    
    def on_order_impl(self, order) -> None:
        """订单状态处理"""
        self.write_log(f"订单状态: {order.status.value} {order.direction.value} {order.volume}手@{order.price:.2f}")
    
    def get_strategy_data(self) -> Dict[str, Any]:
        """获取策略数据（用于监控界面）"""
        return {
            "ma_short_value": round(self.ma_short_value, 2),
            "ma_long_value": round(self.ma_long_value, 2),
            "ma_trend": self.ma_trend,
            "entry_price": round(self.entry_price, 2),
            "last_signal": self.last_signal,
            "current_price": round(self.am.close, 2) if self.am.inited else 0,
            "position": self.pos,
            "total_trades": self.total_trades,
            "total_pnl": round(self.total_pnl, 2)
        }
