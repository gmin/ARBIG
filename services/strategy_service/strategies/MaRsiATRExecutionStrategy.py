"""
MaRsiATRExecutionStrategy

基于 MA 交叉 + RSI 确认 + ATR 风控 的生产级策略（1m 驱动 + 5m 过滤）。

设计要点（简要）：
- 信号：EMA(fast/slow) 金叉/死叉 + RSI(14) 位于合理区间；
- 过滤：5m EMA 方向一致性过滤（有则用，无则放行）；
- 执行：限价 GFD，价格=当前价±offset_tick×tick_size；
- 风控：SL=1.5×ATR(14)，TP=3×ATR(14)；固定手数=1，最大持仓=3；
- 观察性：
  - K线日志：logs/bar_{SYMBOL}_1m_YYYYMMDD.log（空格分隔）
  - 指标日志：logs/indicators_MaRsiATRExecutionStrategy_{SYMBOL}_1m_YYYYMMDD.csv
  - 事件日志：logs/strategy/MaRsiATRExecutionStrategy_{SYMBOL}_YYYYMMDD.log（key=value）

仅修改策略目录内文件。非策略文件如需变更将先行征求确认。
"""

import os
import csv
import time
import math
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到路径（与现有策略保持一致）
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from services.strategy_service.core.data_tools import ArrayManager
from utils.logger import get_logger


logger = get_logger(__name__)


