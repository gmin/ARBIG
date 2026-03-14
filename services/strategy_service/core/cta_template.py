"""
ARBIG CTA策略模板
基于vnpy CtaTemplate设计，适配ARBIG微服务架构
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import json
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from vnpy.trader.object import TickData, BarData, OrderData, TradeData
from vnpy.trader.constant import Direction
from .signal_sender import SignalData
from utils.logger import get_logger

logger = get_logger(__name__)

class StrategyStatus(Enum):
    """策略状态"""
    INIT = "init"           # 初始化
    RUNNING = "running"     # 运行中
    PAUSED = "paused"       # 已暂停（Trading Service 断连时自动触发，保留策略状态）
    STOPPED = "stopped"     # 已停止
    ERROR = "error"         # 错误状态

class ARBIGCtaTemplate(ABC):
    """
    ARBIG CTA策略模板
    
    基于vnpy CtaTemplate设计理念，提供标准化的策略开发接口
    同时适配ARBIG的微服务架构，通过事件机制与交易服务通信
    """
    
    # 策略参数（子类可重写）
    parameters = []
    variables = []
    
    def __init__(
        self,
        strategy_name: str,
        symbol: str,
        setting: Dict[str, Any],
        signal_sender  # 信号发送器，用于向交易服务发送信号
    ):
        """
        初始化策略
        
        Args:
            strategy_name: 策略名称
            symbol: 交易合约
            setting: 策略参数设置
            signal_sender: 信号发送器
        """
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.setting = setting.copy()
        self.signal_sender = signal_sender
        
        # 策略状态
        self.status = StrategyStatus.INIT
        self.active = False
        self.trading = False
        
        # 持仓信息
        self.pos = 0                    # 净持仓数量
        self.target_pos = 0             # 目标持仓

        # 多头持仓
        self.long_pos = 0               # 多头数量
        self.long_price = 0.0           # 多头均价
        self.long_cost = 0.0            # 多头总成本

        # 空头持仓
        self.short_pos = 0              # 空头数量
        self.short_price = 0.0          # 空头均价
        self.short_cost = 0.0           # 空头总成本
        
        # 订单管理
        self.orders: Dict[str, OrderData] = {}
        self.trades: Dict[str, TradeData] = {}
        
        # 数据存储
        self.tick: Optional[TickData] = None
        self.bar: Optional[BarData] = None
        self.bars: List[BarData] = []
        
        # 统计信息
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        
        # 持仓持久化文件
        self._real_positions_file = f"data/real_positions_{strategy_name}_{symbol}.json"

        # 初始化策略参数
        self.update_setting(setting)
        
        logger.info(f"策略初始化完成: {self.strategy_name} - {self.symbol}")
    
    def update_setting(self, setting: Dict[str, Any]) -> None:
        """
        更新策略参数
        
        Args:
            setting: 新的参数设置
        """
        for name in self.parameters:
            if name in setting:
                setattr(self, name, setting[name])
        
        self.setting.update(setting)
        logger.info(f"策略参数更新: {self.strategy_name}")
    
    def get_variables(self) -> Dict[str, Any]:
        """获取策略变量"""
        variables = {}
        for name in self.variables:
            variables[name] = getattr(self, name, None)
        return variables
    
    def get_parameters(self) -> Dict[str, Any]:
        """获取策略参数"""
        parameters = {}
        for name in self.parameters:
            parameters[name] = getattr(self, name, None)
        return parameters
    
    # ==================== 策略生命周期管理 ====================
    
    def start(self) -> None:
        """启动策略"""
        if self.status not in [StrategyStatus.INIT, StrategyStatus.STOPPED]:
            logger.warning(f"策略 {self.strategy_name} 状态异常，无法启动 (当前状态: {self.status})")
            return
        
        try:
            self.active = True
            self.trading = True  # 策略微服务中默认允许交易
            self.status = StrategyStatus.RUNNING
            self.on_init()
            self.on_start()
            logger.info(f"策略启动成功: {self.strategy_name}")
        except Exception as e:
            self.status = StrategyStatus.ERROR
            logger.error(f"策略启动失败 {self.strategy_name}: {e}")
    
    def stop(self) -> None:
        """停止策略"""
        if self.status not in [StrategyStatus.RUNNING, StrategyStatus.PAUSED]:
            logger.warning(f"策略 {self.strategy_name} 未在运行或暂停状态")
            return
        
        try:
            self.active = False
            self.trading = False
            self.status = StrategyStatus.STOPPED
            self.on_stop()
            logger.info(f"策略停止成功: {self.strategy_name}")
        except Exception as e:
            self.status = StrategyStatus.ERROR
            logger.error(f"策略停止失败 {self.strategy_name}: {e}")

    def pause(self) -> None:
        """暂停策略（Trading Service 断连时由引擎调用，冻结信号和下单，保留内部状态）"""
        if self.status != StrategyStatus.RUNNING:
            return

        self.trading = False
        self.status = StrategyStatus.PAUSED
        logger.info(f"策略已暂停: {self.strategy_name}")

    def resume(self) -> None:
        """恢复策略（Trading Service 重连且持仓对齐后由引擎调用）"""
        if self.status != StrategyStatus.PAUSED:
            return

        self.trading = True
        self.status = StrategyStatus.RUNNING
        logger.info(f"策略已恢复: {self.strategy_name}")
    
    # ==================== 标准交易方法 (vnpy风格) ====================
    
    def buy(self, price: float, volume: int, stop: bool = False, time_condition: str = "GFD") -> str:
        """
        买入开仓

        Args:
            price: 委托价格，0表示市价单
            volume: 委托数量
            stop: 是否为停止单
            time_condition: 订单有效期类型 (GFD/GFS，默认GFD激进价格)

        Returns:
            订单ID
        """
        return self._send_order(Direction.LONG, "BUY", volume, price, stop, time_condition)

    def sell(self, price: float, volume: int, stop: bool = False, time_condition: str = "GFD") -> str:
        """
        卖出平仓

        Args:
            price: 委托价格，0表示市价单
            volume: 委托数量
            stop: 是否为停止单
            time_condition: 订单有效期类型 (GFD/GFS，默认GFD激进价格)

        Returns:
            订单ID
        """
        return self._send_order(Direction.SHORT, "SELL", volume, price, stop, time_condition)

    def short(self, price: float, volume: int, stop: bool = False, time_condition: str = "GFD") -> str:
        """
        卖出开仓

        Args:
            price: 委托价格，0表示市价单
            volume: 委托数量
            stop: 是否为停止单
            time_condition: 订单有效期类型 (GFD/GFS，默认GFD激进价格)

        Returns:
            订单ID
        """
        return self._send_order(Direction.SHORT, "SHORT", volume, price, stop, time_condition)

    def cover(self, price: float, volume: int, stop: bool = False, time_condition: str = "GFD") -> str:
        """
        买入平仓

        Args:
            price: 委托价格，0表示市价单
            volume: 委托数量
            stop: 是否为停止单
            time_condition: 订单有效期类型 (GFD/GFS，默认GFD激进价格)

        Returns:
            订单ID
        """
        return self._send_order(Direction.LONG, "COVER", volume, price, stop, time_condition)
    
    def set_target_pos(self, target_pos: int) -> None:
        """
        设置目标持仓
        
        Args:
            target_pos: 目标持仓数量（正数为多头，负数为空头）
        """
        self.target_pos = target_pos
        
        # 计算需要调整的持仓
        pos_diff = target_pos - self.pos
        
        if pos_diff > 0:
            # 需要增加多头持仓
            if self.pos < 0:
                # 当前为空头，先平仓再开多
                cover_volume = min(abs(self.pos), pos_diff)
                self.cover(0, cover_volume)  # 市价平空
                pos_diff -= cover_volume
            
            if pos_diff > 0:
                # 开多头仓位
                self.buy(0, pos_diff)  # 市价买入
        
        elif pos_diff < 0:
            # 需要减少持仓或增加空头
            pos_diff = abs(pos_diff)
            
            if self.pos > 0:
                # 当前为多头，先平仓再开空
                sell_volume = min(self.pos, pos_diff)
                self.sell(0, sell_volume)  # 市价平多
                pos_diff -= sell_volume
            
            if pos_diff > 0:
                # 开空头仓位
                self.short(0, pos_diff)  # 市价卖空
        
        logger.info(f"设置目标持仓: {self.strategy_name} {self.pos} -> {target_pos}")
    
    def _send_order(
        self,
        direction: Direction,
        action: str,
        volume: int,
        price: float,
        stop: bool = False,
        time_condition: str = "GFD"
    ) -> str:
        """
        发送订单信号到交易服务

        架构决策 6：开仓(BUY/SHORT)前必须查询远程持仓，校验通过才发信号；
        平仓(SELL/COVER)不阻塞，优先减少风险敞口。

        Args:
            direction: 交易方向
            action: 交易动作
            volume: 数量
            price: 价格
            stop: 是否为停止单
            time_condition: 订单有效期类型 (GFD/GFS，默认GFD激进价格)

        Returns:
            订单ID
        """
        if not self.active or not self.trading:
            logger.warning(f"策略 {self.strategy_name} 未激活或禁止交易")
            return ""

        # 架构决策 6：开仓前强制查询远程持仓；平仓（SELL/COVER）不阻塞，优先减少风险敞口
        is_open = action in ("BUY", "SHORT")
        if is_open:
            try:
                remote_positions = self.signal_sender.get_positions()
                if remote_positions.get("success") is False:
                    logger.error(
                        f"[{self.strategy_name}] 开仓前持仓查询失败，拒绝发送信号: "
                        f"{remote_positions.get('message', '未知错误')}"
                    )
                    return ""
            except Exception as e:
                logger.error(f"[{self.strategy_name}] 开仓前持仓查询异常，拒绝发送信号: {e}")
                return ""

        signal = SignalData(
            strategy_name=self.strategy_name,
            symbol=self.symbol,
            direction=direction,
            action=action,
            volume=volume,
            price=price if price > 0 else None,
            signal_type="TRADE",
            timestamp=datetime.now()
        )

        order_id = self.signal_sender.send_signal(signal, time_condition)

        logger.info(f"发送交易信号: {self.strategy_name} {action} {volume}@{price} (time_condition={time_condition})")
        return order_id
    
    # ==================== 数据处理方法 ====================
    
    def on_tick(self, tick: TickData) -> None:
        """
        Tick数据回调

        Args:
            tick: Tick数据
        """
        if not self.active:
            return

        self.tick = tick

        # 调用策略实现
        try:
            self.on_tick_impl(tick)
        except Exception as e:
            logger.error(f"策略 {self.strategy_name} Tick处理异常: {e}")
    
    def on_bar(self, bar: BarData) -> None:
        """
        Bar数据回调

        Args:
            bar: Bar数据
        """
        if not self.active:
            logger.warning(f"[{self.strategy_name}] ⚠️ 策略未激活(active={self.active})，跳过bar处理")
            return

        self.bar = bar
        self.bars.append(bar)

        # 限制历史数据长度
        if len(self.bars) > 1000:
            self.bars = self.bars[-1000:]

        # 调用策略实现
        try:
            self.on_bar_impl(bar)
        except Exception as e:
            logger.error(f"策略 {self.strategy_name} Bar处理异常: {e}")
    
    def on_order(self, order: OrderData) -> None:
        """
        订单状态回调

        Args:
            order: 订单数据
        """
        # vnpy 用 orderid 而不是 order_id
        order_id = getattr(order, 'orderid', getattr(order, 'order_id', ''))
        self.orders[order_id] = order

        try:
            self.on_order_impl(order)
        except Exception as e:
            logger.error(f"策略 {self.strategy_name} 订单处理异常: {e}")

    def on_trade(self, trade: TradeData) -> None:
        """
        成交回调

        Args:
            trade: 成交数据
        """
        # vnpy 用 tradeid 而不是 trade_id
        trade_id = getattr(trade, 'tradeid', getattr(trade, 'trade_id', ''))
        self.trades[trade_id] = trade

        # 更新持仓和均价 - 兼容 vnpy 的 Offset 枚举
        # Direction.LONG = 买, Direction.SHORT = 卖
        # 买开 = 开多仓, 买平 = 平空仓
        # 卖开 = 开空仓, 卖平 = 平多仓
        offset_val = str(getattr(trade.offset, 'value', trade.offset)).upper()
        is_open = offset_val in ["OPEN", "开"]
        price = trade.price
        volume = trade.volume

        if trade.direction == Direction.LONG:
            if is_open:
                # 买开：增加多头
                new_cost = self.long_cost + price * volume
                new_volume = self.long_pos + volume
                self.long_price = new_cost / new_volume if new_volume > 0 else 0
                self.long_cost = new_cost
                self.long_pos = new_volume
                self.pos += volume
                logger.info(f"📈 [均价] 多头开仓: {self.long_pos}手@{self.long_price:.2f}")
            else:
                # 买平：平空仓
                new_volume = max(0, self.short_pos - volume)
                if new_volume == 0:
                    self.short_pos = 0
                    self.short_price = 0.0
                    self.short_cost = 0.0
                    logger.info(f"📉 [均价] 空头全平")
                else:
                    self.short_pos = new_volume
                    self.short_cost = new_volume * self.short_price
                    logger.info(f"📉 [均价] 空头平仓: {self.short_pos}手@{self.short_price:.2f}")
                self.pos += volume
        else:  # SHORT
            if is_open:
                # 卖开：增加空头
                new_cost = self.short_cost + price * volume
                new_volume = self.short_pos + volume
                self.short_price = new_cost / new_volume if new_volume > 0 else 0
                self.short_cost = new_cost
                self.short_pos = new_volume
                self.pos -= volume
                logger.info(f"📈 [均价] 空头开仓: {self.short_pos}手@{self.short_price:.2f}")
            else:
                # 卖平：平多仓
                new_volume = max(0, self.long_pos - volume)
                if new_volume == 0:
                    self.long_pos = 0
                    self.long_price = 0.0
                    self.long_cost = 0.0
                    logger.info(f"📉 [均价] 多头全平")
                else:
                    self.long_pos = new_volume
                    self.long_cost = new_volume * self.long_price
                    logger.info(f"📉 [均价] 多头平仓: {self.long_pos}手@{self.long_price:.2f}")
                self.pos -= volume

        # 更新统计
        self.total_trades += 1
        self.total_pnl += trade.pnl if hasattr(trade, 'pnl') else 0

        logger.info(f"策略成交: {self.strategy_name} {trade.direction.value} "
                   f"{volume}@{price} 净持仓:{self.pos} 多:{self.long_pos}@{self.long_price:.2f} 空:{self.short_pos}@{self.short_price:.2f}")

        try:
            self.on_trade_impl(trade)
        except Exception as e:
            logger.error(f"策略 {self.strategy_name} 成交处理异常: {e}")
    
    # ==================== 抽象方法 (子类必须实现) ====================
    
    @abstractmethod
    def on_init(self) -> None:
        """策略初始化"""
        pass
    
    @abstractmethod
    def on_start(self) -> None:
        """策略启动"""
        pass
    
    @abstractmethod
    def on_stop(self) -> None:
        """策略停止"""
        pass
    
    @abstractmethod
    def on_tick_impl(self, tick: TickData) -> None:
        """Tick数据处理实现"""
        pass
    
    @abstractmethod
    def on_bar_impl(self, bar: BarData) -> None:
        """Bar数据处理实现"""
        pass
    
    def on_order_impl(self, order: OrderData) -> None:
        """订单状态处理实现（可选重写）"""
        pass
    
    def on_trade_impl(self, trade: TradeData) -> None:
        """成交处理实现（可选重写）"""
        pass
    
    # ==================== 工具方法 ====================
    
    def write_log(self, msg: str, level: str = "INFO") -> None:
        """写入日志"""
        log_msg = f"[{self.strategy_name}] {msg}"
        if level == "INFO":
            logger.info(log_msg)
        elif level == "WARNING":
            logger.warning(log_msg)
        elif level == "ERROR":
            logger.error(log_msg)
        elif level == "DEBUG":
            logger.debug(log_msg)
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取策略状态信息"""
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "status": self.status.value,
            "active": self.active,
            "trading": self.trading,
            "pos": self.pos,
            "target_pos": self.target_pos,
            "total_trades": self.total_trades,
            "total_pnl": self.total_pnl,
            "parameters": self.get_parameters(),
            "variables": self.get_variables()
        }

    # ==================== 交易时间判断（通用） ====================

    @staticmethod
    def _is_trading_time() -> bool:
        """SHFE 交易时间判断（日盘 + 夜盘）"""
        now = datetime.now()
        t = now.hour * 100 + now.minute
        if 900 <= t <= 1015:
            return True
        if 1030 <= t <= 1130:
            return True
        if 1330 <= t <= 1500:
            return True
        if 2100 <= t <= 2359:
            return True
        if 0 <= t <= 230:
            return True
        return False

    # ==================== 持仓持久化（通用） ====================

    def _load_real_positions(self):
        """从文件恢复持仓均价（重启后保持状态连续）"""
        try:
            os.makedirs("data", exist_ok=True)
            if os.path.exists(self._real_positions_file):
                with open(self._real_positions_file, "r", encoding="utf-8") as f:
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
                logger.info(
                    f"[均价] 加载: 多{self.long_pos}手@{self.long_price:.2f} "
                    f"空{self.short_pos}手@{self.short_price:.2f}"
                )
        except Exception as e:
            logger.error(f"[真实均价] 加载失败: {e}")

    def _save_real_positions(self):
        """持久化持仓均价到文件"""
        try:
            os.makedirs("data", exist_ok=True)
            data = {}
            if self.long_pos > 0:
                data["long"] = {
                    "volume": self.long_pos,
                    "avg_price": round(self.long_price, 4),
                    "total_cost": round(self.long_cost, 4),
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            if self.short_pos > 0:
                data["short"] = {
                    "volume": self.short_pos,
                    "avg_price": round(self.short_price, 4),
                    "total_cost": round(self.short_cost, 4),
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            with open(self._real_positions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[真实均价] 保存失败: {e}")
