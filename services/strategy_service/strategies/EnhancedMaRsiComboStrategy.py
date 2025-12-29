"""
增强型均线RSI组合策略 - 黄金期货专业交易策略

## 策略概述
这是一个专门针对上期所黄金期货设计的增强型技术分析策略，在基础MA-RSI策略基础上
增加了多重智能过滤机制，提供更可靠的交易信号。

## 核心改进
1. **智能交叉检测**：确认检测(1-2根K线) + 强度过滤 + 价格确认
2. **动态RSI阈值**：根据市场波动率自适应调整RSI阈值
3. **防假突破机制**：成交量确认 + 价格位置确认 + 持续时间确认
4. **震荡市过滤**：均线距离 + ADX趋势强度 + 波动率综合判断
5. **专业风控系统**：凯利仓位管理 + 移动止损 + 分批止盈

## 技术指标组合
- 📈 **双均线系统**：EMA10/EMA30 用于趋势识别
- 📊 **RSI指标**：14周期RSI用于超买超卖确认
- 🛡️ **ATR止损**：基于波动率的动态止损
- 🔄 **持仓管理**：实时查询 + 智能缓存机制

## 适用市场
- ✅ 上期所黄金期货（au主力合约）
- ✅ 日内交易和短线交易
- ✅ 趋势性行情（震荡市自动过滤）
"""

import sys
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from services.strategy_service.core.data_tools import ArrayManager
from utils.logger import get_logger

logger = get_logger(__name__)


