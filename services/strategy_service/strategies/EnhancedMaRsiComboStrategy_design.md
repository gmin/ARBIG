"""
问题1：金叉死叉的检测
    瞬间检测：刚发生交叉就立即信号？
    确认检测：交叉后再等1-2个K线确认？
    强度检测：要求交叉时有一定的角度/幅度？
问题2：RSI的确认条件
    RSI > 50 vs RSI < 70：
        RSI > 50：确认多头强势，但可能错过早期机会
        RSI < 70：避免追高，但可能在强势中错失机会
        组合使用：50 < RSI < 70 最佳区间？
    RSI < 50 vs RSI > 30：
        RSI < 50：确认空头强势
        RSI > 30：避免杀跌
        组合使用：30 < RSI < 50 最佳区间？
问题3：信号的时序关系
    同时满足：金叉和RSI条件必须在同一个K线满足？
    先后满足：允许在几个K线内先后满足条件？
    优先级：金叉优先还是RSI优先？
问题4：防假突破机制
    最小交叉幅度：MA5和MA20的差值要达到多少？
    持续时间：交叉后要维持多长时间才确认？
    成交量确认：是否需要成交量配合？
问题5：震荡市过滤
    如何识别震荡：MA5和MA20距离太近？
    震荡时策略：停止交易还是调整参数？
    趋势强度：如何量化趋势的强弱？
"""

"""
回答和抉择：

问题1：关于金叉死叉检测的问题，有三个选项。这里的关键是理解不同选择的利弊：
"瞬间检测"反应快但假信号多；
"确认检测"可靠性高但会滞后；
"强度检测"能过滤噪音但可能错过温和转折。
实战中，我们可以使用确认检测（1-2根K线）结合幅度过滤，在反应速度和可靠性间取得平衡

问题2：RSI确认条件的问题，这个问题难点在于避免过度优化。
RSI>50确实可能错过早期机会，
RSI<70又可能在强势市场中过早出场。
50-70区间是个不错的折中，但要注意不同品种特性可能不同。黄金趋势性较强，或许可以适当放宽上限

问题3：时序关系问题，这个问题涉及信号同步问题。严格要求同一根K线满足所有条件会大幅减少交易机会，
但允许先后满足又可能引入逻辑不一致。还是优先保证主信号（金叉/死叉）的质量，辅助指标可以在前后1-2根K线内满足即可。

问题4：防假突破机制这个问题，是专业策略的关键。除了幅度、持续时间、成交量三个维度，
还可以考虑波动率自适应阈值——在市场波动大时要求更严格的突破条件。

问题5：震荡市过滤问题，可能是五个问题中最重要的一环。传统ADX指标有时滞后，可以结合均线通道宽度（MA20与MA5的距离比例）和ATR来实时识别震荡市。
在震荡市中，要么停止交易，要么切换到均值回归模式——但这需要另一套完全不同的规则
"""

"""
参数优化建议
参数	推荐值	说明
快线周期	8-12	敏感但不至于过度交易
慢线周期	25-35	捕捉主要趋势
RSI周期	12-16	平衡敏感度和稳定性
RSI多头阈值	42-48	避免错过早期信号
RSI空头阈值	52-58	避免过早反转
确认K线数	1-2	平衡速度和可靠性
"""

import numpy as np
import pandas as pd
from vnpy.trader.utility import ArrayManager
from vnpy_ctastrategy import CtaTemplate

class EnhancedDualMATrendStrategy(CtaTemplate):
    """增强型双均线趋势策略"""
    
    author = "Gold Quant"
    
    # 策略参数
    fast_window = 10    # 快线周期
    slow_window = 30    # 慢线周期
    rsi_window = 14     # RSI周期
    rsi_long_level = 45  # 多头RSI阈值
    rsi_short_level = 55 # 空头RSI阈值
    trend_threshold = 0.0015  # 趋势强度阈值
    min_cross_distance = 0.002  # 最小交叉幅度
    confirmation_bars = 1      # 确认K线数
    
    parameters = [
        "fast_window", "slow_window", "rsi_window",
        "rsi_long_level", "rsi_short_level", 
        "trend_threshold", "min_cross_distance", "confirmation_bars"
    ]
    
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        # K线管理器
        self.am = ArrayManager(size=100)
        
        # 状态变量
        self.cross_status = 0  # 0:无交叉, 1:金叉, -1:死叉
        self.confirmation_count = 0
        self.last_cross_price = 0
        
    def on_bar(self, bar: BarData):
        """K线更新"""
        # 更新K线数据
        self.am.update_bar(bar)
        if not self.am.inited:
            return
        
        # 计算技术指标
        fast_ma = self.am.sma(self.fast_window)
        slow_ma = self.am.sma(self.slow_window)
        rsi = self.am.rsi(self.rsi_window)
        
        # 检测金叉死叉
        cross_signal = self.detect_cross(fast_ma, slow_ma, bar.close_price)
        
        # 检查RSI条件
        rsi_condition = self.check_rsi_condition(rsi, cross_signal)
        
        # 趋势强度过滤
        trend_strength = self.measure_trend_strength(fast_ma, slow_ma)
        
        # 生成交易信号
        if (cross_signal != 0 and rsi_condition and 
            trend_strength > self.trend_threshold):
            
            if cross_signal == 1:
                self.execute_long_strategy(bar)
            else:
                self.execute_short_strategy(bar)
        
        self.put_event()

