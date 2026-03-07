"""
均值回归策略 - 黄金期货震荡市交易策略

核心逻辑：
1. 布林带+RSI双重确认：价格触及布林带边界 + RSI超买超卖同时满足
2. N根K线确认：连续N根K线满足条件才触发信号，避免瞬间假信号
3. 带宽过滤：只在布林带带宽收窄（震荡市）时启用，趋势市不做均值回归
4. 止盈目标：布林带中轨（均值），而非固定百分比
5. 多空独立风控：独立止损止盈参数

适用场景：震荡行情，价格在布林带通道内来回波动
"""

import time
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from services.strategy_service.core.data_tools import ArrayManager
from utils.logger import get_logger

logger = get_logger(__name__)


class MeanReversionStrategy(ARBIGCtaTemplate):
    """
    均值回归策略

    信号逻辑：
    - 价格触及布林带下轨 + RSI超卖 → 连续N根K线确认 → 做多（目标：中轨）
    - 价格触及布林带上轨 + RSI超买 → 连续N根K线确认 → 做空（目标：中轨）
    - 布林带带宽过宽（趋势市）时不交易
    - 反向信号强制平仓
    """

    # ==================== 策略参数配置 ====================

    # 布林带参数
    bollinger_period = 20        # 布林带计算周期
    bollinger_std = 2.0          # 布林带标准差倍数

    # RSI参数
    rsi_period = 14              # RSI计算周期
    rsi_overbought = 75          # RSI超买阈值（均值回归用更极端的值）
    rsi_oversold = 25            # RSI超卖阈值（均值回归用更极端的值）

    # 均值回归确认参数
    reversion_confirm_bars = 2   # 确认所需K线数：连续2根K线满足条件
    max_bandwidth_pct = 0.03     # 最大带宽百分比：3%（超过此值认为是趋势市，不做回归）
    min_band_touch_pct = 0.001   # 最小触及阈值：价格需在布林带边界0.1%内

    # 风控参数
    stop_loss_pct = 0.006        # 默认止损 0.6%（均值回归止损应更紧）
    take_profit_pct = 0.02       # 默认止盈 2%（回归目标通常较小）
    use_middle_band_tp = True    # 是否使用布林带中轨作为止盈目标

    # ATR参数
    atr_period = 14              # ATR周期

    # 交易参数
    trade_volume = 1             # 基础交易手数
    max_position = 3             # 最大持仓

    def __init__(self, strategy_name: str, symbol: str, setting: dict, signal_sender=None, **kwargs):
        """初始化策略"""
        super().__init__(strategy_name, symbol, setting, signal_sender)

        # 从设置中获取参数
        self.bollinger_period = setting.get('bollinger_period', self.bollinger_period)
        self.bollinger_std = setting.get('bollinger_std', self.bollinger_std)
        self.rsi_period = setting.get('rsi_period', self.rsi_period)
        self.rsi_overbought = setting.get('rsi_overbought', self.rsi_overbought)
        self.rsi_oversold = setting.get('rsi_oversold', self.rsi_oversold)
        self.reversion_confirm_bars = setting.get('reversion_confirm_bars', self.reversion_confirm_bars)
        self.max_bandwidth_pct = setting.get('max_bandwidth_pct', self.max_bandwidth_pct)
        self.min_band_touch_pct = setting.get('min_band_touch_pct', self.min_band_touch_pct)
        self.use_middle_band_tp = setting.get('use_middle_band_tp', self.use_middle_band_tp)
        self.atr_period = setting.get('atr_period', self.atr_period)

        # 多空独立止损止盈
        self.long_stop_loss_pct = setting.get('long_stop_loss_pct', 0.006)
        self.long_take_profit_pct = setting.get('long_take_profit_pct', 0.02)
        self.short_stop_loss_pct = setting.get('short_stop_loss_pct', 0.006)
        self.short_take_profit_pct = setting.get('short_take_profit_pct', 0.02)

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

        # 均值回归确认状态
        self.pending_reversion_type = None       # "LONG" / "SHORT" / None
        self.pending_reversion_bar_count = 0     # 确认K线计数
        self.pending_reversion_rsi_sum = 0.0     # 确认期间RSI累加（取平均）
        self.pending_reversion_price = 0.0       # 首次触发时的价格

        # 指标缓存
        self.current_upper = 0.0
        self.current_middle = 0.0
        self.current_lower = 0.0
        self.current_rsi = 50.0
        self.current_atr = 0.0
        self.current_bandwidth = 0.0             # 布林带带宽百分比
        self.current_reversion_signal = "NONE"

        # 信号控制
        self.signal_lock = False
        self.cached_position = 0
        self.last_position_update = 0

        # 持仓持久化
        self._real_positions_file = f"data/real_positions_{self.strategy_name}_{self.symbol}.json"
        self._load_real_positions()

        logger.info(f"✅ {self.strategy_name} 初始化完成 | 品种:{self.symbol}")
        logger.info(f"   布林带:BB({self.bollinger_period},{self.bollinger_std}) | RSI({self.rsi_period}) 超买>{self.rsi_overbought} 超卖<{self.rsi_oversold}")
        logger.info(f"   回归确认:{self.reversion_confirm_bars}K线 | 最大带宽:{self.max_bandwidth_pct*100:.1f}% | 中轨止盈:{self.use_middle_band_tp}")
        logger.info(f"   风控-多单:止损{self.long_stop_loss_pct*100:.1f}%/止盈{self.long_take_profit_pct*100:.1f}%")
        logger.info(f"   风控-空单:止损{self.short_stop_loss_pct*100:.1f}%/止盈{self.short_take_profit_pct*100:.1f}%")


    def on_init(self):
        """策略初始化回调"""
        self.write_log("均值回归策略初始化")

    def on_start(self):
        """策略启动回调"""
        self.write_log("🚀 均值回归策略已启动")

    def on_stop(self):
        """策略停止回调"""
        self.write_log("⏹️ 均值回归策略已停止")
        self._save_real_positions()

    # ==================== 交易时间检查 ====================

    def _is_trading_time(self) -> bool:
        """检查当前是否在SHFE交易时间内"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        t = hour * 100 + minute

        # 日盘：09:00-10:15, 10:30-11:30, 13:30-15:00
        if 900 <= t <= 1015:
            return True
        if 1030 <= t <= 1130:
            return True
        if 1330 <= t <= 1500:
            return True

        # 夜盘：21:00-23:59, 00:00-02:30
        if 2100 <= t <= 2359:
            return True
        if 0 <= t <= 230:
            return True

        return False

    # ==================== 持仓持久化 ====================

    def _load_real_positions(self):
        """从文件加载真实开仓均价到父类属性"""
        try:
            os.makedirs("data", exist_ok=True)
            if os.path.exists(self._real_positions_file):
                with open(self._real_positions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if "long" in data:
                    self.long_pos = data["long"].get("volume", 0)
                    self.long_price = data["long"].get("avg_price", 0.0)
                    self.long_cost = data["long"].get("total_cost", 0.0)
                if "short" in data:
                    self.short_pos = data["short"].get("volume", 0)
                    self.short_price = data["short"].get("avg_price", 0.0)
                    self.short_cost = data["short"].get("total_cost", 0.0)
                self.pos = self.long_pos - self.short_pos
                logger.info(f"[均价] 加载: 多{self.long_pos}手@{self.long_price:.2f} 空{self.short_pos}手@{self.short_price:.2f}")
            else:
                logger.debug(f"[均价] 文件不存在，初始化为空")
        except Exception as e:
            logger.error(f"❌ [真实均价] 加载失败: {e}")

    def _save_real_positions(self):
        """保存父类的真实开仓均价到文件"""
        try:
            os.makedirs("data", exist_ok=True)
            data = {}
            if self.long_pos > 0:
                data["long"] = {
                    "volume": self.long_pos,
                    "avg_price": round(self.long_price, 4),
                    "total_cost": round(self.long_cost, 4),
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            if self.short_pos > 0:
                data["short"] = {
                    "volume": self.short_pos,
                    "avg_price": round(self.short_price, 4),
                    "total_cost": round(self.short_cost, 4),
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            with open(self._real_positions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"[均价] 已保存: 多{self.long_pos}@{self.long_price:.2f} 空{self.short_pos}@{self.short_price:.2f}")
        except Exception as e:
            logger.error(f"❌ [真实均价] 保存失败: {e}")


    # ==================== K线核心逻辑 ====================

    def on_bar_impl(self, bar: BarData):
        """K线数据处理 - 均值回归策略核心入口"""
        logger.debug(f"[K线] {bar.symbol} {bar.datetime} 价格:{bar.close_price:.2f}")

        if not self.trading:
            logger.warning(f"⚠️ 策略未启用交易")
            return

        self.am.update_bar(bar)

        if not self.am.inited:
            logger.debug(f"🔧 ArrayManager 初始化中 ({self.am.count}/20)")
            return

        # 计算指标（每根K线只算一次）
        self._calculate_indicators()

        # 检查风控（先于信号，保护已有持仓）
        risk_action = self._check_risk_control(bar.close_price)
        if risk_action:
            return

        # 检查交易时间
        if not self._is_trading_time():
            return

        # 生成交易信号
        signal, reason = self._generate_trading_signal(bar.close_price)

        if signal:
            self._process_trading_signal(signal, bar.close_price, reason)

    # ==================== 指标计算 ====================

    def _calculate_indicators(self):
        """计算所有技术指标（每根K线调用一次）"""
        # 布林带
        upper, middle, lower = self.am.boll(self.bollinger_period, self.bollinger_std)
        self.current_upper = upper
        self.current_middle = middle
        self.current_lower = lower

        # 布林带宽百分比 = (上轨 - 下轨) / 中轨
        if middle > 0:
            self.current_bandwidth = (upper - lower) / middle
        else:
            self.current_bandwidth = 0.0

        # RSI
        self.current_rsi = self.am.rsi(self.rsi_period)

        # ATR
        self.current_atr = self.am.atr(self.atr_period)

    # ==================== 信号生成 ====================

    def _generate_trading_signal(self, current_price: float) -> tuple:
        """
        均值回归信号生成：布林带触及 + RSI极端 + 带宽过滤 + N根K线确认

        Returns:
            (signal, reason): signal为"LONG"/"SHORT"/None
        """
        # 步骤1：带宽过滤 - 趋势市不做均值回归
        if self.current_bandwidth > self.max_bandwidth_pct:
            # 趋势市，取消任何待确认信号
            if self.pending_reversion_type:
                logger.info(f"📊 [带宽过滤] 带宽{self.current_bandwidth*100:.2f}% > {self.max_bandwidth_pct*100:.1f}%，取消{self.pending_reversion_type}待确认")
                self._reset_pending_reversion()
            return None, ""

        # 步骤2：检测新的回归信号
        new_signal = self._detect_reversion_signal(current_price)

        # 步骤3：N根K线确认逻辑
        if new_signal:
            if self.pending_reversion_type == new_signal:
                # 同方向信号持续，累加确认计数
                self.pending_reversion_bar_count += 1
                self.pending_reversion_rsi_sum += self.current_rsi
                logger.info(f"📊 [回归确认] {new_signal} 第{self.pending_reversion_bar_count}/{self.reversion_confirm_bars}根K线 "
                           f"RSI={self.current_rsi:.1f} 带宽={self.current_bandwidth*100:.2f}%")
            else:
                # 新方向或首次检测，重置并开始确认
                self.pending_reversion_type = new_signal
                self.pending_reversion_bar_count = 1
                self.pending_reversion_rsi_sum = self.current_rsi
                self.pending_reversion_price = current_price
                logger.info(f"📊 [回归检测] 检测到{new_signal}回归信号，开始确认 "
                           f"价格={current_price:.2f} RSI={self.current_rsi:.1f}")
        else:
            # 没有信号，重置
            if self.pending_reversion_type:
                logger.debug(f"📊 [回归取消] {self.pending_reversion_type} 条件不再满足，重置")
                self._reset_pending_reversion()
            return None, ""

        # 步骤4：确认完成 → 触发交易
        if self.pending_reversion_bar_count >= self.reversion_confirm_bars:
            confirmed_signal = self.pending_reversion_type
            avg_rsi = self.pending_reversion_rsi_sum / self.pending_reversion_bar_count
            entry_price = self.pending_reversion_price

            self._reset_pending_reversion()

            if confirmed_signal == "LONG":
                reason = (f"均值回归做多 | 价格{current_price:.2f}触及下轨{self.current_lower:.2f} "
                         f"RSI={avg_rsi:.1f}<{self.rsi_oversold} 带宽={self.current_bandwidth*100:.2f}% "
                         f"目标中轨{self.current_middle:.2f}")
                return "LONG", reason
            else:
                reason = (f"均值回归做空 | 价格{current_price:.2f}触及上轨{self.current_upper:.2f} "
                         f"RSI={avg_rsi:.1f}>{self.rsi_overbought} 带宽={self.current_bandwidth*100:.2f}% "
                         f"目标中轨{self.current_middle:.2f}")
                return "SHORT", reason

        return None, ""

    def _detect_reversion_signal(self, current_price: float) -> Optional[str]:
        """
        检测单根K线的回归信号条件

        条件（做多）：价格在下轨附近 + RSI超卖
        条件（做空）：价格在上轨附近 + RSI超买
        """
        if self.current_lower <= 0 or self.current_upper <= 0:
            return None

        # 做多：价格触及下轨 + RSI超卖
        lower_distance = (current_price - self.current_lower) / self.current_lower
        if lower_distance <= self.min_band_touch_pct and self.current_rsi < self.rsi_oversold:
            return "LONG"

        # 做空：价格触及上轨 + RSI超买
        upper_distance = (self.current_upper - current_price) / self.current_upper
        if upper_distance <= self.min_band_touch_pct and self.current_rsi > self.rsi_overbought:
            return "SHORT"

        return None

    def _reset_pending_reversion(self):
        """重置待确认回归状态"""
        self.pending_reversion_type = None
        self.pending_reversion_bar_count = 0
        self.pending_reversion_rsi_sum = 0.0
        self.pending_reversion_price = 0.0

    # ==================== 风控逻辑 ====================

    def _check_risk_control(self, current_price: float) -> bool:
        """
        检查风控：止损止盈 + 布林带中轨止盈

        注意：持仓更新由父类 on_trade() 统一处理，这里只发送平仓指令

        Returns:
            True 如果触发了风控动作（调用方应跳过信号生成）
        """
        triggered = False

        # 多仓风控
        if self.long_pos > 0 and self.long_price > 0:
            long_pnl_pct = (current_price - self.long_price) / self.long_price

            # 止损
            if long_pnl_pct <= -self.long_stop_loss_pct:
                logger.info(f"🛑 [多仓止损] 亏损{long_pnl_pct*100:.2f}% >= {self.long_stop_loss_pct*100:.1f}% | "
                           f"开仓价{self.long_price:.2f} 现价{current_price:.2f}")
                self._smart_close_position('LONG', self.long_pos, current_price)
                triggered = True

            # 中轨止盈（均值回归核心：回到均值就走）
            elif self.use_middle_band_tp and self.current_middle > 0:
                if current_price >= self.current_middle:
                    logger.info(f"🎯 [多仓中轨止盈] 价格{current_price:.2f} >= 中轨{self.current_middle:.2f} | "
                               f"盈利{long_pnl_pct*100:.2f}%")
                    self._smart_close_position('LONG', self.long_pos, current_price)
                    triggered = True

            # 固定止盈（备用）
            elif long_pnl_pct >= self.long_take_profit_pct:
                logger.info(f"✅ [多仓止盈] 盈利{long_pnl_pct*100:.2f}% >= {self.long_take_profit_pct*100:.1f}%")
                self._smart_close_position('LONG', self.long_pos, current_price)
                triggered = True

        # 空仓风控
        if self.short_pos > 0 and self.short_price > 0:
            short_pnl_pct = (self.short_price - current_price) / self.short_price

            # 止损
            if short_pnl_pct <= -self.short_stop_loss_pct:
                logger.info(f"🛑 [空仓止损] 亏损{short_pnl_pct*100:.2f}% >= {self.short_stop_loss_pct*100:.1f}% | "
                           f"开仓价{self.short_price:.2f} 现价{current_price:.2f}")
                self._smart_close_position('SHORT', self.short_pos, current_price)
                triggered = True

            # 中轨止盈
            elif self.use_middle_band_tp and self.current_middle > 0:
                if current_price <= self.current_middle:
                    logger.info(f"🎯 [空仓中轨止盈] 价格{current_price:.2f} <= 中轨{self.current_middle:.2f} | "
                               f"盈利{short_pnl_pct*100:.2f}%")
                    self._smart_close_position('SHORT', self.short_pos, current_price)
                    triggered = True

            # 固定止盈
            elif short_pnl_pct >= self.short_take_profit_pct:
                logger.info(f"✅ [空仓止盈] 盈利{short_pnl_pct*100:.2f}% >= {self.short_take_profit_pct*100:.1f}%")
                self._smart_close_position('SHORT', self.short_pos, current_price)
                triggered = True

        return triggered

    # ==================== 交易执行 ====================

    def _process_trading_signal(self, signal: str, price: float, reason: str):
        """
        处理交易信号 - 反向信号先平仓再开仓

        注意：持仓更新由父类 on_trade() 统一处理，这里不手动修改持仓变量

        Args:
            signal: "LONG" / "SHORT"
            price: 当前价格
            reason: 信号原因
        """
        volume = self._calculate_position_size()
        need_delay = False

        if signal == "LONG":
            # 有空仓 → 先平空
            if self.short_pos > 0:
                logger.info(f"🔄 [反向平仓] 做多信号，先平空仓{self.short_pos}手")
                self._smart_close_position('SHORT', self.short_pos, price)
                need_delay = True

            # 检查是否已有多仓
            if self.long_pos >= self.max_position:
                logger.info(f"⚠️ [仓位限制] 多仓已满 {self.long_pos}/{self.max_position}")
                return

            # 开多
            if need_delay:
                time.sleep(0.1)
            logger.info(f"📈 [开多] {volume}手 @ {price:.2f} | {reason}")
            self.buy(price, volume, stop=False)

        elif signal == "SHORT":
            # 有多仓 → 先平多
            if self.long_pos > 0:
                logger.info(f"🔄 [反向平仓] 做空信号，先平多仓{self.long_pos}手")
                self._smart_close_position('LONG', self.long_pos, price)
                need_delay = True

            # 检查是否已有空仓
            if self.short_pos >= self.max_position:
                logger.info(f"⚠️ [仓位限制] 空仓已满 {self.short_pos}/{self.max_position}")
                return

            # 开空
            if need_delay:
                time.sleep(0.1)
            logger.info(f"📉 [开空] {volume}手 @ {price:.2f} | {reason}")
            self.short(price, volume, stop=False)

    # ==================== 智能平仓 ====================

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
            logger.warning(f"⚠️ [智能平仓] 无可平仓位")
            return

        # 优先平昨仓，再平今仓
        close_yesterday = min(volume, yesterday_pos)
        close_today = volume - close_yesterday

        logger.info(f"📋 [智能平仓] {action_name}: 总{volume}手 = 昨{close_yesterday}手 + 今{close_today}手")

        if direction == 'LONG':
            if close_yesterday > 0:
                self.sell(price, close_yesterday, stop=False)
            if close_today > 0:
                self.sell(price, close_today, stop=False)
        else:
            if close_yesterday > 0:
                self.cover(price, close_yesterday, stop=False)
            if close_today > 0:
                self.cover(price, close_today, stop=False)

    def _query_real_position(self) -> Optional[dict]:
        """实时查询真实持仓 - 返回完整持仓信息（包含今昨仓）"""
        try:
            import requests

            url = f"http://localhost:8001/real_trading/positions?symbol={self.symbol}"
            response = requests.get(url, timeout=2.0)

            if response.status_code == 200:
                position_data = response.json()
                if position_data.get("success") and position_data.get("data"):
                    position_info = position_data["data"]
                    return {
                        "net_position": position_info.get("net_position", 0),
                        "long_position": position_info.get("long_position", 0),
                        "short_position": position_info.get("short_position", 0),
                        "long_price": position_info.get("long_price", 0),
                        "short_price": position_info.get("short_price", 0),
                        "current_price": position_info.get("current_price", 0),
                        "long_today": position_info.get("long_today", 0),
                        "long_yesterday": position_info.get("long_yesterday", 0),
                        "short_today": position_info.get("short_today", 0),
                        "short_yesterday": position_info.get("short_yesterday", 0)
                    }
                else:
                    logger.warning(f"⚠️ [持仓查询] 返回空数据")
                    return None
            else:
                logger.warning(f"⚠️ [持仓查询] 失败: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"⚠️ [持仓查询] 异常: {e}")
            return None

    def on_tick_impl(self, tick: TickData):
        """Tick数据处理实现 - 实时风控检查"""
        # 🛡️ 基于Tick的实时风控检查（止损止盈+中轨止盈）
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
    """创建MeanReversionStrategy策略实例"""
    return MeanReversionStrategy(strategy_name, symbol, setting, signal_sender, **kwargs)