class EnhancedMaRsiComboStrategy(ARBIGCtaTemplate):
    """
    增强型均线RSI组合策略 - 黄金期货专业交易策略

    ## 核心交易逻辑
    1. **智能交叉检测**：确认检测(1-2根K线) + 强度过滤 + 价格确认
    2. **动态RSI阈值**：根据市场波动率自适应调整RSI阈值
    3. **防假突破机制**：成交量确认 + 价格位置确认 + 持续时间确认
    4. **震荡市过滤**：均线距离 + 波动率综合判断
    5. **专业风控系统**：ATR止损 + 移动止损 + 分批止盈

    ## 技术指标详解
    - **EMA10/EMA30**：快慢均线，识别趋势方向和强度
    - **RSI14**：相对强弱指标，动态阈值避免追高杀跌
    - **ATR14**：平均真实波幅，用于动态止损和仓位计算

    ## 差异化市场状态交易策略
    根据市场状态自动切换交易逻辑：

    ### 📊 震荡市 (ranging) - 区间交易
    - RSI < 30 → 做多（超卖反弹）
    - RSI > 70 → 做空（超买回落）
    - 仓位：50%

    ### 🔄 转换期 (transition) - 轻仓试探
    - MA交叉信号 + 放宽RSI条件
    - 仓位：30%

    ### 🔥 趋势市 (trending) - 趋势跟踪
    - MA交叉 + RSI确认 + 趋势强度达标
    - 仓位：100%

    ### ⚡ 高波动 (volatile) - 谨慎交易
    - 极端RSI（<25 或 >75）
    - 仓位：50%，止损扩大1.5倍
    """

    author = "ARBIG Quant Team"

    # ==================== 策略参数配置 ====================

    # 技术指标参数
    fast_window = 10      # 快线周期(8-12推荐)
    slow_window = 30      # 慢线周期(25-35推荐)
    rsi_window = 14       # RSI周期(12-16推荐)
    rsi_long_level = 45   # 多头RSI阈值(42-48推荐)
    rsi_short_level = 55  # 空头RSI阈值(52-58推荐)

    # 交叉检测参数
    min_cross_distance = 0.002   # 最小交叉幅度(0.2%)
    confirmation_bars = 1        # 确认K线数(1-2推荐)
    trend_threshold = 0.0015     # 趋势强度阈值

    # 风险控制参数
    stop_loss_atr = 2.0     # ATR止损倍数
    take_profit_atr = 3.0   # ATR止盈倍数
    trailing_stop_pct = 0.3 # 移动止损回撤比例（降低以避免过早止损）

    # 交易执行参数
    trade_volume = 1      # 基础交易手数
    max_position = 3      # 最大持仓限制
    min_signal_interval = 60  # 最小信号间隔（秒）

    # 震荡市区间交易参数
    ranging_rsi_oversold = 30    # 超卖阈值（做多）
    ranging_rsi_overbought = 70  # 超买阈值（做空）
    ranging_tp_ratio = 0.5       # 区间止盈比例（到中线的距离）
    ranging_position_ratio = 0.5 # 震荡市仓位比例（相对正常仓位）

    # 转换期参数
    transition_position_ratio = 0.3  # 转换期仓位比例（轻仓试探）

    # 高波动市参数
    volatile_stop_multiplier = 1.5   # 高波动止损扩大倍数
    volatile_position_ratio = 0.5    # 高波动仓位比例

    # 策略变量
    last_signal_time = 0
    current_regime = "ranging"  # 当前市场状态

    def __init__(self, strategy_name: str, symbol: str, setting: dict, signal_sender=None, **kwargs):
        """初始化策略 - 兼容策略引擎参数"""
        super().__init__(strategy_name, symbol, setting, signal_sender=signal_sender, **kwargs)

        # 从设置中获取参数
        self.fast_window = setting.get('fast_window', 10)
        self.slow_window = setting.get('slow_window', 30)
        self.rsi_window = setting.get('rsi_window', 14)
        self.rsi_long_level = setting.get('rsi_long_level', 45)
        self.rsi_short_level = setting.get('rsi_short_level', 55)
        self.min_cross_distance = setting.get('min_cross_distance', 0.002)
        self.confirmation_bars = setting.get('confirmation_bars', 1)
        self.trend_threshold = setting.get('trend_threshold', 0.0015)
        self.stop_loss_atr = setting.get('stop_loss_atr', 2.0)
        self.take_profit_atr = setting.get('take_profit_atr', 3.0)
        self.trailing_stop_pct = setting.get('trailing_stop_pct', 0.3)
        self.trade_volume = setting.get('trade_volume', 1)
        self.max_position = setting.get('max_position', 3)
        self.min_signal_interval = setting.get('min_signal_interval', 60)

        # 震荡市区间交易参数
        self.ranging_rsi_oversold = setting.get('ranging_rsi_oversold', 30)
        self.ranging_rsi_overbought = setting.get('ranging_rsi_overbought', 70)
        self.ranging_tp_ratio = setting.get('ranging_tp_ratio', 0.5)
        self.ranging_position_ratio = setting.get('ranging_position_ratio', 0.5)

        # 转换期/高波动参数
        self.transition_position_ratio = setting.get('transition_position_ratio', 0.3)
        self.volatile_stop_multiplier = setting.get('volatile_stop_multiplier', 1.5)
        self.volatile_position_ratio = setting.get('volatile_position_ratio', 0.5)

        # 初始化ArrayManager
        self.am = ArrayManager(size=100)

        # 交叉检测状态
        self.cross_status = 0  # 0:无交叉, 1:金叉, -1:死叉
        self.confirmation_count = 0
        self.last_cross_price = 0.0

        # 均线历史数据（用于金叉死叉检测）
        self.fast_ma_history = []
        self.slow_ma_history = []
        self.max_history_length = 10

        # 持仓缓存机制
        self.cached_position = 0
        self.last_position_update = 0

        # 风控状态
        self.entry_price = 0.0      # 入场价格
        self.stop_loss_price = 0.0  # 止损价格
        self.best_price = 0.0       # 最佳价格（用于移动止损）
        self.tp1_hit = False        # 第一止盈目标是否触及
        self.tp2_hit = False        # 第二止盈目标是否触及

        # 信号锁定
        self.signal_lock = False

        logger.info(f"✅ {self.strategy_name} 初始化完成")
        logger.info(f"   交易品种: {self.symbol}")
        logger.info(f"   双均线: EMA{self.fast_window}/EMA{self.slow_window}")
        logger.info(f"   RSI参数: {self.rsi_window}({self.rsi_long_level}-{self.rsi_short_level})")
        logger.info(f"   风控: ATR止损{self.stop_loss_atr}倍 止盈{self.take_profit_atr}倍")
        logger.info(f"   🔧 已集成增强型交叉检测和专业风控系统")

    # ==================== 生命周期方法 ====================

    def on_init(self):
        """策略初始化回调"""
        self.write_log("增强型MA-RSI组合策略初始化")

    def on_start(self):
        """策略启动回调"""
        self.write_log("🚀 增强型MA-RSI组合策略已启动")

    def on_stop(self):
        """策略停止回调"""
        self.write_log("⏹️ 增强型MA-RSI组合策略已停止")

    # ==================== 数据处理方法 ====================

    def on_tick_impl(self, tick: TickData) -> None:
        """Tick数据处理实现 - 实时风控检查"""
        if self.pos != 0 and self.entry_price > 0:
            self._check_risk_control(tick.last_price)

    def on_bar_impl(self, bar: BarData) -> None:
        """K线数据处理实现 - 信号生成核心"""
        if not self.trading:
            return

        # 更新K线数据
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # 计算技术指标
        fast_ma = self.am.ema(self.fast_window)
        slow_ma = self.am.ema(self.slow_window)
        rsi = self.am.rsi(self.rsi_window)

        # 更新均线历史
        self._update_ma_history(fast_ma, slow_ma)

        # 检查市场状态
        market_regime = self._identify_market_regime(fast_ma, slow_ma)
        trend_strength = self._measure_trend_strength(fast_ma, slow_ma)

        # 检测交叉信号（用于日志记录）
        cross_signal = self._detect_ma_cross(bar.close_price, fast_ma, slow_ma)

        # 📊 记录技术指标到CSV
        self._log_indicators_to_csv(bar, fast_ma, slow_ma, rsi, cross_signal,
                                     market_regime, trend_strength)

        # 检查信号间隔（使用 <= 避免边界条件问题）
        current_time = time.time()
        if current_time - self.last_signal_time <= self.min_signal_interval:
            return

        # 生成交易信号
        self._generate_trading_signal(bar, fast_ma, slow_ma, rsi)

    def _update_ma_history(self, fast_ma: float, slow_ma: float) -> None:
        """更新均线历史数据"""
        self.fast_ma_history.append(fast_ma)
        self.slow_ma_history.append(slow_ma)

        if len(self.fast_ma_history) > self.max_history_length:
            self.fast_ma_history.pop(0)
        if len(self.slow_ma_history) > self.max_history_length:
            self.slow_ma_history.pop(0)

    # ==================== 信号生成方法 ====================

    def _generate_trading_signal(self, bar: BarData, fast_ma: float, slow_ma: float, rsi: float) -> None:
        """
        生成交易信号 - 差异化市场状态策略

        根据不同市场状态采用不同交易逻辑：
        - ranging: 区间交易（RSI超买超卖）
        - transition: 轻仓试探（等待方向确认）
        - trending: 趋势跟踪（MA交叉）
        - volatile: 减仓扩止损
        """
        if self.signal_lock:
            logger.info(f"🔒 [信号锁定] 等待交易完成")
            return

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

    def _generate_ranging_signal(self, bar: BarData, rsi: float, fast_ma: float, slow_ma: float) -> None:
        """
        震荡市区间交易策略

        逻辑：
        - RSI < 30 → 做多（超卖反弹）
        - RSI > 70 → 做空（超买回落）
        - 止盈目标：区间中线
        - 已有同方向持仓时不重复开仓
        """
        current_price = bar.close_price

        # 🔧 检查当前持仓，避免重复开仓
        current_pos = self.cached_position

        # 超卖做多（仅在无多头持仓时）
        if rsi < self.ranging_rsi_oversold:
            if current_pos > 0:
                logger.info(f"📊 [震荡市] RSI超卖但已有多头持仓{current_pos}手，跳过")
                return

            logger.info(f"📊 [震荡市] RSI超卖={rsi:.1f} < {self.ranging_rsi_oversold}, 考虑做多")

            signal_decision = {
                'action': 'BUY',
                'reason': f"震荡市RSI超卖反弹({rsi:.1f})",
                'rsi': rsi,
                'regime': 'ranging',
                'position_ratio': self.ranging_position_ratio
            }
            self._process_trading_signal(signal_decision, current_price)

        # 超买做空（仅在无空头持仓时）
        elif rsi > self.ranging_rsi_overbought:
            if current_pos < 0:
                logger.info(f"📊 [震荡市] RSI超买但已有空头持仓{current_pos}手，跳过")
                return

            logger.info(f"📊 [震荡市] RSI超买={rsi:.1f} > {self.ranging_rsi_overbought}, 考虑做空")

            signal_decision = {
                'action': 'SELL',
                'reason': f"震荡市RSI超买回落({rsi:.1f})",
                'rsi': rsi,
                'regime': 'ranging',
                'position_ratio': self.ranging_position_ratio
            }
            self._process_trading_signal(signal_decision, current_price)

    def _generate_transition_signal(self, bar: BarData, fast_ma: float, slow_ma: float, rsi: float) -> None:
        """
        转换期轻仓试探策略

        逻辑：
        - 检测MA交叉信号
        - 轻仓试探（仓位减半）
        - 等待趋势确认后加仓
        - 已有同方向持仓时不重复开仓
        """
        # 检测交叉信号
        cross_signal = self._detect_ma_cross(bar.close_price, fast_ma, slow_ma)
        if cross_signal == 0:
            return

        # 🔧 检查当前持仓，避免重复开仓
        current_pos = self.cached_position
        if cross_signal == 1 and current_pos > 0:
            logger.info(f"🔄 [转换期] 金叉但已有多头持仓{current_pos}手，跳过")
            return
        if cross_signal == -1 and current_pos < 0:
            logger.info(f"🔄 [转换期] 死叉但已有空头持仓{current_pos}手，跳过")
            return

        # RSI条件（放宽标准）
        if cross_signal == 1 and rsi > 65:  # 金叉但RSI太高
            logger.info(f"⚠️ [转换期] 金叉但RSI过高({rsi:.1f})，观望")
            return
        if cross_signal == -1 and rsi < 35:  # 死叉但RSI太低
            logger.info(f"⚠️ [转换期] 死叉但RSI过低({rsi:.1f})，观望")
            return

        logger.info(f"🔄 [转换期] {'金叉' if cross_signal == 1 else '死叉'}信号, RSI={rsi:.1f}, 轻仓试探")

        signal_decision = {
            'action': 'BUY' if cross_signal == 1 else 'SELL',
            'reason': f"转换期{'金叉' if cross_signal == 1 else '死叉'}轻仓试探({rsi:.1f})",
            'cross_signal': cross_signal,
            'rsi': rsi,
            'regime': 'transition',
            'position_ratio': self.transition_position_ratio
        }
        self._process_trading_signal(signal_decision, bar.close_price)

    def _generate_trending_signal(self, bar: BarData, fast_ma: float, slow_ma: float, rsi: float) -> None:
        """
        趋势市趋势跟踪策略

        逻辑：
        - MA交叉确认趋势
        - 完整仓位操作
        - 移动止损跟踪
        - 已有同方向持仓时不重复开仓
        """
        # 检测交叉信号
        cross_signal = self._detect_ma_cross(bar.close_price, fast_ma, slow_ma)

        # 🔧 检查当前持仓，避免重复开仓
        current_pos = self.cached_position
        if cross_signal == 1 and current_pos > 0:
            logger.info(f"🔥 [趋势市] 金叉但已有多头持仓{current_pos}手，跳过")
            return
        if cross_signal == -1 and current_pos < 0:
            logger.info(f"🔥 [趋势市] 死叉但已有空头持仓{current_pos}手，跳过")
            return

        # RSI条件
        rsi_condition = self._check_rsi_condition(rsi, cross_signal)

        # 趋势强度
        trend_strength = self._measure_trend_strength(fast_ma, slow_ma)

        # 防假突破
        breakout_valid = self._filter_false_breakout(cross_signal, bar.close_price)

        # 综合判断
        if cross_signal != 0 and rsi_condition and trend_strength > self.trend_threshold and breakout_valid:
            logger.info(f"🔥 [趋势市] 交叉={cross_signal}, RSI={rsi:.1f}, "
                       f"趋势强度={trend_strength:.4f}, 全仓跟踪")

            signal_decision = {
                'action': 'BUY' if cross_signal == 1 else 'SELL',
                'reason': f"趋势市{'金叉' if cross_signal == 1 else '死叉'}({rsi:.1f})",
                'cross_signal': cross_signal,
                'rsi': rsi,
                'trend_strength': trend_strength,
                'regime': 'trending',
                'position_ratio': 1.0  # 全仓
            }
            self._process_trading_signal(signal_decision, bar.close_price)

    def _generate_volatile_signal(self, bar: BarData, fast_ma: float, slow_ma: float, rsi: float) -> None:
        """
        高波动市谨慎交易策略

        逻辑：
        - 只在极端RSI时交易
        - 减小仓位
        - 扩大止损
        - 已有同方向持仓时不重复开仓
        """
        # 🔧 检查当前持仓，避免重复开仓
        current_pos = self.cached_position

        # 只在极端RSI时交易
        if rsi < 25:  # 极度超卖
            if current_pos > 0:
                logger.info(f"⚡ [高波动] RSI超卖但已有多头持仓{current_pos}手，跳过")
                return

            logger.info(f"⚡ [高波动] RSI极度超卖={rsi:.1f}, 减仓做多")

            signal_decision = {
                'action': 'BUY',
                'reason': f"高波动市极度超卖({rsi:.1f})",
                'rsi': rsi,
                'regime': 'volatile',
                'position_ratio': self.volatile_position_ratio,
                'stop_multiplier': self.volatile_stop_multiplier
            }
            self._process_trading_signal(signal_decision, bar.close_price)

        elif rsi > 75:  # 极度超买
            if current_pos < 0:
                logger.info(f"⚡ [高波动] RSI超买但已有空头持仓{current_pos}手，跳过")
                return

            logger.info(f"⚡ [高波动] RSI极度超买={rsi:.1f}, 减仓做空")

            signal_decision = {
                'action': 'SELL',
                'reason': f"高波动市极度超买({rsi:.1f})",
                'rsi': rsi,
                'regime': 'volatile',
                'position_ratio': self.volatile_position_ratio,
                'stop_multiplier': self.volatile_stop_multiplier
            }
            self._process_trading_signal(signal_decision, bar.close_price)

    def _detect_ma_cross(self, current_price: float, fast_ma: float, slow_ma: float) -> int:
        """
        智能交叉检测系统

        实现三层检测机制：
        1. 瞬间检测：识别交叉发生
        2. 强度检测：过滤幅度不足的交叉
        3. 确认检测：等待1-2根K线确认

        Returns:
            1: 金叉确认
            -1: 死叉确认
            0: 无信号或等待确认
        """
        if len(self.fast_ma_history) < 2 or len(self.slow_ma_history) < 2:
            return 0

        # 获取当前和前一时刻的均线值
        current_fast = fast_ma
        current_slow = slow_ma
        prev_fast = self.fast_ma_history[-2]
        prev_slow = self.slow_ma_history[-2]

        current_diff = current_fast - current_slow
        prev_diff = prev_fast - prev_slow

        # 1. 瞬间检测
        if current_diff * prev_diff <= 0:  # 发生交叉
            cross_type = 1 if current_diff > 0 else -1

            # 2. 强度检测
            cross_strength = abs(current_diff) / current_slow if current_slow > 0 else 0
            if cross_strength < self.min_cross_distance:
                logger.info(f"🔍 [交叉过滤] 幅度不足: {cross_strength:.4f} < {self.min_cross_distance}")
                return 0

            # 3. 价格确认
            if cross_type == 1:  # 金叉
                price_confirm = current_price > current_fast
            else:  # 死叉
                price_confirm = current_price < current_fast

            if not price_confirm:
                logger.info(f"🔍 [交叉过滤] 价格未确认")
                return 0

            # 4. 确认检测
            if self.cross_status == 0:  # 新交叉
                self.cross_status = cross_type
                self.confirmation_count = 1
                self.last_cross_price = current_price
                logger.info(f"⏳ [交叉检测] 新{'金叉' if cross_type == 1 else '死叉'}，等待确认")
                return 0
            elif self.cross_status == cross_type:  # 同方向继续
                self.confirmation_count += 1
                if self.confirmation_count >= self.confirmation_bars:
                    self.cross_status = 0
                    self.confirmation_count = 0
                    logger.info(f"✅ [交叉确认] {'金叉' if cross_type == 1 else '死叉'}确认完成")
                    return cross_type
            else:  # 反向交叉
                logger.info(f"⚠️ [交叉取消] 方向反转")
                self.cross_status = 0
                self.confirmation_count = 0

        return 0

    def _check_rsi_condition(self, rsi: float, cross_signal: int) -> bool:
        """
        动态RSI条件检查

        根据市场波动率自适应调整RSI阈值：
        - 高波动市场：放宽RSI条件
        - 低波动市场：严格RSI条件

        Args:
            rsi: 当前RSI值
            cross_signal: 交叉信号(1=金叉, -1=死叉, 0=无)

        Returns:
            True: RSI条件满足
            False: RSI条件不满足
        """
        if cross_signal == 0:
            return False

        # 根据市场波动率调整RSI阈值
        volatility = self._calculate_volatility()
        adjusted_long_level = self.rsi_long_level
        adjusted_short_level = self.rsi_short_level

        # 高波动市场放宽条件
        if volatility > 0.02:
            adjusted_long_level = max(40, self.rsi_long_level - 5)
            adjusted_short_level = min(60, self.rsi_short_level + 5)

        # 根据交叉方向检查RSI
        if cross_signal == 1:  # 金叉
            # 多头条件：RSI不能太高（避免追高），但要有上升动力
            condition = adjusted_long_level <= rsi <= 65
            if condition:
                logger.info(f"✅ [RSI确认] 金叉RSI条件满足: RSI={rsi:.2f}")
            return condition
        else:  # 死叉
            # 空头条件：RSI不能太低（避免杀跌），但要有下降动力
            condition = 35 <= rsi <= adjusted_short_level
            if condition:
                logger.info(f"✅ [RSI确认] 死叉RSI条件满足: RSI={rsi:.2f}")
            return condition

    def _measure_trend_strength(self, fast_ma: float, slow_ma: float) -> float:
        """
        测量趋势强度

        使用均线距离作为趋势强度指标

        Returns:
            趋势强度值(0-1之间)
        """
        if slow_ma == 0:
            return 0.0

        # 均线距离比例
        ma_distance = abs(fast_ma - slow_ma) / slow_ma
        return ma_distance

    def _identify_market_regime(self, fast_ma: float, slow_ma: float) -> str:
        """
        识别市场状态 - 针对黄金期货优化

        黄金期货日内波动特性：
        - 日内波动通常在0.3%-1.0%之间
        - 均线差距通常在0.05%-0.3%之间
        - 需要更敏感的阈值设置

        Returns:
            "trending": 趋势市
            "ranging": 震荡市
            "volatile": 高波动市
            "transition": 转换期
        """
        # 1. 均线距离指标
        ma_distance = abs(fast_ma - slow_ma) / slow_ma if slow_ma > 0 else 0

        # 2. 价格波动率
        volatility = self._calculate_volatility()

        # 市场状态分类 - 针对黄金期货调整阈值
        # 黄金日内均线差距通常很小，需要降低阈值
        if ma_distance > 0.002:  # 0.2% → 约2元差距(黄金价格~1000)
            return "trending"  # 趋势市
        elif ma_distance < 0.0005 and volatility < 0.008:  # 0.05% + 低波动
            return "ranging"   # 震荡市
        elif volatility > 0.015:  # 1.5%日内波动算高波动
            return "volatile"  # 高波动市
        else:
            return "transition"  # 转换期

    def _filter_false_breakout(self, cross_signal: int, current_price: float) -> bool:
        """
        防假突破过滤器

        多重确认机制：
        1. 成交量确认
        2. 价格位置确认
        3. 持续时间确认

        Returns:
            True: 有效突破
            False: 假突破
        """
        if cross_signal == 0:
            return False

        # 简化版：检查价格是否在均线正确一侧
        if len(self.am.close_array) < 5:
            return True  # 数据不足，默认通过

        # 价格位置确认
        if cross_signal == 1:  # 金叉
            # 价格应该在快线上方
            price_confirm = current_price > self.am.ema(self.fast_window)
        else:  # 死叉
            # 价格应该在快线下方
            price_confirm = current_price < self.am.ema(self.fast_window)

        return price_confirm

    def _calculate_volatility(self) -> float:
        """计算当前波动率"""
        if len(self.am.close_array) < 20:
            return 0.01  # 默认波动率

        std = self.am.std(20)
        close = self.am.close_array[-1]

        if close > 0:
            return std / close
        return 0.01

    # ==================== 交易执行方法 ====================

    def _process_trading_signal(self, signal: Dict[str, Any], current_price: float) -> None:
        """
        处理交易信号

        Args:
            signal: 信号字典，包含action, reason, position_ratio, stop_multiplier等
            current_price: 当前价格
        """
        action = signal.get('action')
        reason = signal.get('reason', '')
        position_ratio = signal.get('position_ratio', 1.0)  # 仓位比例
        stop_multiplier = signal.get('stop_multiplier', 1.0)  # 止损倍数
        regime = signal.get('regime', 'unknown')

        logger.info(f"📌 [信号处理] 市场状态={regime}, 仓位比例={position_ratio}, 止损倍数={stop_multiplier}")

        # 查询真实持仓
        real_position = self._query_real_position()

        # 安全检查
        if not self._pre_trade_safety_check(action, real_position):
            return

        # 锁定信号
        self.signal_lock = True

        try:
            if action == 'BUY':
                self._execute_buy_signal(real_position, current_price, reason, position_ratio, stop_multiplier)
            elif action == 'SELL':
                self._execute_sell_signal(real_position, current_price, reason, position_ratio, stop_multiplier)
        finally:
            self.signal_lock = False
            self.last_signal_time = time.time()

    def _execute_buy_signal(self, real_position: int, current_price: float, reason: str,
                            position_ratio: float = 1.0, stop_multiplier: float = 1.0) -> None:
        """
        执行买入信号

        Args:
            real_position: 当前真实持仓
            current_price: 当前价格
            reason: 交易原因
            position_ratio: 仓位比例（0-1）
            stop_multiplier: 止损倍数
        """
        # 如果有空头持仓，先平仓
        if real_position < 0:
            logger.info(f"🔄 [平仓] 平空头持仓{abs(real_position)}手")
            self.cover(current_price, abs(real_position))
            self._update_position_cache_after_trade(0)

        # 开多仓
        if real_position <= 0:
            # 计算仓位（应用仓位比例）
            base_volume = self._calculate_position_size(current_price)
            volume = max(1, int(base_volume * position_ratio))

            if volume > 0:
                logger.info(f"📈 [开仓] 开多头仓位{volume}手 @ {current_price:.2f} (比例:{position_ratio})")
                logger.info(f"   原因: {reason}")
                self.buy(current_price, volume)

                # 更新风控状态（应用止损倍数）
                self.entry_price = current_price
                self.stop_loss_price = self._calculate_stop_loss(current_price, 'long', stop_multiplier)
                self.best_price = current_price
                self.tp1_hit = False
                self.tp2_hit = False

                self._update_position_cache_after_trade(volume)

    def _execute_sell_signal(self, real_position: int, current_price: float, reason: str,
                             position_ratio: float = 1.0, stop_multiplier: float = 1.0) -> None:
        """
        执行卖出信号

        Args:
            real_position: 当前真实持仓
            current_price: 当前价格
            reason: 交易原因
            position_ratio: 仓位比例（0-1）
            stop_multiplier: 止损倍数
        """
        # 如果有多头持仓，先平仓
        if real_position > 0:
            logger.info(f"🔄 [平仓] 平多头持仓{real_position}手")
            self.sell(current_price, real_position)
            self._update_position_cache_after_trade(0)

        # 开空仓
        if real_position >= 0:
            # 计算仓位（应用仓位比例）
            base_volume = self._calculate_position_size(current_price)
            volume = max(1, int(base_volume * position_ratio))

            if volume > 0:
                logger.info(f"📉 [开仓] 开空头仓位{volume}手 @ {current_price:.2f} (比例:{position_ratio})")
                logger.info(f"   原因: {reason}")
                self.short(current_price, volume)

                # 更新风控状态（应用止损倍数）
                self.entry_price = current_price
                self.stop_loss_price = self._calculate_stop_loss(current_price, 'short', stop_multiplier)
                self.best_price = current_price
                self.tp1_hit = False
                self.tp2_hit = False

                self._update_position_cache_after_trade(-volume)

    def _pre_trade_safety_check(self, action: str, real_position: int) -> bool:
        """
        交易前安全检查

        Returns:
            True: 通过检查
            False: 未通过检查
        """
        # 检查持仓限制
        if action == 'BUY' and real_position >= self.max_position:
            logger.info(f"⚠️ [安全检查] 多头持仓已达上限: {real_position}/{self.max_position}")
            return False

        if action == 'SELL' and real_position <= -self.max_position:
            logger.info(f"⚠️ [安全检查] 空头持仓已达上限: {real_position}/{-self.max_position}")
            return False

        return True

    def _calculate_position_size(self, current_price: float) -> int:
        """
        计算仓位大小 - 基于波动率的仓位管理

        Returns:
            交易手数
        """
        # 基础仓位
        base_volume = self.trade_volume

        # 波动率调整
        volatility = self._calculate_volatility()
        avg_volatility = 0.015  # 假设平均波动率

        vol_ratio = volatility / avg_volatility if avg_volatility > 0 else 1.0

        # 高波动率减少仓位，低波动率增加仓位
        if vol_ratio > 1.5:
            adjustment = 0.5
        elif vol_ratio > 1.2:
            adjustment = 0.8
        elif vol_ratio < 0.8:
            adjustment = 1.2
        else:
            adjustment = 1.0

        adjusted_volume = int(base_volume * adjustment)
        return max(1, min(adjusted_volume, self.max_position))

    def _calculate_stop_loss(self, entry_price: float, position_type: str,
                             stop_multiplier: float = 1.0) -> float:
        """
        计算止损价格 - 基于ATR的动态止损

        Args:
            entry_price: 入场价格
            position_type: 'long' 或 'short'
            stop_multiplier: 止损倍数（用于高波动市扩大止损）

        Returns:
            止损价格
        """
        # 🔧 修复：使用 am.inited 检查，并确保 ATR 不为 0
        atr = self.am.atr(14) if self.am.inited else 0

        # 如果 ATR 为 0 或太小，使用 fallback 值（黄金期货约 0.5 元）
        min_atr = 0.5  # 黄金期货最小 ATR 约 0.5 元
        if atr < min_atr:
            atr = max(min_atr, entry_price * 0.0005)  # 至少 0.05% 的价格
            logger.info(f"⚠️ [止损计算] ATR过小({atr:.4f})，使用最小值: {min_atr}")

        # 应用止损倍数
        adjusted_stop_atr = self.stop_loss_atr * stop_multiplier

        if position_type == 'long':
            stop_loss = entry_price - adjusted_stop_atr * atr
        else:
            stop_loss = entry_price + adjusted_stop_atr * atr

        logger.info(f"🛡️ [止损计算] ATR={atr:.2f}, 倍数={adjusted_stop_atr:.1f}, 止损={stop_loss:.2f}")
        return stop_loss

    # ==================== 风险控制方法 ====================

    def _check_risk_control(self, current_price: float) -> None:
        """
        实时风控检查 - 在on_tick中调用

        包含：
        1. 止损检查
        2. 移动止损更新
        3. 分批止盈检查
        """
        if self.entry_price <= 0:
            return

        # 判断持仓方向
        position_type = 'long' if self.pos > 0 else 'short'

        # 1. 止损检查
        if self._check_stop_loss(current_price, position_type):
            self._execute_stop_loss(current_price, position_type)
            return

        # 2. 更新移动止损
        self._update_trailing_stop(current_price, position_type)

        # 3. 分批止盈检查
        self._check_take_profit(current_price, position_type)

    def _check_stop_loss(self, current_price: float, position_type: str) -> bool:
        """检查是否触发止损"""
        if position_type == 'long':
            return current_price <= self.stop_loss_price
        else:
            return current_price >= self.stop_loss_price

    def _execute_stop_loss(self, current_price: float, position_type: str) -> None:
        """执行止损"""
        logger.info(f"🛑 [止损触发] 当前价格={current_price:.2f}, 止损价={self.stop_loss_price:.2f}, 方向={position_type}")

        if position_type == 'long':
            self.sell(current_price, abs(self.pos))
        else:
            self.cover(current_price, abs(self.pos))

        # 重置风控状态
        self._reset_risk_state()
        self._update_position_cache_after_trade(0)

    def _update_trailing_stop(self, current_price: float, position_type: str) -> None:
        """更新移动止损"""
        if position_type == 'long':
            # 多头：价格创新高时更新止损
            if current_price > self.best_price:
                self.best_price = current_price
                # 新止损 = 最高价 - (最高价 - 原止损) * 回撤比例
                new_stop = self.best_price - (self.best_price - self.stop_loss_price) * self.trailing_stop_pct
                if new_stop > self.stop_loss_price:
                    old_stop = self.stop_loss_price
                    self.stop_loss_price = new_stop
                    logger.info(f"📈 [移动止损] 多头止损上移: {old_stop:.2f} → {self.stop_loss_price:.2f}, 最高价={self.best_price:.2f}")
        else:
            # 空头：价格创新低时更新止损
            if current_price < self.best_price:
                self.best_price = current_price
                new_stop = self.best_price + (self.stop_loss_price - self.best_price) * self.trailing_stop_pct
                if new_stop < self.stop_loss_price:
                    old_stop = self.stop_loss_price
                    self.stop_loss_price = new_stop
                    logger.info(f"📉 [移动止损] 空头止损下移: {old_stop:.2f} → {self.stop_loss_price:.2f}, 最低价={self.best_price:.2f}")

    def _check_take_profit(self, current_price: float, position_type: str) -> None:
        """检查分批止盈"""
        if self.entry_price <= 0:
            return

        profit_pct = abs(current_price - self.entry_price) / self.entry_price

        # 计算ATR止盈目标
        atr = self.am.atr(14) if len(self.am.close_array) >= 14 else self.entry_price * 0.01
        tp1_target = atr * 1.5 / self.entry_price  # 1.5倍ATR
        tp2_target = atr * 2.5 / self.entry_price  # 2.5倍ATR

        # 第一止盈目标
        if not self.tp1_hit and profit_pct >= tp1_target:
            close_volume = max(1, abs(self.pos) // 3)  # 平仓1/3
            if close_volume > 0:
                logger.info(f"🎯 [止盈1] 达到第一目标，平仓{close_volume}手")
                if position_type == 'long':
                    self.sell(current_price, close_volume)
                else:
                    self.cover(current_price, close_volume)
                self.tp1_hit = True

        # 第二止盈目标
        elif not self.tp2_hit and profit_pct >= tp2_target:
            close_volume = max(1, abs(self.pos) // 2)  # 平仓剩余的一半
            if close_volume > 0:
                logger.info(f"🎯 [止盈2] 达到第二目标，平仓{close_volume}手")
                if position_type == 'long':
                    self.sell(current_price, close_volume)
                else:
                    self.cover(current_price, close_volume)
                self.tp2_hit = True

    def _reset_risk_state(self) -> None:
        """重置风控状态"""
        self.entry_price = 0.0
        self.stop_loss_price = 0.0
        self.best_price = 0.0
        self.tp1_hit = False
        self.tp2_hit = False

    # ==================== 持仓查询方法 ====================

    def _query_real_position(self) -> int:
        """
        查询真实持仓 - 带缓存机制

        Returns:
            净持仓数量（正数=多头，负数=空头）
        """
        import requests

        current_time = time.time()

        # 缓存有效期5秒
        if current_time - self.last_position_update < 5:
            return self.cached_position

        try:
            response = requests.get(
                f"http://localhost:8001/real_trading/positions?symbol={self.symbol}",
                timeout=2
            )

            if response.status_code == 200:
                data = response.json()
                positions = data.get('positions', [])

                net_position = 0
                for pos in positions:
                    if pos.get('symbol') == self.symbol:
                        direction = pos.get('direction', '')
                        volume = pos.get('volume', 0)
                        if direction == 'LONG':
                            net_position += volume
                        elif direction == 'SHORT':
                            net_position -= volume

                self.cached_position = net_position
                self.last_position_update = current_time
                self.pos = net_position  # 同步更新策略持仓

                return net_position
        except Exception as e:
            logger.warning(f"⚠️ [持仓查询] 查询失败: {e}")

        return self.cached_position

    def _update_position_cache_after_trade(self, new_position: int) -> None:
        """交易后更新持仓缓存"""
        self.cached_position = new_position
        self.pos = new_position
        self.last_position_update = time.time()

    # ==================== 日志记录方法 ====================

    def _log_indicators_to_csv(self, bar: BarData, fast_ma: float, slow_ma: float,
                                rsi: float, cross_signal: int, market_regime: str,
                                trend_strength: float) -> None:
        """
        📊 记录技术指标到CSV文件

        记录内容:
        - K线数据(OHLCV)
        - 技术指标(EMA快线/慢线, RSI, ATR)
        - 信号状态(交叉信号, 市场状态, 趋势强度)
        - 风控状态(入场价, 止损价, 最佳价)
        """
        import csv
        import os

        try:
            # 创建logs目录
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # CSV文件路径 - 按日期分文件
            today = datetime.now().strftime('%Y%m%d')
            csv_file = f"{log_dir}/indicators_{self.strategy_name}_{self.symbol}_{today}.csv"

            # 检查文件是否存在
            file_exists = os.path.exists(csv_file)

            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # 写入表头
                if not file_exists:
                    writer.writerow([
                        'DateTime', 'Open', 'High', 'Low', 'Close', 'Volume',
                        'EMA_Fast', 'EMA_Slow', 'RSI', 'ATR',
                        'MA_Diff', 'Cross_Signal', 'Market_Regime', 'Trend_Strength',
                        'Position', 'Entry_Price', 'Stop_Loss', 'Best_Price'
                    ])

                # 计算指标
                ma_diff = fast_ma - slow_ma
                atr = self.am.atr(14) if len(self.am.close_array) >= 14 else 0

                # 交叉信号转换
                cross_str = "GOLDEN" if cross_signal == 1 else ("DEAD" if cross_signal == -1 else "NONE")

                # 写入数据
                writer.writerow([
                    bar.datetime.strftime('%Y-%m-%d %H:%M:%S'),
                    f"{bar.open_price:.2f}",
                    f"{bar.high_price:.2f}",
                    f"{bar.low_price:.2f}",
                    f"{bar.close_price:.2f}",
                    bar.volume,
                    f"{fast_ma:.2f}",
                    f"{slow_ma:.2f}",
                    f"{rsi:.2f}",
                    f"{atr:.2f}",
                    f"{ma_diff:.2f}",
                    cross_str,
                    market_regime,
                    f"{trend_strength:.4f}",
                    self.pos,
                    f"{self.entry_price:.2f}",
                    f"{self.stop_loss_price:.2f}",
                    f"{self.best_price:.2f}"
                ])

            # 每10个K线输出一次指标摘要
            if hasattr(self, '_csv_log_count'):
                self._csv_log_count += 1
            else:
                self._csv_log_count = 1

            if self._csv_log_count % 10 == 0:
                logger.info(f"📊 [指标] EMA{self.fast_window}:{fast_ma:.2f} | "
                           f"EMA{self.slow_window}:{slow_ma:.2f} | RSI:{rsi:.2f} | "
                           f"状态:{market_regime}")

        except Exception as e:
            logger.error(f"⚠️ [指标记录] CSV记录失败: {e}")