"""问题1：金叉死叉检测解决方案"""
"""1.1 智能交叉检测系统"""
def detect_cross(self, fast_ma, slow_ma, current_price):
    """智能交叉检测"""
    # 计算当前差值
    current_diff = fast_ma - slow_ma
    prev_diff = self.am.fast_ma[-2] - self.am.slow_ma[-2]
    
    # 1. 瞬间检测（初步信号）
    if current_diff * prev_diff <= 0:  # 发生交叉
        cross_type = 1 if current_diff > 0 else -1
        
        # 2. 强度检测：检查交叉幅度
        cross_strength = abs(current_diff) / slow_ma
        if cross_strength < self.min_cross_distance:
            return 0  # 交叉幅度不足，忽略
        
        # 3. 确认检测：等待确认K线
        if self.cross_status == 0:  # 新交叉
            self.cross_status = cross_type
            self.confirmation_count = 1
            self.last_cross_price = current_price
            return 0  # 等待确认
        elif self.cross_status == cross_type:  # 同方向继续
            self.confirmation_count += 1
            if self.confirmation_count >= self.confirmation_bars:
                # 确认完成，重置状态
                self.cross_status = 0
                self.confirmation_count = 0
                return cross_type
        else:  # 反向交叉，重置
            self.cross_status = 0
            self.confirmation_count = 0
            
    return 0

"""1.2 交叉强度量化标准"""
def calculate_cross_quality(self, fast_ma, slow_ma):
    """计算交叉质量"""
    # 1. 角度强度（斜率变化）
    fast_slope = fast_ma - self.am.fast_ma[-5]
    slow_slope = slow_ma - self.am.slow_ma[-5]
    slope_ratio = fast_slope / slow_slope if slow_slope != 0 else 0
    
    # 2. 幅度强度
    ma_diff = abs(fast_ma - slow_ma) / slow_ma
    
    # 3. 价格确认
    price_confirmation = 1 if (
        (fast_ma > slow_ma and self.am.close[-1] > fast_ma) or
        (fast_ma < slow_ma and self.am.close[-1] < fast_ma)
    ) else 0
    
    # 综合评分
    quality_score = slope_ratio * 0.4 + ma_diff * 0.4 + price_confirmation * 0.2
    return quality_score

"""问题2：RSI确认条件优化"""
"""2.1 动态RSI阈值系统"""
def check_rsi_condition(self, rsi, cross_signal):
    """动态RSI条件检查"""
    if cross_signal == 0:
        return False
    
    # 根据市场波动率调整RSI阈值
    volatility = self.am.std(20) / self.am.close[-1]
    adjusted_long_level = self.rsi_long_level
    adjusted_short_level = self.rsi_short_level
    
    # 高波动市场放宽条件
    if volatility > 0.02:
        adjusted_long_level = max(40, self.rsi_long_level - 5)
        adjusted_short_level = min(60, self.rsi_short_level + 5)
    
    # 根据交叉方向检查RSI
    if cross_signal == 1:  # 金叉
        # 多头条件：RSI不能太高（避免追高），但要有上升动力
        rsi_rising = rsi > self.am.rsi(self.rsi_window)[-2]
        return adjusted_long_level <= rsi <= 65 and rsi_rising
        
    else:  # 死叉
        # 空头条件：RSI不能太低（避免杀跌），但要有下降动力
        rsi_falling = rsi < self.am.rsi(self.rsi_window)[-2]
        return 35 <= rsi <= adjusted_short_level and rsi_falling
    
"""2.2 RSI动量确认"""
def check_rsi_momentum(self):
    """RSI动量确认"""
    rsi = self.am.rsi(self.rsi_window)
    rsi_prev = self.am.rsi(self.rsi_window)[-2]
    
    # RSI变化率
    rsi_change = rsi - rsi_prev
    
    # RSI方向一致性（最近3根K线）
    rsi_trend = sum(np.diff(self.am.rsi(self.rsi_window)[-3:]))
    
    # 动量确认条件
    if abs(rsi_change) > 2 and rsi_trend * rsi_change > 0:
        return True
    return False