class MaRsiATRExecutionStrategy(ARBIGCtaTemplate):
    """MA+RSI+ATR 执行策略（1m 驱动 + 5m 过滤）"""

    # 策略参数（可由引擎注入）
    fast_ma: int = 10
    slow_ma: int = 30
    rsi_period: int = 14
    atr_period: int = 14

    fixed_qty: int = 1
    max_position: int = 3

    limit_offset_ticks: int = 1
    min_signal_interval_seconds: int = 2
    cooldown_seconds: int = 60

    # 注意：不同品种最小变动价位不同，建议外部明确设置
    tick_size: float = 0.02
    # 交叉强度阈值：以 ATR 比例度量，过滤微弱交叉
    min_cross_atr_ratio: float = 0.2  # 交叉强度至少达到 0.2*ATR
    # 最小有效 ATR（以 tick 为单位），过滤极低波动时段
    min_atr_in_ticks: float = 1.0

    # 参数声明供 UI/引擎查询
    parameters = [
        "fast_ma", "slow_ma", "rsi_period", "atr_period",
        "fixed_qty", "max_position", "limit_offset_ticks",
        "min_signal_interval_seconds", "cooldown_seconds", "tick_size",
        "min_cross_atr_ratio", "min_atr_in_ticks"
    ]

    def __init__(self, strategy_name: str, symbol: str, setting: Dict[str, Any], signal_sender=None, **kwargs):
        super().__init__(strategy_name, symbol, setting, signal_sender=signal_sender)

        # 应用外部配置
        for name in self.parameters:
            if name in setting:
                setattr(self, name, setting[name])

        # 1m 与 5m 指标管理器
        self.am_1m = ArrayManager(size=200)
        self.am_5m = ArrayManager(size=200)

        # 5m 聚合状态
        self._agg_5m = {
            "open": None, "high": None, "low": None, "close": None,
            "volume": 0, "start_dt": None, "count": 0
        }

        # 前一根 EMA 值（用于交叉确认）
        self.prev_ema_fast: float = 0.0
        self.prev_ema_slow: float = 0.0

        # 最近一次发单时间/信号时间
        self.last_signal_time: float = 0.0
        self.last_order_time: float = 0.0

        # 最近一次计算的 ATR，用于风控
        self.last_atr_1m: float = 0.0

        logger.info(f"✅ {self.strategy_name} 初始化完成 - {self.symbol}")

    # ==================== 生命周期 ====================
    def on_init(self) -> None:
        self._log_event("state", details={"from": "init", "to": "running", "reason": "init"})

    def on_start(self) -> None:
        self._log_event("state", details={"from": "stopped", "to": "running", "reason": "start"})

    def on_stop(self) -> None:
        self._log_event("state", details={"from": "running", "to": "stopped", "reason": "stop"})

    # ==================== Bar/Tick 处理 ====================
    def on_bar_impl(self, bar: BarData) -> None:
        # 更新 1m 指标
        self.am_1m.update_bar(bar)
        if not self.am_1m.inited:
            return

        # 更新 5m 聚合与指标
        self._aggregate_5m(bar)

        # 计算技术指标（1m）
        ema_fast = self.am_1m.ema(self.fast_ma)
        ema_slow = self.am_1m.ema(self.slow_ma)
        rsi_val = self.am_1m.rsi(self.rsi_period)
        atr_val = self.am_1m.atr(self.atr_period)
        self.last_atr_1m = atr_val or 0.0

        # 5m 过滤：若 5m 未就绪，放行；就绪则方向一致才放行
        filter_pass = True
        regime = "NA"
        ema_fast_5m = 0.0
        ema_slow_5m = 0.0
        if self.am_5m.inited:
            ema_fast_5m = self.am_5m.ema(self.fast_ma)
            ema_slow_5m = self.am_5m.ema(self.slow_ma)
            regime = "BULL" if ema_fast_5m > ema_slow_5m else ("BEAR" if ema_fast_5m < ema_slow_5m else "NEUTRAL")
            # 方向一致性过滤（先简化为放行，具体在决策时按方向校验）
            filter_pass = True

        # 写入日志（K线 + 指标）
        self._write_bar_log(bar)
        self._write_indicator_csv(
            ts=bar.datetime,
            close=bar.close_price,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            rsi14=rsi_val,
            atr14=atr_val,
            ema_diff=(ema_fast - ema_slow) if ema_slow else 0.0,
            cross_signal=self._cross_label(self.prev_ema_fast, self.prev_ema_slow, ema_fast, ema_slow),
            filter_pass=1 if filter_pass else 0,
            regime=regime
        )

        # 金叉/死叉判定（2点确认：上一根与当前根）
        cross = self._detect_cross(self.prev_ema_fast, self.prev_ema_slow, ema_fast, ema_slow)

        # 更新前值
        self.prev_ema_fast = ema_fast
        self.prev_ema_slow = ema_slow

        # 去抖与冷却
        now = time.time()
        if now - self.last_signal_time < self.min_signal_interval_seconds:
            self._log_event("skip", details={"reason": "min_interval", "interval": self.min_signal_interval_seconds})
            return
        if self.cooldown_seconds > 0 and (now - self.last_order_time < self.cooldown_seconds):
            self._log_event("skip", details={"reason": "cooldown", "cooldown": self.cooldown_seconds})
            return

        # 基于 RSI 的确认（避免极端）
        rsi_ok = 30 < rsi_val < 70

        # 方向一致性（若 5m 就绪）
        dir_ok_long = True
        dir_ok_short = True
        if self.am_5m.inited:
            dir_ok_long = ema_fast_5m >= ema_slow_5m
            dir_ok_short = ema_fast_5m <= ema_slow_5m

        # 交叉强度过滤（以 ATR 为尺度）
        cross_ok = self._cross_significant(ema_fast, ema_slow, self.last_atr_1m)

        action = "NONE"
        reason = ""
        if cross == 1 and rsi_ok and dir_ok_long and cross_ok:
            action = "BUY"
            reason = f"golden_cross+rsi({rsi_val:.1f})+5m_filter+cross_ok"
        elif cross == -1 and rsi_ok and dir_ok_short and cross_ok:
            action = "SELL"
            reason = f"death_cross+rsi({rsi_val:.1f})+5m_filter+cross_ok"
        else:
            self._log_event("skip", details={
                "reason": "filters_not_passed",
                "cross": cross,
                "rsi_ok": int(rsi_ok),
                "dir_ok_long": int(dir_ok_long),
                "dir_ok_short": int(dir_ok_short),
                "cross_ok": int(cross_ok)
            })
            return

        # 生成信号事件日志
        self._log_event(
            "signal",
            details={
                "action": action, "reason": reason,
                "price": f"{bar.close_price:.2f}",
                "ema_fast": f"{ema_fast:.2f}", "ema_slow": f"{ema_slow:.2f}",
                "rsi": f"{rsi_val:.1f}", "atr": f"{atr_val:.2f}",
            }
        )

        # 发单前：查询真实净持仓与入场均价
        pos_info = self._query_real_position()
        if not pos_info:
            self._log_event("risk_event", details={"type": "position_unavailable"})
            return
        real_pos = int(pos_info.get("net_position", 0) or 0)

        # 计算下单数量（开仓/平仓分流），同时做风控容量核验
        volume = self._calc_order_volume(action, real_pos)
        if volume <= 0:
            self._log_event("skip", details={"reason": "volume_zero", "action": action, "real_pos": real_pos})
            return

        # 计算委托价格（GFD 限价 ±1tick）
        px = bar.close_price
        offset = self.limit_offset_ticks * self.tick_size
        if action == "BUY":
            # BUY: 开多 or 平空
            if real_pos < 0:
                # 平空：买入平仓（COVER）
                price = self._round_price(px + offset, side="BUY")
                self._log_event("order_request", details={"action": "COVER", "volume": volume, "price": f"{price:.2f}", "tc": "GFD"})
                self.cover(price, volume, stop=False, time_condition="GFD")
            else:
                # 开多
                price = self._round_price(px + offset, side="BUY")
                self._log_event("order_request", details={"action": action, "volume": volume, "price": f"{price:.2f}", "tc": "GFD"})
                self.buy(price, volume, stop=False, time_condition="GFD")
        elif action == "SELL":
            # SELL: 平多 or 开空
            if real_pos > 0:
                # 平多
                price = self._round_price(px - offset, side="SELL")
                self._log_event("order_request", details={"action": action, "mode": "close_long", "volume": volume, "price": f"{price:.2f}", "tc": "GFD"})
                self.sell(price, volume, stop=False, time_condition="GFD")
            else:
                # 开空
                price = self._round_price(px - offset, side="SELL")
                self._log_event("order_request", details={"action": "SHORT", "volume": volume, "price": f"{price:.2f}", "tc": "GFD"})
                self.short(price, volume, stop=False, time_condition="GFD")

        self.last_signal_time = now
        self.last_order_time = now

    def on_tick_impl(self, tick: TickData) -> None:
        # 基于 1m ATR 的简单 SL/TP 风控（需要真实入场均价）
        if self.pos == 0 or self.last_atr_1m <= 0:
            return

        pos_info = self._query_real_position()
        if not pos_info:
            return

        entry_price = pos_info.get("average_price", 0) or 0
        if entry_price <= 0:
            return

        atr = self.last_atr_1m
        sl = 1.5 * atr
        tp = 3.0 * atr

        price = tick.last_price
        if self.pos > 0:
            if price <= entry_price - sl:
                self._log_event("risk_event", details={"type": "SL", "entry": f"{entry_price:.2f}", "current": f"{price:.2f}"})
                self.sell(price, abs(self.pos), stop=False, time_condition="GFD")
            elif price >= entry_price + tp:
                self._log_event("risk_event", details={"type": "TP", "entry": f"{entry_price:.2f}", "current": f"{price:.2f}"})
                self.sell(price, abs(self.pos), stop=False, time_condition="GFD")
        elif self.pos < 0:
            if price >= entry_price + sl:
                self._log_event("risk_event", details={"type": "SL", "entry": f"{entry_price:.2f}", "current": f"{price:.2f}"})
                self.cover(price, abs(self.pos), stop=False, time_condition="GFD")
            elif price <= entry_price - tp:
                self._log_event("risk_event", details={"type": "TP", "entry": f"{entry_price:.2f}", "current": f"{price:.2f}"})
                self.cover(price, abs(self.pos), stop=False, time_condition="GFD")

    # ==================== 内部方法 ====================
    def _detect_cross(self, prev_fast: float, prev_slow: float, cur_fast: float, cur_slow: float) -> int:
        """返回 1=金叉，-1=死叉，0=无"""
        if prev_fast == 0 or prev_slow == 0 or cur_fast == 0 or cur_slow == 0:
            return 0
        # 金叉：上一根 fast<=slow 且当前 fast>slow
        if prev_fast <= prev_slow and cur_fast > cur_slow:
            return 1
        # 死叉：上一根 fast>=slow 且当前 fast<slow
        if prev_fast >= prev_slow and cur_fast < cur_slow:
            return -1
        return 0

    def _cross_significant(self, ema_fast: float, ema_slow: float, atr: float) -> bool:
        """基于 ATR 比例过滤微弱交叉，避免噪声交易。"""
        if atr is None or atr <= 0:
            return False
        # ATR 不足（低波动）直接拒绝
        if atr < max(self.tick_size, 1e-9) * self.min_atr_in_ticks:
            return False
        strength = abs((ema_fast or 0) - (ema_slow or 0)) / max(atr, 1e-9)
        return strength >= self.min_cross_atr_ratio

    def _cross_label(self, prev_fast: float, prev_slow: float, cur_fast: float, cur_slow: float) -> str:
        c = self._detect_cross(prev_fast, prev_slow, cur_fast, cur_slow)
        return "GOLDEN_CROSS" if c == 1 else ("DEATH_CROSS" if c == -1 else "NONE")

    def _aggregate_5m(self, bar: BarData) -> None:
        """将 5 根 1m K 聚合为 5m K 并推进 am_5m。"""
        a = self._agg_5m
        if a["count"] == 0:
            a["open"] = bar.open_price
            a["high"] = bar.high_price
            a["low"] = bar.low_price
            a["close"] = bar.close_price
            a["volume"] = bar.volume
            a["start_dt"] = bar.datetime
            a["count"] = 1
            return

        # 更新当前 5m 聚合
        a["high"] = max(a["high"], bar.high_price)
        a["low"] = min(a["low"], bar.low_price)
        a["close"] = bar.close_price
        a["volume"] = (a["volume"] or 0) + (bar.volume or 0)
        a["count"] += 1

        # 满 5 根，推进到 am_5m
        if a["count"] >= 5:
            bar_5m = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=a["start_dt"],
                interval="5m",
                volume=a["volume"],
                open_price=a["open"],
                high_price=a["high"],
                low_price=a["low"],
                close_price=a["close"],
                open_interest=bar.open_interest,
                gateway_name=getattr(bar, 'gateway_name', 'CTP')
            )
            self.am_5m.update_bar(bar_5m)
            # 重置计数器
            a["open"] = None
            a["high"] = None
            a["low"] = None
            a["close"] = None
            a["volume"] = 0
            a["start_dt"] = None
            a["count"] = 0

    def _round_price(self, price: float, side: str) -> float:
        """按最小变动价位对齐价格。BUY 向上取整，SELL 向下取整。"""
        ts = max(self.tick_size, 1e-9)
        if side.upper() == "BUY":
            return round(math.ceil(price / ts) * ts, 10)
        else:
            return round(math.floor(price / ts) * ts, 10)

    def _calc_order_volume(self, action: str, real_pos: int) -> int:
        """根据当前净持仓与动作，计算下单数量并做上限控制。"""
        qty = int(max(1, self.fixed_qty))
        # 平仓优先使用不超过现有持仓的数量
        if action == 'BUY' and real_pos < 0:
            return min(qty, abs(real_pos))
        if action == 'SELL' and real_pos > 0:
            return min(qty, abs(real_pos))

        # 开仓：受 max_position 约束
        remaining = max(0, self.max_position - abs(real_pos))
        return min(qty, remaining)

    # ==================== 事件/日志 ====================
    def _bar_log_path(self, dt: datetime) -> str:
        date_str = dt.strftime('%Y%m%d')
        os.makedirs('logs', exist_ok=True)
        return os.path.join('logs', f"bar_{self.symbol}_1m_{date_str}.log")

    def _ind_csv_path(self, dt: datetime) -> str:
        date_str = dt.strftime('%Y%m%d')
        os.makedirs('logs', exist_ok=True)
        return os.path.join('logs', f"indicators_MaRsiATRExecutionStrategy_{self.symbol}_1m_{date_str}.csv")

    def _event_log_path(self, dt: datetime) -> str:
        date_str = dt.strftime('%Y%m%d')
        path = os.path.join('logs', 'strategy')
        os.makedirs(path, exist_ok=True)
        return os.path.join(path, f"MaRsiATRExecutionStrategy_{self.symbol}_{date_str}.log")

    def _write_bar_log(self, bar: BarData) -> None:
        try:
            line = f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} {bar.open_price:.2f} {bar.high_price:.2f} {bar.low_price:.2f} {bar.close_price:.2f} {bar.volume}"
            with open(self._bar_log_path(bar.datetime), 'a', encoding='utf-8') as f:
                f.write(line + "\n")
        except Exception as e:
            logger.error(f"K线日志写入失败: {e}")

    def _write_indicator_csv(self, ts: datetime, close: float, ema_fast: float, ema_slow: float,
                              rsi14: float, atr14: float, ema_diff: float,
                              cross_signal: str, filter_pass: int, regime: str) -> None:
        try:
            csv_file = self._ind_csv_path(ts)
            file_exists = os.path.exists(csv_file)
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        'ts', 'close', 'ema_fast', 'ema_slow', 'rsi14', 'atr14',
                        'ema_diff', 'cross_signal', 'filter_pass', 'regime'
                    ])
                writer.writerow([
                    ts.strftime('%Y-%m-%d %H:%M:%S'),
                    f"{close:.2f}", f"{ema_fast:.2f}", f"{ema_slow:.2f}", f"{rsi14:.2f}", f"{atr14:.2f}",
                    f"{ema_diff:.4f}", cross_signal, filter_pass, regime
                ])
        except Exception as e:
            logger.error(f"指标CSV写入失败: {e}")

    def _log_event(self, event: str, details: Optional[Dict[str, Any]] = None) -> None:
        try:
            ts = datetime.now()
            path = self._event_log_path(ts)
            parts = [f"[{event}]", f"ts={ts.strftime('%Y-%m-%d %H:%M:%S')}", f"strategy={self.strategy_name}", f"symbol={self.symbol}"]
            if details:
                for k, v in details.items():
                    parts.append(f"{k}={v}")
            line = " ".join(parts)
            with open(path, 'a', encoding='utf-8') as f:
                f.write(line + "\n")
        except Exception as e:
            logger.error(f"事件日志写入失败: {e}")

    # ==================== 交易前安全检查/查询 ====================
    def _pre_trade_safety_check(self, action: str) -> bool:
        info = self._query_real_position()
        if info is None:
            return False
        real_pos = info.get("net_position", 0)
        # 同步 pos
        if real_pos != self.pos:
            self.pos = real_pos
        # 开仓检查
        if action == 'BUY' and real_pos >= 0:
            return abs(real_pos) + self.fixed_qty <= self.max_position
        if action == 'SELL' and real_pos <= 0:
            return abs(real_pos) + self.fixed_qty <= self.max_position
        # 平仓允许
        return True

    def _query_real_position(self) -> Optional[dict]:
        """查询交易服务持仓（与现有策略保持一致的接口语义）。"""
        try:
            import requests
            url = f"http://localhost:8001/real_trading/positions?symbol={self.symbol}"
            resp = requests.get(url, timeout=2.0)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data.get("success"):
                return None
            return data.get("data")
        except Exception:
            return None


