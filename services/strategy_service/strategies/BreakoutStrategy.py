"""
布林带突破策略 - 黄金期货突破交易策略

核心逻辑：
1. 布林带突破检测 + N根K线回踩确认
2. RSI过滤：避免追高杀低（上突破时RSI不能超买，下突破时RSI不能超卖）
3. 突破幅度确认：突破强度需超过最小阈值
4. 多空独立风控：独立止损止盈参数

适用场景：趋势启动阶段，价格突破重要通道边界
"""

import time
import json
import os
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from vnpy.trader.object import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from services.strategy_service.core.data_tools import ArrayManager
from utils.logger import get_logger

logger = get_logger(__name__)


class BreakoutStrategy(ARBIGCtaTemplate):
    """
    布林带突破策略

    信号逻辑：
    - 价格突破布林带上轨 → 等待N根K线回踩确认 → 做多
    - 价格突破布林带下轨 → 等待N根K线回踩确认 → 做空
    - RSI过滤：上突破时RSI<70，下突破时RSI>30
    - 反向信号强制平仓（类似MaRsiComboStrategy）
    """

    # ==================== 策略参数配置 ====================

    # 布林带参数
    bollinger_period = 20        # 布林带计算周期
    bollinger_std = 2.0          # 布林带标准差倍数

    # RSI参数
    rsi_period = 14              # RSI计算周期
    rsi_overbought = 70          # RSI超买阈值（上突破时RSI需低于此值）
    rsi_oversold = 30            # RSI超卖阈值（下突破时RSI需高于此值）

    # 突破确认参数
    breakout_confirm_bars = 2    # 突破确认所需K线数
    min_breakout_strength = 0.002  # 最小突破强度（0.2%）
    pullback_tolerance = 0.5     # 回踩容忍度：回踩不超过突破幅度的50%视为有效

    # 风控参数
    stop_loss_pct = 0.008        # 默认止损 0.8%
    take_profit_pct = 0.05       # 默认止盈 5%

    # 交易参数
    trade_volume = 1             # 基础交易手数
    max_position = 3             # 最大持仓

    # ATR参数
    atr_period = 14              # ATR周期

    def __init__(self, strategy_name: str, symbol: str, setting: dict, signal_sender=None, **kwargs):
        """初始化策略"""
        super().__init__(strategy_name, symbol, setting, signal_sender)

        # 从设置中获取参数
        self.bollinger_period = setting.get('bollinger_period', self.bollinger_period)
        self.bollinger_std = setting.get('bollinger_std', self.bollinger_std)
        self.rsi_period = setting.get('rsi_period', self.rsi_period)
        self.rsi_overbought = setting.get('rsi_overbought', self.rsi_overbought)
        self.rsi_oversold = setting.get('rsi_oversold', self.rsi_oversold)
        self.breakout_confirm_bars = setting.get('breakout_confirm_bars', self.breakout_confirm_bars)
        self.min_breakout_strength = setting.get('min_breakout_strength', self.min_breakout_strength)
        self.pullback_tolerance = setting.get('pullback_tolerance', self.pullback_tolerance)
        self.atr_period = setting.get('atr_period', self.atr_period)

        # 多空独立止损止盈
        self.long_stop_loss_pct = setting.get('long_stop_loss_pct', 0.008)
        self.long_take_profit_pct = setting.get('long_take_profit_pct', 0.05)
        self.short_stop_loss_pct = setting.get('short_stop_loss_pct', 0.008)
        self.short_take_profit_pct = setting.get('short_take_profit_pct', 0.05)

        # 兼容旧参数
        if 'stop_loss_pct' in setting and 'long_stop_loss_pct' not in setting:
            self.long_stop_loss_pct = setting['stop_loss_pct']
            self.short_stop_loss_pct = setting['stop_loss_pct']
        if 'take_profit_pct' in setting and 'long_take_profit_pct' not in setting:
            self.long_take_profit_pct = setting['take_profit_pct']
            self.short_take_profit_pct = setting['take_profit_pct']

        self.trade_volume = setting.get('trade_volume', self.trade_volume)
        self.max_position = setting.get('max_position', self.max_position)

        # 初始化ArrayManager
        self.am = ArrayManager(size=max(self.bollinger_period * 3, 100))

        # 突破确认状态
        self.pending_breakout_type = None      # "UP" / "DOWN" / None
        self.pending_breakout_bar_count = 0    # 确认K线计数
        self.pending_breakout_price = 0.0      # 突破时的价格
        self.pending_breakout_band = 0.0       # 突破时的布林带边界值
        self.pending_breakout_strength = 0.0   # 突破强度
        self.pending_breakout_extreme = 0.0    # 确认期间的极值

        # 指标缓存
        self.current_upper = 0.0
        self.current_middle = 0.0
        self.current_lower = 0.0
        self.current_rsi = 50.0
        self.current_atr = 0.0
        self.current_breakout_signal = "NONE"
        self.confirmed_breakout_strength = 0.0  # 🔧 确认后的突破强度（避免reset清零）

        # 信号控制
        self.signal_lock = False
        self.cached_position = 0
        self.last_position_update = 0

        self._load_real_positions()

        logger.info(f"✅ {self.strategy_name} 初始化完成 | 品种:{self.symbol}")
        logger.info(f"   布林带:BB({self.bollinger_period},{self.bollinger_std}) | RSI({self.rsi_period})")
        logger.info(f"   突破确认:{self.breakout_confirm_bars}K线 | 最小强度:{self.min_breakout_strength*100:.1f}%")
        logger.info(f"   风控-多单:止损{self.long_stop_loss_pct*100:.1f}%/止盈{self.long_take_profit_pct*100:.1f}%")
        logger.info(f"   风控-空单:止损{self.short_stop_loss_pct*100:.1f}%/止盈{self.short_take_profit_pct*100:.1f}%")



    def on_init(self):
        """策略初始化回调"""
        self.write_log("布林带突破策略初始化")

    def on_start(self):
        """策略启动回调"""
        self.write_log("🚀 布林带突破策略已启动")

    def on_stop(self):
        """策略停止回调"""
        self.write_log("⏹️ 布林带突破策略已停止")
        self._save_real_positions()

    # ==================== 交易时间检查 ====================

    # _is_trading_time, _load/_save_real_positions 已移至基类 ARBIGCtaTemplate

    # ==================== 核心交易逻辑 ====================

    def on_bar_impl(self, bar: BarData):
        """K线数据处理 - 突破策略核心入口"""
        logger.debug(f"[K线] {bar.symbol} {bar.datetime} 价格:{bar.close_price:.2f}")

        if not self.trading:
            logger.warning(f"⚠️ 策略未启用交易")
            return

        # 更新ArrayManager
        self.am.update_bar(bar)

        if not self.am.inited:
            logger.debug(f"🔧 ArrayManager 初始化中 ({self.am.count}/{self.bollinger_period * 3})")
            return

        # 计算指标（每根K线只算一次）
        self._calculate_indicators()

        # 检测突破信号（含N根K线确认）
        self._detect_breakout(bar)

        # 风控检查
        self._check_risk_control(bar.close_price)

        # 生成交易信号
        self._generate_trading_signal(bar)

    def _calculate_indicators(self):
        """计算技术指标"""
        # 布林带（使用ArrayManager.boll统一计算，中轨为EMA）
        self.current_upper, self.current_middle, self.current_lower = self.am.boll(self.bollinger_period, self.bollinger_std)

        # RSI
        self.current_rsi = self.am.rsi(self.rsi_period)

        # ATR
        self.current_atr = self.am.atr(self.atr_period)

        logger.debug(f"📊 [指标] BB上:{self.current_upper:.2f} 中:{self.current_middle:.2f} 下:{self.current_lower:.2f} | RSI:{self.current_rsi:.1f} | ATR:{self.current_atr:.2f}")

    def _detect_breakout(self, bar: BarData):
        """检测布林带突破 + N根K线确认机制

        逻辑：
        1. 价格突破布林带上/下轨 → 记录为待确认突破
        2. 等待 breakout_confirm_bars 根K线
        3. 确认期间：价格回踩不超过 pullback_tolerance → 确认有效
        4. 确认成功 → 设置 current_breakout_signal
        """
        close = bar.close_price
        high = bar.high_price
        low = bar.low_price

        # 重置信号
        self.current_breakout_signal = "NONE"

        # --- 状态机：处理待确认的突破 ---
        if self.pending_breakout_type is not None:
            self.pending_breakout_bar_count += 1

            if self.pending_breakout_type == "UP":
                # 上突破确认：跟踪最高价
                self.pending_breakout_extreme = max(self.pending_breakout_extreme, high)
                # 回踩检查：收盘价不应跌回布林带内太多
                pullback = (self.pending_breakout_band - close) / self.pending_breakout_band if close < self.pending_breakout_band else 0
                breakthrough_held = pullback <= self.pullback_tolerance * self.min_breakout_strength

                if self.pending_breakout_bar_count >= self.breakout_confirm_bars:
                    if breakthrough_held:
                        self.current_breakout_signal = "BREAKOUT_UP"
                        # 🔧 保存强度到confirmed变量，因为reset会清零
                        self.confirmed_breakout_strength = self.pending_breakout_strength
                        logger.info(f"✅ [突破确认] 上突破确认! {self.pending_breakout_bar_count}根K线 | "
                                    f"突破价:{self.pending_breakout_price:.2f} 上轨:{self.pending_breakout_band:.2f} "
                                    f"强度:{self.pending_breakout_strength*100:.2f}%")
                    else:
                        logger.info(f"❌ [假突破] 上突破回踩过深，取消 | 回踩:{pullback*100:.2f}%")
                    self._reset_pending_breakout()

            elif self.pending_breakout_type == "DOWN":
                # 下突破确认：跟踪最低价
                self.pending_breakout_extreme = min(self.pending_breakout_extreme, low)
                # 回踩检查：收盘价不应反弹回布林带内太多
                pullback = (close - self.pending_breakout_band) / self.pending_breakout_band if close > self.pending_breakout_band else 0
                breakthrough_held = pullback <= self.pullback_tolerance * self.min_breakout_strength

                if self.pending_breakout_bar_count >= self.breakout_confirm_bars:
                    if breakthrough_held:
                        self.current_breakout_signal = "BREAKOUT_DOWN"
                        # 🔧 保存强度到confirmed变量，因为reset会清零
                        self.confirmed_breakout_strength = self.pending_breakout_strength
                        logger.info(f"✅ [突破确认] 下突破确认! {self.pending_breakout_bar_count}根K线 | "
                                    f"突破价:{self.pending_breakout_price:.2f} 下轨:{self.pending_breakout_band:.2f} "
                                    f"强度:{self.pending_breakout_strength*100:.2f}%")
                    else:
                        logger.info(f"❌ [假突破] 下突破回踩过深，取消 | 回踩:{pullback*100:.2f}%")
                    self._reset_pending_breakout()

            return  # 确认期间不检测新突破

        # --- 检测新突破 ---
        # 上突破：收盘价突破布林带上轨
        if close > self.current_upper and self.current_upper > 0:
            strength = (close - self.current_upper) / self.current_upper
            if strength >= self.min_breakout_strength:
                self.pending_breakout_type = "UP"
                self.pending_breakout_bar_count = 0
                self.pending_breakout_price = close
                self.pending_breakout_band = self.current_upper
                self.pending_breakout_strength = strength
                self.pending_breakout_extreme = high
                logger.info(f"🔔 [突破检测] 上突破! 收盘:{close:.2f} > 上轨:{self.current_upper:.2f} | 强度:{strength*100:.2f}% | 等待{self.breakout_confirm_bars}根K线确认")

        # 下突破：收盘价突破布林带下轨
        elif close < self.current_lower and self.current_lower > 0:
            strength = (self.current_lower - close) / self.current_lower
            if strength >= self.min_breakout_strength:
                self.pending_breakout_type = "DOWN"
                self.pending_breakout_bar_count = 0
                self.pending_breakout_price = close
                self.pending_breakout_band = self.current_lower
                self.pending_breakout_strength = strength
                self.pending_breakout_extreme = low
                logger.info(f"🔔 [突破检测] 下突破! 收盘:{close:.2f} < 下轨:{self.current_lower:.2f} | 强度:{strength*100:.2f}% | 等待{self.breakout_confirm_bars}根K线确认")

    def _reset_pending_breakout(self):
        """重置待确认突破状态"""
        self.pending_breakout_type = None
        self.pending_breakout_bar_count = 0
        self.pending_breakout_price = 0.0
        self.pending_breakout_band = 0.0
        self.pending_breakout_strength = 0.0
        self.pending_breakout_extreme = 0.0

    # ==================== 信号生成 ====================

    def _generate_trading_signal(self, bar: BarData):
        """生成交易信号 - 基于确认的突破信号 + RSI过滤"""
        if self.signal_lock:
            logger.debug(f"🔒 信号生成锁定中")
            return

        signal = self.current_breakout_signal
        rsi = self.current_rsi
        price = bar.close_price

        if signal == "BREAKOUT_UP":
            # 上突破做多 — RSI不能超买（避免追高）
            if rsi < self.rsi_overbought:
                decision = {
                    "action": "BUY",
                    "reason": f"布林带上突破确认+RSI({rsi:.1f})<{self.rsi_overbought}",
                    "strength": min(self.confirmed_breakout_strength * 100, 1.0) if self.confirmed_breakout_strength > 0 else 1.0
                }
                logger.info(f"🎯 [信号] BUY - {decision['reason']}")
                self._process_trading_signal(decision, price)
            else:
                logger.info(f"⚠️ [过滤] 上突破但RSI超买({rsi:.1f}>={self.rsi_overbought})，放弃")

        elif signal == "BREAKOUT_DOWN":
            # 下突破做空 — RSI不能超卖（避免杀低）
            if rsi > self.rsi_oversold:
                decision = {
                    "action": "SELL",
                    "reason": f"布林带下突破确认+RSI({rsi:.1f})>{self.rsi_oversold}",
                    "strength": min(self.confirmed_breakout_strength * 100, 1.0) if self.confirmed_breakout_strength > 0 else 1.0
                }
                logger.info(f"🎯 [信号] SELL - {decision['reason']}")
                self._process_trading_signal(decision, price)
            else:
                logger.info(f"⚠️ [过滤] 下突破但RSI超卖({rsi:.1f}<={self.rsi_oversold})，放弃")

    # ==================== 风控检查 ====================

    def _check_risk_control(self, current_price: float):
        """检查风险控制 - 多空独立止损止盈"""
        try:
            # 检查多单
            if self.long_pos > 0 and self.long_price > 0:
                long_pnl_pct = (current_price - self.long_price) / self.long_price
                logger.info(f"🛡️ [风控-多单] {self.long_pos}手@{self.long_price:.2f} 现价={current_price:.2f} "
                            f"盈亏={long_pnl_pct*100:.2f}% 止损线={-self.long_stop_loss_pct*100:.1f}% 止盈线={self.long_take_profit_pct*100:.1f}%")

                if long_pnl_pct <= -self.long_stop_loss_pct + 1e-6:
                    logger.info(f"🛑 [风控] 多单触发止损! pnl={long_pnl_pct*100:.2f}%")
                    self._close_position_by_direction('LONG', self.long_pos, current_price, self.long_price, "多单止损")
                elif long_pnl_pct >= self.long_take_profit_pct - 1e-6:
                    logger.info(f"🎯 [风控] 多单触发止盈! pnl={long_pnl_pct*100:.2f}%")
                    self._close_position_by_direction('LONG', self.long_pos, current_price, self.long_price, "多单止盈")

            # 检查空单
            if self.short_pos > 0 and self.short_price > 0:
                short_pnl_pct = (self.short_price - current_price) / self.short_price
                logger.info(f"🛡️ [风控-空单] {self.short_pos}手@{self.short_price:.2f} 现价={current_price:.2f} "
                            f"盈亏={short_pnl_pct*100:.2f}% 止损线={-self.short_stop_loss_pct*100:.1f}% 止盈线={self.short_take_profit_pct*100:.1f}%")

                if short_pnl_pct <= -self.short_stop_loss_pct + 1e-6:
                    logger.info(f"🛑 [风控] 空单触发止损! pnl={short_pnl_pct*100:.2f}%")
                    self._close_position_by_direction('SHORT', self.short_pos, current_price, self.short_price, "空单止损")
                elif short_pnl_pct >= self.short_take_profit_pct - 1e-6:
                    logger.info(f"🎯 [风控] 空单触发止盈! pnl={short_pnl_pct*100:.2f}%")
                    self._close_position_by_direction('SHORT', self.short_pos, current_price, self.short_price, "空单止盈")

        except Exception as e:
            logger.error(f"❌ [风控] 异常: {e}")

    # ==================== 交易执行 ====================

    def _process_trading_signal(self, signal_decision: dict, current_price: float):
        """信号处理模块 - 反向平仓 + 开仓"""
        action = signal_decision['action']

        logger.info(f"🔧 [持仓管理] {action}信号 | 价格:{current_price:.2f}")

        long_position = self.long_pos
        short_position = self.short_pos
        long_price = self.long_price
        short_price = self.short_price

        logger.info(f"🔍 [持仓] 多:{long_position}手@{long_price:.2f} 空:{short_position}手@{short_price:.2f} | 决策:{action}")

        trade_volume = self._calculate_position_size(signal_decision.get('strength', 1.0))
        need_delay = False

        # 上突破信号：平空 → 开多
        if action == 'BUY':
            # 1. 平掉所有空单（反向信号强制平仓）
            if short_position > 0:
                short_pnl = (short_price - current_price) * short_position
                logger.info(f"🔄 [平仓] 上突破平空 {short_position}手 盈亏={short_pnl:.2f}元")
                self._smart_close_position('SHORT', short_position, current_price)
                need_delay = True

            # 2. 开多仓
            if long_position >= self.max_position:
                logger.warning(f"⚠️ [持仓管理] 多头已达上限{long_position}/{self.max_position}手")
            else:
                if need_delay:
                    time.sleep(0.1)
                if long_position == 0:
                    logger.info(f"🚀 [开仓] 上突破开多{trade_volume}手")
                else:
                    logger.info(f"🚀 [加仓] 上突破加多{trade_volume}手 (现有{long_position}手)")
                self.buy(current_price, trade_volume, stop=False)

        # 下突破信号：平多 → 开空
        elif action == 'SELL':
            # 1. 平掉所有多单
            if long_position > 0:
                long_pnl = (current_price - long_price) * long_position
                logger.info(f"🔄 [平仓] 下突破平多 {long_position}手 盈亏={long_pnl:.2f}元")
                self._smart_close_position('LONG', long_position, current_price)
                need_delay = True

            # 2. 开空仓
            if short_position >= self.max_position:
                logger.warning(f"⚠️ [持仓管理] 空头已达上限{short_position}/{self.max_position}手")
            else:
                if need_delay:
                    time.sleep(0.1)
                if short_position == 0:
                    logger.info(f"🚀 [开仓] 下突破开空{trade_volume}手")
                else:
                    logger.info(f"🚀 [加仓] 下突破加空{trade_volume}手 (现有{short_position}手)")
                self.short(current_price, trade_volume, stop=False)

        # 更新持仓缓存
        old_cache = self.cached_position
        self.cached_position = self.pos
        self.last_position_update = time.time()
        logger.debug(f"[缓存更新] {old_cache} → {self.pos}")

    def _close_position_by_direction(self, direction: str, volume: int, price: float, entry_price: float, reason: str):
        """平掉指定方向的持仓"""
        if volume <= 0:
            return

        if direction == 'LONG':
            pnl_amount = (price - entry_price) * volume
            pnl_pct = (price - entry_price) / entry_price
        else:
            pnl_amount = (entry_price - price) * volume
            pnl_pct = (entry_price - price) / entry_price

        logger.info(f"🛑 [风控触发] {reason} | {direction} {volume}手 | 入场:{entry_price:.2f} → 平仓:{price:.2f} | 盈亏:{pnl_amount:+.2f}元({pnl_pct*100:+.2f}%)")
        self._smart_close_position(direction, volume, price)
        self.write_log(f"🛑 {reason}: 平{direction} {volume}手 @ {price:.2f}, 盈亏{pnl_pct*100:+.2f}%")

    def _smart_close_position(self, direction: str, volume: int, price: float):
        """智能平仓 - 自动拆分今昨仓订单"""
        if volume <= 0:
            logger.warning(f"⚠️ [智能平仓] 平仓数量无效: {volume}")
            return

        position_info = self._query_real_position()
        if not position_info:
            logger.warning(f"⚠️ [智能平仓] 无法获取持仓信息，使用普通平仓")
            if direction == 'LONG':
                self.sell(price, volume, stop=False)
            else:
                self.cover(price, volume, stop=False)
            return

        if direction == 'LONG':
            today_pos = position_info.get("long_today", 0)
            yesterday_pos = position_info.get("long_yesterday", 0)
            action_name = "平多"
        else:
            today_pos = position_info.get("short_today", 0)
            yesterday_pos = position_info.get("short_yesterday", 0)
            action_name = "平空"

        total_pos = today_pos + yesterday_pos
        if volume > total_pos:
            logger.warning(f"⚠️ [智能平仓] {action_name}数量{volume}超过持仓{total_pos}，调整为{total_pos}")
            volume = total_pos

        if volume <= 0:
            logger.warning(f"⚠️ [智能平仓] 调整后数量为0，取消平仓")
            return

        logger.info(f"🔍 [智能平仓] {action_name}{volume}手: 今仓{today_pos}手, 昨仓{yesterday_pos}手")

        if today_pos > 0 and yesterday_pos > 0 and volume > yesterday_pos:
            yesterday_volume = min(volume, yesterday_pos)
            today_volume = volume - yesterday_volume
            logger.info(f"📋 [平仓] 拆分: 昨仓{yesterday_volume}手 + 今仓{today_volume}手")
            if yesterday_volume > 0:
                if direction == 'LONG':
                    self.sell(price, yesterday_volume, stop=False)
                else:
                    self.cover(price, yesterday_volume, stop=False)
                time.sleep(0.1)
            if today_volume > 0:
                if direction == 'LONG':
                    self.sell(price, today_volume, stop=False)
                else:
                    self.cover(price, today_volume, stop=False)
        else:
            if direction == 'LONG':
                self.sell(price, volume, stop=False)
            else:
                self.cover(price, volume, stop=False)

    def _query_real_position(self) -> Optional[dict]:
        """通过 signal_sender 查询真实持仓（包含今昨仓）"""
        try:
            position_data = self.signal_sender.get_positions()
            if position_data.get("success") and position_data.get("data"):
                info = position_data["data"]
                net_position = info.get("net_position", 0)
                self.cached_position = net_position
                return {
                    "net_position": net_position,
                    "long_position": info.get("long_position", 0),
                    "short_position": info.get("short_position", 0),
                    "long_price": info.get("long_price", 0),
                    "short_price": info.get("short_price", 0),
                    "current_price": info.get("current_price", 0),
                    "long_today": info.get("long_today", 0),
                    "long_yesterday": info.get("long_yesterday", 0),
                    "short_today": info.get("short_today", 0),
                    "short_yesterday": info.get("short_yesterday", 0),
                }
            else:
                logger.warning("⚠️ [持仓查询] 返回空数据")
                return None
        except Exception as e:
            logger.warning(f"⚠️ [持仓查询] 异常: {e}")
            return None

    def on_tick_impl(self, tick: TickData):
        """Tick数据处理实现 - 实时风控检查"""
        # 🛡️ 基于Tick的实时风控检查（止损止盈）
        if self.long_pos > 0 or self.short_pos > 0:
            self._check_risk_control(tick.last_price)

    def on_trade_impl(self, trade):
        """成交处理实现 - 持久化持仓数据

        注意：均价计算已在父类 on_trade() 中完成
        这里只需要：1. 记录日志 2. 持久化到文件 3. 更新缓存
        """
        logger.info(f"💰 [成交] {trade.direction.value} {trade.offset} {trade.volume}手 @ {trade.price:.2f} | 持仓→{self.pos}手")

        # 持久化均价到文件（均价已由父类计算并更新到 self.long_price/short_price）
        self._save_real_positions()

        # 更新持仓缓存
        old_cache = self.cached_position
        self.cached_position = self.pos
        self.last_position_update = time.time()
        logger.debug(f"[缓存更新] {old_cache} → {self.pos}")

    def _calculate_position_size(self, signal_strength: float = 1.0) -> int:
        """计算交易数量"""
        base_volume = self.trade_volume
        adjusted_volume = int(base_volume * signal_strength)
        return max(1, adjusted_volume)


# 策略工厂函数
def create_strategy(strategy_name: str, symbol: str, setting: dict, signal_sender=None, **kwargs):
    """创建BreakoutStrategy策略实例"""
    return BreakoutStrategy(strategy_name, symbol, setting, signal_sender, **kwargs)