"""问题3：信号时序关系处理"""
"""3.1 信号同步与优先级系统"""
def manage_signal_timing(self, cross_signal, rsi_condition):
    """信号时序管理"""
    # 信号状态机
    if cross_signal != 0 and not hasattr(self, 'signal_state'):
        # 新信号出现
        self.signal_state = {
            'cross_signal': cross_signal,
            'cross_time': self.am.datetime[-1],
            'rsi_condition': False,
            'timeout_count': 0
        }
    
    if hasattr(self, 'signal_state'):
        # 检查RSI条件是否满足
        if not self.signal_state['rsi_condition'] and rsi_condition:
            self.signal_state['rsi_condition'] = True
        
        # 检查超时（3根K线内必须满足所有条件）
        self.signal_state['timeout_count'] += 1
        if self.signal_state['timeout_count'] > 3:
            # 超时清除
            delattr(self, 'signal_state')
            return 0
        
        # 所有条件满足
        if self.signal_state['rsi_condition']:
            signal = self.signal_state['cross_signal']
            delattr(self, 'signal_state')
            return signal
    
    return 0

"""问题4：防假突破机制"""
"""4.1 多重假突破过滤器"""
def filter_false_breakout(self, cross_signal):
    """假突破过滤"""
    # 1. 成交量确认
    volume_confirm = self.am.volume[-1] > self.am.volume[-5:].mean() * 1.2
    
    # 2. 价格位置确认
    if cross_signal == 1:  # 金叉
        price_confirm = self.am.close[-1] > self.am.high[-5:].max()
    else:  # 死叉
        price_confirm = self.am.close[-1] < self.am.low[-5:].min()
    
    # 3. 持续时间确认（交叉后价格维持）
    if cross_signal != 0:
        maintain_bars = 2  # 需要维持2根K线
        if len(self.am.close) > maintain_bars:
            if cross_signal == 1:
                maintain_confirm = all(self.am.close[-maintain_bars:] > 
                                     self.am.slow_ma[-maintain_bars:])
            else:
                maintain_confirm = all(self.am.close[-maintain_bars:] < 
                                     self.am.slow_ma[-maintain_bars:])
        else:
            maintain_confirm = False
    else:
        maintain_confirm = False
    
    # 综合确认（满足2个条件即可）
    confirm_count = sum([volume_confirm, price_confirm, maintain_confirm])
    return confirm_count >= 2

"""问题5：震荡市识别与过滤"""
"""5.1 市场状态识别系统"""
def identify_market_regime(self):
    """识别市场状态"""
    fast_ma = self.am.sma(self.fast_window)
    slow_ma = self.am.sma(self.slow_window)
    
    # 1. 均线距离指标
    ma_distance = abs(fast_ma - slow_ma) / slow_ma
    
    # 2. ADX趋势强度
    adx_value = self.am.adx(14) if len(self.am.close) > 28 else 0
    
    # 3. 价格波动率
    volatility = self.am.atr(14) / self.am.close[-1]
    
    # 4. 均线斜率（趋势方向）
    ma_slope = fast_ma - self.am.fast_ma[-5]
    
    # 市场状态分类
    if adx_value > 25 and ma_distance > 0.01:
        return "trending"  # 趋势市
    elif adx_value < 20 and ma_distance < 0.005:
        return "ranging"   # 震荡市
    elif volatility > 0.025:
        return "volatile"  # 高波动市
    else:
        return "transition"  # 转换期

def adjust_strategy_for_market_regime(self, market_regime):
    """根据市场状态调整策略 - 旧版（已废弃）"""
    if market_regime == "ranging":
        # 震荡市：收紧参数，减少交易
        self.min_cross_distance = 0.003  # 提高交叉幅度要求
        self.trend_threshold = 0.002     # 提高趋势强度要求
        return False  # 暂停交易或减少仓位

    elif market_regime == "trending":
        # 趋势市：放宽参数，积极交易
        self.min_cross_distance = 0.001
        self.trend_threshold = 0.001
        return True

    elif market_regime == "volatile":
        # 高波动市：谨慎交易，严格止损
        self.min_cross_distance = 0.002
        return True

    else:
        # 转换期：观望
        return False

"""
================================================================================
5.2 差异化市场状态交易策略 (2025-12-06 实现)
================================================================================

核心思想：不同市场状态采用完全不同的交易逻辑，而不是简单的开关

市场状态识别阈值（针对黄金期货优化）：
- trending:   MA距离 > 0.2%  (约2元差距)
- ranging:    MA距离 < 0.05% 且 波动率 < 0.8%
- volatile:   波动率 > 1.5%
- transition: 其他情况

差异化交易策略：
+------------+---------------------------+----------+----------+
| 市场状态   | 交易条件                  | 仓位比例 | 止损倍数 |
+------------+---------------------------+----------+----------+
| ranging    | RSI<30做多, RSI>70做空    | 50%      | 1.0x     |
| transition | MA交叉+放宽RSI条件        | 30%      | 1.0x     |
| trending   | MA交叉+RSI确认+趋势强度   | 100%     | 1.0x     |
| volatile   | RSI<25做多, RSI>75做空    | 50%      | 1.5x     |
+------------+---------------------------+----------+----------+
"""