# 工厂与模板
def create_strategy(strategy_engine, strategy_name: str, symbol: str, setting: dict) -> MaRsiATRExecutionStrategy:
    default_setting = {
        "fast_ma": 10,
        "slow_ma": 30,
        "rsi_period": 14,
        "atr_period": 14,
        "fixed_qty": 1,
        "max_position": 3,
        "limit_offset_ticks": 1,
        "min_signal_interval_seconds": 2,
        "cooldown_seconds": 60,
        "tick_size": 0.02,
        "min_cross_atr_ratio": 0.2,
        "min_atr_in_ticks": 1.0
    }
    merged = {**default_setting, **(setting or {})}
    return MaRsiATRExecutionStrategy(strategy_name, symbol, merged, signal_sender=merged.get('signal_sender'))


STRATEGY_TEMPLATE = {
    "class_name": "MaRsiATRExecutionStrategy",
    "file_name": "MaRsiATRExecutionStrategy.py",
    "description": "MA+RSI+ATR 执行策略（1m驱动+5m过滤，GFD限价，ATR风控）",
    "parameters": {
        "fast_ma": {"type": "int", "default": 10, "description": "快线周期"},
        "slow_ma": {"type": "int", "default": 30, "description": "慢线周期"},
        "rsi_period": {"type": "int", "default": 14, "description": "RSI周期"},
        "atr_period": {"type": "int", "default": 14, "description": "ATR周期"},
        "fixed_qty": {"type": "int", "default": 1, "description": "每次交易手数"},
        "max_position": {"type": "int", "default": 3, "description": "最大持仓手数"},
        "limit_offset_ticks": {"type": "int", "default": 1, "description": "限价偏移tick"},
        "min_signal_interval_seconds": {"type": "int", "default": 2, "description": "最小信号间隔秒"},
        "cooldown_seconds": {"type": "int", "default": 60, "description": "冷却秒"},
        "tick_size": {"type": "float", "default": 0.02, "description": "最小变动价位"},
        "min_cross_atr_ratio": {"type": "float", "default": 0.2, "description": "交叉强度最低ATR比例"},
        "min_atr_in_ticks": {"type": "float", "default": 1.0, "description": "最小ATR(以tick计)"}
    }
}