# 新增参数
REGIME_PARAMS = {
    # 震荡市区间交易参数
    'ranging_rsi_oversold': 30,       # 超卖阈值（做多）
    'ranging_rsi_overbought': 70,     # 超买阈值（做空）
    'ranging_tp_ratio': 0.5,          # 区间止盈比例
    'ranging_position_ratio': 0.5,    # 震荡市仓位比例

    # 转换期参数
    'transition_position_ratio': 0.3, # 转换期仓位比例（轻仓试探）

    # 高波动市参数
    'volatile_stop_multiplier': 1.5,  # 高波动止损扩大倍数
    'volatile_position_ratio': 0.5,   # 高波动仓位比例
}

def _generate_trading_signal(self, bar, fast_ma, slow_ma, rsi):
    """
    差异化市场状态交易信号生成 - 主分发函数

    根据市场状态分发到不同交易逻辑
    """
    # 1. 识别市场状态
    market_regime = self._identify_market_regime(fast_ma, slow_ma)
    self.current_regime = market_regime

    # 2. 根据市场状态分发到不同交易逻辑
    if market_regime == "ranging":
        self._generate_ranging_signal(bar, rsi, fast_ma, slow_ma)
    elif market_regime == "transition":
        self._generate_transition_signal(bar, fast_ma, slow_ma, rsi)
    elif market_regime == "trending":
        self._generate_trending_signal(bar, fast_ma, slow_ma, rsi)
    elif market_regime == "volatile":
        self._generate_volatile_signal(bar, fast_ma, slow_ma, rsi)

def _generate_ranging_signal(self, bar, rsi, fast_ma, slow_ma):
    """
    震荡市区间交易策略

    逻辑：
    - RSI < 30 → 做多（超卖反弹）
    - RSI > 70 → 做空（超买回落）
    - 仓位：50%
    - 止盈目标：区间中线
    """
    # 超卖做多
    if rsi < self.ranging_rsi_oversold:
        signal = {
            'action': 'BUY',
            'reason': f"震荡市RSI超卖反弹({rsi:.1f})",
            'regime': 'ranging',
            'position_ratio': self.ranging_position_ratio  # 0.5
        }
        self._process_trading_signal(signal, bar.close_price)

    # 超买做空
    elif rsi > self.ranging_rsi_overbought:
        signal = {
            'action': 'SELL',
            'reason': f"震荡市RSI超买回落({rsi:.1f})",
            'regime': 'ranging',
            'position_ratio': self.ranging_position_ratio  # 0.5
        }
        self._process_trading_signal(signal, bar.close_price)

def _generate_transition_signal(self, bar, fast_ma, slow_ma, rsi):
    """
    转换期轻仓试探策略

    逻辑：
    - 检测MA交叉信号
    - 放宽RSI条件（金叉RSI<65，死叉RSI>35）
    - 轻仓试探（仓位30%）
    """
    cross_signal = self._detect_ma_cross(bar.close_price, fast_ma, slow_ma)
    if cross_signal == 0:
        return

    # 放宽的RSI条件
    if cross_signal == 1 and rsi > 65:  # 金叉但RSI太高
        return
    if cross_signal == -1 and rsi < 35:  # 死叉但RSI太低
        return

    signal = {
        'action': 'BUY' if cross_signal == 1 else 'SELL',
        'reason': f"转换期{'金叉' if cross_signal == 1 else '死叉'}轻仓试探({rsi:.1f})",
        'regime': 'transition',
        'position_ratio': self.transition_position_ratio  # 0.3
    }
    self._process_trading_signal(signal, bar.close_price)

def _generate_trending_signal(self, bar, fast_ma, slow_ma, rsi):
    """
    趋势市趋势跟踪策略

    逻辑：
    - MA交叉确认趋势
    - RSI条件严格检查
    - 趋势强度达标
    - 防假突破过滤
    - 完整仓位操作（100%）
    """
    cross_signal = self._detect_ma_cross(bar.close_price, fast_ma, slow_ma)
    rsi_condition = self._check_rsi_condition(rsi, cross_signal)
    trend_strength = self._measure_trend_strength(fast_ma, slow_ma)
    breakout_valid = self._filter_false_breakout(cross_signal, bar.close_price)

    if cross_signal != 0 and rsi_condition and trend_strength > self.trend_threshold and breakout_valid:
        signal = {
            'action': 'BUY' if cross_signal == 1 else 'SELL',
            'reason': f"趋势市{'金叉' if cross_signal == 1 else '死叉'}({rsi:.1f})",
            'regime': 'trending',
            'position_ratio': 1.0  # 全仓
        }
        self._process_trading_signal(signal, bar.close_price)

def _generate_volatile_signal(self, bar, fast_ma, slow_ma, rsi):
    """
    高波动市谨慎交易策略

    逻辑：
    - 只在极端RSI时交易（<25 或 >75）
    - 减小仓位（50%）
    - 扩大止损（1.5倍）
    """
    if rsi < 25:  # 极度超卖
        signal = {
            'action': 'BUY',
            'reason': f"高波动市极度超卖({rsi:.1f})",
            'regime': 'volatile',
            'position_ratio': self.volatile_position_ratio,  # 0.5
            'stop_multiplier': self.volatile_stop_multiplier  # 1.5
        }
        self._process_trading_signal(signal, bar.close_price)

    elif rsi > 75:  # 极度超买
        signal = {
            'action': 'SELL',
            'reason': f"高波动市极度超买({rsi:.1f})",
            'regime': 'volatile',
            'position_ratio': self.volatile_position_ratio,  # 0.5
            'stop_multiplier': self.volatile_stop_multiplier  # 1.5
        }
        self._process_trading_signal(signal, bar.close_price)

"""
执行方法修改：

_process_trading_signal() 需要处理新的参数：
- position_ratio: 仓位比例
- stop_multiplier: 止损倍数

_execute_buy_signal() 和 _execute_sell_signal() 增加参数：
- position_ratio: float = 1.0
- stop_multiplier: float = 1.0

_calculate_stop_loss() 增加参数：
- stop_multiplier: float = 1.0
"""

    """完整信号生成逻辑"""
def generate_trading_signal(self):
    """生成交易信号"""
    # 计算指标
    fast_ma = self.am.sma(self.fast_window)
    slow_ma = self.am.sma(self.slow_window)
    rsi = self.am.rsi(self.rsi_window)
    
    # 1. 检测交叉信号
    cross_signal = self.detect_cross(fast_ma, slow_ma, self.am.close[-1])
    
    # 2. 检查市场状态
    market_regime = self.identify_market_regime()
    trade_allowed = self.adjust_strategy_for_market_regime(market_regime)
    
    if not trade_allowed:
        return 0
    
    # 3. 检查RSI条件
    rsi_condition = self.check_rsi_condition(rsi, cross_signal)
    
    # 4. 检查趋势强度
    trend_strength = self.measure_trend_strength(fast_ma, slow_ma)
    
    # 5. 防假突破检查
    false_breakout_filter = self.filter_false_breakout(cross_signal)
    
    # 6. 信号时序管理
    final_signal = self.manage_signal_timing(cross_signal, rsi_condition)
    
    # 最终确认
    if (final_signal != 0 and rsi_condition and 
        trend_strength > self.trend_threshold and 
        false_breakout_filter):
        
        return final_signal
    
    return 0

    # 15分钟K线参数优化
OPTIMAL_PARAMS = {
    # 均线参数
    'fast_ma': 12,    # 3小时窗口
    'slow_ma': 36,    # 9小时窗口
    
    # RSI参数
    'rsi_period': 14,
    'rsi_oversold': 42,
    'rsi_overbought': 58,
    
    # 止损参数
    'atr_period': 14,
    'stop_loss_atr': 2.5,
    'take_profit_atr': 3.0,
    
    # 时间过滤器
    'avoid_open_minutes': 15,  # 避开开盘前15分钟
    'night_session_only': False,  # 是否只交易夜盘
}

def night_session_adjustment(self, current_time):
    """夜盘特殊处理"""
    if self.is_night_session(current_time):
        # 夜盘波动大，调整参数
        adjusted_params = {
            'fast_ma': 10,  # 更敏感的均线
            'stop_loss_atr': 3.0,  # 更大的止损
            'min_volume': 1500,  # 更高的成交量要求
        }
        return adjusted_params
    else:
        return self.default_params

class RiskManagementSystem:
    """专业风险管理系统"""
    
    def __init__(self, capital, strategy_config):
        # 资金配置
        self.capital = capital
        self.risk_per_trade = 0.02  # 单笔风险2%
        self.risk_per_day = 0.05    # 单日风险5%
        self.max_drawdown = 0.15    # 最大回撤15%
        
        # 策略配置
        self.config = strategy_config
        self.position_size = 0
        self.daily_pnl = 0
        self.equity_peak = capital
        
        # 交易记录
        self.trade_history = []
        
    def calculate_position_size(self, entry_price, stop_loss_price):
        """
        计算仓位大小 - 基于风险的仓位管理
        """
        # 1. 计算单笔风险金额
        risk_amount = min(
            self.capital * self.risk_per_trade,
            (self.capital * self.risk_per_day - self.daily_pnl)
        )
        
        # 2. 计算每手风险
        risk_per_contract = abs(entry_price - stop_loss_price) * self.config['contract_multiplier']
        
        if risk_per_contract <= 0:
            return 0
            
        # 3. 计算合约数量
        contracts = int(risk_amount / risk_per_contract)
        
        # 4. 资金约束检查
        max_capital_contracts = int(self.capital * 0.5 / (entry_price * self.config['contract_multiplier']))
        contracts = min(contracts, max_capital_contracts)
        
        # 5. 流动性约束
        contracts = min(contracts, self.config['max_position_limit'])
        
        return max(1, contracts)  # 至少1手
    
    def dynamic_stop_loss(self, entry_price, position_type, volatility):
        """
        动态止损计算
        """
        # 基于ATR的止损
        atr = volatility * entry_price
        
        if position_type == 'long':
            # 多头止损
            stop_loss = entry_price - self.config['stop_loss_atr'] * atr
            
            # 附加支撑位检测
            support_level = self.find_support_level()
            if support_level > stop_loss:
                stop_loss = support_level * 0.99  # 在支撑位下方一点点
                
        else:
            # 空头止损
            stop_loss = entry_price + self.config['stop_loss_atr'] * atr
            
            # 附加阻力位检测
            resistance_level = self.find_resistance_level()
            if resistance_level < stop_loss:
                stop_loss = resistance_level * 1.01  # 在阻力位上方一点点
                
        return stop_loss
    
    def trailing_stop_loss(self, current_price, position_type, initial_stop):
        """
        移动止损（追踪止损）
        """
        if not hasattr(self, 'best_price'):
            self.best_price = current_price
            
        # 更新最佳价格
        if position_type == 'long':
            self.best_price = max(self.best_price, current_price)
            new_stop = self.best_price - (self.best_price - initial_stop) * 0.5
        else:
            self.best_price = min(self.best_price, current_price)
            new_stop = self.best_price + (initial_stop - self.best_price) * 0.5
            
        return new_stop
    
    def take_profit_strategy(self, entry_price, position_type, volatility):
        """
        止盈策略 - 多层止盈
        """
        atr = volatility * entry_price
        
        if position_type == 'long':
            # 三层止盈目标
            targets = [
                entry_price + self.config['take_profit_1'] * atr,  # 第一目标
                entry_price + self.config['take_profit_2'] * atr,  # 第二目标
                entry_price + self.config['take_profit_3'] * atr   # 第三目标
            ]
        else:
            targets = [
                entry_price - self.config['take_profit_1'] * atr,
                entry_price - self.config['take_profit_2'] * atr,
                entry_price - self.config['take_profit_3'] * atr
            ]
            
        return targets
    
    def execute_risk_checks(self):
        """
        执行风险检查
        """
        # 1. 单日亏损检查
        if self.daily_pnl < -self.capital * self.risk_per_day:
            self.close_all_positions()
            return False
            
        # 2. 最大回撤检查
        current_equity = self.capital + self.daily_pnl
        drawdown = (self.equity_peak - current_equity) / self.equity_peak
        
        if drawdown > self.max_drawdown:
            self.close_all_positions()
            self.equity_peak = current_equity  # 重置峰值
            return False
            
        # 3. 连续亏损检查
        if self.check_consecutive_losses():
            self.reduce_position_size(0.5)  # 减半仓位
            return True
            
        return True
    
    def check_consecutive_losses(self, max_losses=3):
        """检查连续亏损"""
        if len(self.trade_history) < max_losses:
            return False
            
        recent_trades = self.trade_history[-max_losses:]
        losses = [t for t in recent_trades if t['pnl'] < 0]
        
        return len(losses) >= max_losses

def fixed_fractional_position_sizing(self, risk_percentage):
    """
    固定分数仓位管理
    每笔交易风险资金 = 总资金 × 风险百分比
    """
    risk_amount = self.capital * risk_percentage
    risk_per_share = self.entry_price - self.stop_loss_price
    
    if risk_per_share <= 0:
        return 0
        
    position_size = risk_amount / risk_per_share
    return int(position_size)

# 使用示例
risk_per_trade = 0.02  # 每笔交易风险2%
position_size = fixed_fractional_position_sizing(risk_per_trade)


def kelly_position_sizing(self, win_rate, win_loss_ratio):
    """
    凯利公式仓位管理
    f* = p - (1-p)/b
    where p=win rate, b=win/loss ratio
    """
    if win_loss_ratio <= 0:
        return 0
        
    kelly_percent = win_rate - (1 - win_rate) / win_loss_ratio
    # 保守使用半凯利
    half_kelly = kelly_percent * 0.5
    
    return max(0.01, min(half_kelly, 0.1))  # 限制在1%-10%

def volatility_adjusted_position_sizing(self, current_volatility, avg_volatility):
    """
    基于波动率的仓位调整
    """
    vol_ratio = current_volatility / avg_volatility
    
    # 高波动率减少仓位，低波动率增加仓位
    if vol_ratio > 1.5:
        adjustment = 0.5  # 减半仓位
    elif vol_ratio > 1.2:
        adjustment = 0.8  # 减少20%
    elif vol_ratio < 0.8:
        adjustment = 1.2  # 增加20%
    elif vol_ratio < 0.5:
        adjustment = 1.5  # 增加50%
    else:
        adjustment = 1.0  # 不变
        
    return adjustment

def set_initial_stop_loss(self, entry_price, position_type):
    """设置初始止损"""
    # 方法1: ATR止损
    atr = self.am.atr(14)
    atr_stop = atr * self.config['stop_loss_atr']
    
    # 方法2: 百分比止损
    percent_stop = entry_price * self.config['stop_loss_percent']
    
    # 方法3: 支撑阻力止损
    technical_stop = self.find_technical_stop(entry_price, position_type)
    
    # 选择最保守的止损
    if position_type == 'long':
        stop_loss = max(technical_stop, entry_price - atr_stop, entry_price - percent_stop)
    else:
        stop_loss = min(technical_stop, entry_price + atr_stop, entry_price + percent_stop)
    
    return stop_loss

def trailing_stop_management(self, current_price, position_type):
    """移动止损管理"""
    if not hasattr(self, 'best_price'):
        self.best_price = current_price
        
    # 更新最佳价格
    if position_type == 'long':
        self.best_price = max(self.best_price, current_price)
        # 回撤止损：从最高点回撤一定比例
        stop_loss = self.best_price * (1 - self.config['trailing_stop_percent'])
    else:
        self.best_price = min(self.best_price, current_price)
        stop_loss = self.best_price * (1 + self.config['trailing_stop_percent'])
    
    return stop_loss

def partial_take_profit(self, current_price, entry_price, position_type):
    """分批止盈"""
    profit_pct = abs(current_price - entry_price) / entry_price
    
    # 第一目标：风险回报比1:1
    if profit_pct >= self.config['take_profit_1'] and not self.tp1_hit:
        close_percent = 0.3  # 平仓30%
        self.tp1_hit = True
        return close_percent
        
    # 第二目标：风险回报比2:1
    elif profit_pct >= self.config['take_profit_2'] and not self.tp2_hit:
        close_percent = 0.3  # 再平仓30%
        self.tp2_hit = True
        return close_percent
        
    # 第三目标：移动止损
    elif profit_pct >= self.config['take_profit_3']:
        # 剩余仓位使用移动止损
        trailing_stop = self.trailing_stop_management(current_price, position_type)
        if (position_type == 'long' and current_price < trailing_stop) or \
           (position_type == 'short' and current_price > trailing_stop):
            return 1.0  # 平掉剩余仓位
            
    return 0.0

class TradingExecutor:
    """交易执行器"""
    
    def execute_trade(self, signal, market_data):
        """执行交易"""
        # 1. 风险检查
        if not self.risk_system.execute_risk_checks():
            return None
            
        # 2. 计算仓位
        entry_price = market_data['close']
        stop_loss = self.risk_system.dynamic_stop_loss(
            entry_price, signal['type'], market_data['volatility']
        )
        
        position_size = self.risk_system.calculate_position_size(entry_price, stop_loss)
        
        # 3. 设置止盈目标
        take_profit_levels = self.risk_system.take_profit_strategy(
            entry_price, signal['type'], market_data['volatility']
        )
        
        # 4. 执行订单
        if signal['type'] == 'long':
            order_id = self.buy(entry_price, position_size)
        else:
            order_id = self.short(entry_price, position_size)
            
        # 5. 设置止损单
        self.set_stop_loss(order_id, stop_loss)
        
        # 6. 设置止盈单（分批）
        for i, tp_level in enumerate(take_profit_levels):
            tp_size = position_size * self.config['tp_weights'][i]
            self.set_take_profit(order_id, tp_level, tp_size)
            
        return order_id
    
    def monitor_and_adjust(self, order_id, market_data):
        """监控和调整"""
        # 移动止损更新
        new_stop = self.risk_system.trailing_stop_loss(
            market_data['close'], 
            self.positions[order_id]['type'],
            self.positions[order_id]['stop_loss']
        )

        # 更新止损
        if new_stop != self.positions[order_id]['stop_loss']:
            self.update_stop_loss(order_id, new_stop)

        # 部分止盈检查
        close_percent = self.risk_system.partial_take_profit(
            market_data['close'],
            self.positions[order_id]['entry_price'],
            self.positions[order_id]['type']
        )

        if close_percent > 0:
            self.partial_close(order_id, close_percent)

---

## 5.3 Bug修复：ATR为0导致止损价=入场价 (2025-12-08 修复)

### 问题描述

2025年12月8日上午9:49-9:51期间，策略出现异常交易行为：
- 09:50:00 开多 @955.32
- 09:50:12 止损触发 @955.34（仅12秒后！）
- 09:51:00 再次开多 @955.12
- 09:51:37 止损触发 @955.16（仅37秒后！）

日志显示：`🛑 [止损触发] 当前价格=955.34, 止损价=955.34`

**止损价 = 当前价格**，这完全不对！

### 根本原因

在 `_calculate_stop_loss` 函数中，条件检查有bug：

```python
# 修复前
atr = self.am.atr(14) if len(self.am.close_array) >= 14 else entry_price * 0.01
```

**问题分析：**
1. `len(self.am.close_array)` 总是等于数组初始化大小（100），所以条件总是 True
2. 但 `self.am.atr(14)` 在 `self.am.inited = False` 时返回 0
3. 当 ATR = 0 时：`stop_loss = entry_price - 2.0 * 0 = entry_price`
4. 止损价 = 入场价，任何价格波动都会触发止损！

### 修复方案

```python
# 修复后
atr = self.am.atr(14) if self.am.inited else 0

# 如果 ATR 为 0 或太小，使用 fallback 值（黄金期货约 0.5 元）
min_atr = 0.5  # 黄金期货最小 ATR 约 0.5 元
if atr < min_atr:
    atr = max(min_atr, entry_price * 0.0005)  # 至少 0.05% 的价格
    logger.warning(f"⚠️ [止损计算] ATR过小({atr:.4f})，使用最小值: {min_atr}")
```

### 修复效果

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| ATR = 0 | 止损距离 = 0 | 止损距离 = 1.0元 (2×0.5) |
| ATR = 0.44 | 止损距离 = 0.88元 | 止损距离 = 0.88元 |
| ATR = 0.3 | 止损距离 = 0.6元 | 止损距离 = 1.0元 (使用最小值) |

### 经验教训

1. **数组长度检查不等于数据有效性检查**：`len(array)` 返回的是数组容量，不是有效数据数量
2. **关键计算需要fallback值**：ATR等技术指标可能返回0，需要有合理的默认值
3. **添加日志输出**：关键计算步骤需要日志，方便调试

---

## 5.4 Bug修复：信号间隔边界条件问题 (2025-12-09 修复)

### 问题描述

2025年12月9日上午交易中发现，每分钟都可能发出新信号，导致频繁开平仓：
- 09:03:00 SHORT @954.90（开空）
- 09:04:00 SHORT @955.16（再次开空信号）
- 09:04:32 COVER @955.04（平仓）

### 根本原因

信号间隔检查使用 `<` 而非 `<=`：

```python
# 旧代码
if current_time - self.last_signal_time < self.min_signal_interval:
    return
```

当 `min_signal_interval = 60` 秒时：
- 09:03:00 发信号，`last_signal_time = 09:03:00`
- 09:04:00 检查：`09:04:00 - 09:03:00 = 60`，`60 < 60` 为 False，通过检查！

### 修复方案

将 `<` 改为 `<=`：

```python
# 修复后
if current_time - self.last_signal_time <= self.min_signal_interval:
    return
```

### 修改位置

- 文件：`EnhancedMaRsiComboStrategy.py`
- 行号：241

### 经验教训

1. **边界条件检查**：`<` 和 `<=` 的区别在边界情况下很重要
2. **时间间隔应使用 `<=`**：确保间隔时间严格大于设定值

---

## 5.5 Bug修复：重复开仓问题 (2025-12-09 修复)

### 问题描述

2025年12月9日下午交易中发现，策略在已有持仓的情况下继续发送同方向开仓信号：
- 14:35:00 SHORT @951.88（开空，此时有多头1手）
- 14:36:00 SHORT @952.00（又开空，变成空头2手）
- 14:36:34 COVER @952.26（平1手空）

### 根本原因

四个信号生成函数（`_generate_ranging_signal`、`_generate_transition_signal`、`_generate_trending_signal`、`_generate_volatile_signal`）在发送信号前**没有检查当前持仓状态**。

当满足技术指标条件时，会直接发送开仓信号，不管是否已有同方向持仓。

### 修复方案

在每个信号生成函数开头添加持仓检查：

```python
# 检查当前持仓，避免重复开仓
current_pos = self.cached_position

# 做多信号时，检查是否已有多头
if current_pos > 0:
    logger.debug("已有多头持仓，跳过做多信号")
    return

# 做空信号时，检查是否已有空头
if current_pos < 0:
    logger.debug("已有空头持仓，跳过做空信号")
    return
```

### 修改位置

| 函数 | 行号 | 修改内容 |
|------|------|----------|
| `_generate_ranging_signal` | 287-334 | 添加 `current_pos` 检查 |
| `_generate_transition_signal` | 336-378 | 添加 `current_pos` 检查 |
| `_generate_trending_signal` | 380-425 | 添加 `current_pos` 检查 |
| `_generate_volatile_signal` | 427-473 | 添加 `current_pos` 检查 |

### 修复效果

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 已有空头，RSI超买 | 再发开空信号 | 跳过，不发信号 |
| 已有多头，RSI超卖 | 再发开多信号 | 跳过，不发信号 |

### 经验教训

1. **信号生成前必须检查持仓**：避免在已有同方向持仓时重复开仓
2. **使用 `cached_position` 而非查询**：避免查询延迟导致的误判
3. **所有信号生成函数都需要统一检查**：确保一致性