"""
风控服务
负责交易前风控检查、实时风控监控和风险事件处理
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable
from datetime import datetime, date

from ..event_engine import EventEngine, Event
from ..types import (
    OrderRequest, TradeData, RiskCheckResult, RiskMetrics,
    ServiceStatus, ServiceConfig, Direction
)
from ..constants import RISK_EVENT, TRADE_EVENT
from ...utils.logger import get_logger

logger = get_logger(__name__)

class RiskServiceBase(ABC):
    """风控服务基类"""
    
    def __init__(self, event_engine: EventEngine, config: ServiceConfig):
        """
        初始化风控服务
        
        Args:
            event_engine: 事件引擎
            config: 服务配置
        """
        self.event_engine = event_engine
        self.config = config
        self.status = ServiceStatus.STOPPED
        
        # 风控参数
        self.max_position_ratio = config.config.get('max_position_ratio', 0.8)
        self.max_daily_loss = config.config.get('max_daily_loss', 50000)
        self.stop_loss_ratio = config.config.get('stop_loss_ratio', 0.02)
        self.max_single_order_volume = config.config.get('max_single_order_volume', 100)
        
        # 风险指标
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        self.peak_balance = 0.0
        
        # 持仓风险
        self.position_limits: Dict[str, float] = {}  # symbol -> max_volume
        self.current_positions: Dict[str, float] = {}  # symbol -> current_volume
        
        # 交易统计
        self.daily_trade_count = 0
        self.daily_trade_volume = 0.0
        self.last_trade_date = None
        
        # 风险状态
        self.risk_level = "LOW"
        self.is_trading_halted = False
        self.halt_reason = ""
        
        # 回调函数
        self.risk_callbacks: List[Callable[[RiskMetrics], None]] = []
        
        # 注册事件处理
        self.event_engine.register(TRADE_EVENT, self.on_trade_event)
        
        logger.info(f"风控服务初始化完成: {self.config.name}")
    
    @abstractmethod
    def start(self) -> bool:
        """启动服务"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止服务"""
        pass
    
    def check_pre_trade_risk(self, order_req: OrderRequest) -> RiskCheckResult:
        """
        交易前风控检查
        
        Args:
            order_req: 订单请求
            
        Returns:
            RiskCheckResult: 风控检查结果
        """
        try:
            # 检查交易是否被暂停
            if self.is_trading_halted:
                return RiskCheckResult(
                    passed=False,
                    reason=f"交易已暂停: {self.halt_reason}",
                    risk_level="CRITICAL"
                )
            
            # 检查单笔订单数量限制
            if order_req.volume > self.max_single_order_volume:
                return RiskCheckResult(
                    passed=False,
                    reason=f"单笔订单数量超限: {order_req.volume} > {self.max_single_order_volume}",
                    suggested_volume=self.max_single_order_volume,
                    risk_level="HIGH"
                )
            
            # 检查持仓限制
            position_check = self._check_position_limit(order_req.symbol, order_req.direction, order_req.volume)
            if not position_check['passed']:
                return RiskCheckResult(
                    passed=False,
                    reason=position_check['reason'],
                    suggested_volume=position_check.get('suggested_volume', 0),
                    risk_level="MEDIUM"
                )
            
            # 检查资金限制
            fund_check = self._check_fund_limit(order_req)
            if not fund_check['passed']:
                return RiskCheckResult(
                    passed=False,
                    reason=fund_check['reason'],
                    risk_level="HIGH"
                )
            
            # 检查日内亏损限制
            if self.daily_pnl < -self.max_daily_loss:
                return RiskCheckResult(
                    passed=False,
                    reason=f"日内亏损超限: {self.daily_pnl} < -{self.max_daily_loss}",
                    risk_level="CRITICAL"
                )
            
            # 所有检查通过
            return RiskCheckResult(
                passed=True,
                reason="风控检查通过",
                risk_level=self.risk_level
            )
            
        except Exception as e:
            logger.error(f"风控检查异常: {e}")
            return RiskCheckResult(
                passed=False,
                reason=f"风控检查异常: {e}",
                risk_level="CRITICAL"
            )
    
    def _check_position_limit(self, symbol: str, direction: Direction, volume: float) -> Dict:
        """检查持仓限制"""
        try:
            # 获取当前持仓
            current_pos = self.current_positions.get(symbol, 0.0)
            
            # 计算新持仓
            if direction == Direction.LONG:
                new_pos = current_pos + volume
            else:
                new_pos = current_pos - volume
            
            # 获取持仓限制
            max_pos = self.position_limits.get(symbol, 1000.0)  # 默认限制
            
            # 检查是否超限
            if abs(new_pos) > max_pos:
                suggested_volume = max(0, max_pos - abs(current_pos))
                return {
                    'passed': False,
                    'reason': f"持仓将超限: {abs(new_pos)} > {max_pos}",
                    'suggested_volume': suggested_volume
                }
            
            return {'passed': True}
            
        except Exception as e:
            logger.error(f"检查持仓限制异常: {e}")
            return {'passed': False, 'reason': f"持仓检查异常: {e}"}
    
    def _check_fund_limit(self, order_req: OrderRequest) -> Dict:
        """检查资金限制"""
        try:
            # 这里需要从账户服务获取可用资金
            # 简化实现，实际应该计算所需保证金
            required_margin = order_req.volume * order_req.price * 0.1  # 假设10%保证金
            
            # 这里应该从账户服务获取可用资金
            # available_funds = self.account_service.get_available_funds()
            available_funds = 100000  # 临时值
            
            if required_margin > available_funds:
                return {
                    'passed': False,
                    'reason': f"资金不足: 需要 {required_margin}, 可用 {available_funds}"
                }
            
            return {'passed': True}
            
        except Exception as e:
            logger.error(f"检查资金限制异常: {e}")
            return {'passed': False, 'reason': f"资金检查异常: {e}"}
    
    def update_pnl(self, trade: TradeData) -> None:
        """
        更新PnL
        
        Args:
            trade: 成交信息
        """
        try:
            # 更新交易统计
            today = date.today()
            if self.last_trade_date != today:
                # 新的一天，重置日内统计
                self.daily_pnl = 0.0
                self.daily_trade_count = 0
                self.daily_trade_volume = 0.0
                self.last_trade_date = today
            
            self.daily_trade_count += 1
            self.daily_trade_volume += trade.volume
            
            # 更新持仓（简化实现）
            symbol = trade.symbol
            if symbol not in self.current_positions:
                self.current_positions[symbol] = 0.0
            
            if trade.direction == Direction.LONG:
                self.current_positions[symbol] += trade.volume
            else:
                self.current_positions[symbol] -= trade.volume
            
            # 计算PnL（这里需要更复杂的逻辑）
            # 简化实现，实际应该根据开仓价、当前价等计算
            pnl_change = 0.0  # 临时值
            
            self.daily_pnl += pnl_change
            self.total_pnl += pnl_change
            
            # 更新回撤
            if self.total_pnl > self.peak_balance:
                self.peak_balance = self.total_pnl
                self.current_drawdown = 0.0
            else:
                self.current_drawdown = self.peak_balance - self.total_pnl
                if self.current_drawdown > self.max_drawdown:
                    self.max_drawdown = self.current_drawdown
            
            # 更新风险级别
            self._update_risk_level()
            
            logger.debug(f"PnL更新: 日内 {self.daily_pnl}, 总计 {self.total_pnl}, 回撤 {self.current_drawdown}")
            
        except Exception as e:
            logger.error(f"更新PnL异常: {e}")
    
    def _update_risk_level(self) -> None:
        """更新风险级别"""
        try:
            # 根据各种指标计算风险级别
            risk_score = 0
            
            # 日内亏损风险
            if self.daily_pnl < -self.max_daily_loss * 0.5:
                risk_score += 2
            elif self.daily_pnl < -self.max_daily_loss * 0.3:
                risk_score += 1
            
            # 回撤风险
            if self.current_drawdown > self.peak_balance * 0.2:
                risk_score += 3
            elif self.current_drawdown > self.peak_balance * 0.1:
                risk_score += 2
            elif self.current_drawdown > self.peak_balance * 0.05:
                risk_score += 1
            
            # 持仓风险
            total_position = sum(abs(pos) for pos in self.current_positions.values())
            if total_position > 1000:  # 假设总持仓限制
                risk_score += 2
            elif total_position > 500:
                risk_score += 1
            
            # 确定风险级别
            if risk_score >= 5:
                new_risk_level = "CRITICAL"
            elif risk_score >= 3:
                new_risk_level = "HIGH"
            elif risk_score >= 1:
                new_risk_level = "MEDIUM"
            else:
                new_risk_level = "LOW"
            
            # 如果风险级别变化，发送事件
            if new_risk_level != self.risk_level:
                old_level = self.risk_level
                self.risk_level = new_risk_level
                
                self._handle_risk_level_change(old_level, new_risk_level)
                
        except Exception as e:
            logger.error(f"更新风险级别异常: {e}")
    
    def _handle_risk_level_change(self, old_level: str, new_level: str) -> None:
        """处理风险级别变化"""
        try:
            logger.warning(f"风险级别变化: {old_level} -> {new_level}")
            
            # 发送风险事件
            risk_metrics = self.get_risk_metrics()
            event_data = {
                'risk_type': 'LEVEL_CHANGE',
                'old_level': old_level,
                'new_level': new_level,
                'metrics': risk_metrics
            }
            
            event = Event(RISK_EVENT, event_data)
            self.event_engine.put(event)
            
            # 根据风险级别采取行动
            if new_level == "CRITICAL":
                self._halt_trading("风险级别达到临界状态")
            
        except Exception as e:
            logger.error(f"处理风险级别变化异常: {e}")
    
    def _halt_trading(self, reason: str) -> None:
        """暂停交易"""
        self.is_trading_halted = True
        self.halt_reason = reason
        logger.critical(f"交易已暂停: {reason}")
        
        # 发送暂停交易事件
        event_data = {
            'risk_type': 'TRADING_HALT',
            'reason': reason,
            'timestamp': datetime.now()
        }
        event = Event(RISK_EVENT, event_data)
        self.event_engine.put(event)
    
    def resume_trading(self) -> None:
        """恢复交易"""
        self.is_trading_halted = False
        self.halt_reason = ""
        logger.info("交易已恢复")
    
    def on_trade_event(self, event: Event) -> None:
        """处理成交事件"""
        try:
            trade = event.data
            if isinstance(trade, TradeData):
                self.update_pnl(trade)
        except Exception as e:
            logger.error(f"处理成交事件异常: {e}")
    
    def get_risk_metrics(self) -> RiskMetrics:
        """获取风险指标"""
        return RiskMetrics(
            timestamp=datetime.now(),
            daily_pnl=self.daily_pnl,
            total_pnl=self.total_pnl,
            max_drawdown=self.max_drawdown,
            position_ratio=sum(abs(pos) for pos in self.current_positions.values()) / 1000,  # 假设基准
            margin_ratio=0.5,  # 临时值
            risk_level=self.risk_level
        )
    
    def get_status(self) -> ServiceStatus:
        """获取服务状态"""
        return self.status
    
    def get_statistics(self) -> Dict[str, any]:
        """获取服务统计信息"""
        return {
            'status': self.status.value,
            'risk_level': self.risk_level,
            'is_trading_halted': self.is_trading_halted,
            'daily_pnl': self.daily_pnl,
            'total_pnl': self.total_pnl,
            'max_drawdown': self.max_drawdown,
            'current_drawdown': self.current_drawdown,
            'daily_trade_count': self.daily_trade_count,
            'total_positions': len(self.current_positions),
            'max_daily_loss': self.max_daily_loss,
            'max_position_ratio': self.max_position_ratio
        }

class RiskService(RiskServiceBase):
    """风控服务实现"""

    def __init__(self, event_engine: EventEngine, config: ServiceConfig, account_service=None):
        """
        初始化风控服务

        Args:
            event_engine: 事件引擎
            config: 服务配置
            account_service: 账户服务实例
        """
        super().__init__(event_engine, config)
        self.account_service = account_service

    def start(self) -> bool:
        """启动服务"""
        try:
            if self.status == ServiceStatus.RUNNING:
                logger.warning("风控服务已在运行")
                return True

            self.status = ServiceStatus.STARTING

            # 初始化持仓限制
            symbols = ['AU2509', 'AU2512']  # 从配置获取
            for symbol in symbols:
                self.position_limits[symbol] = 1000.0  # 默认限制

            self.status = ServiceStatus.RUNNING
            logger.info("风控服务启动成功")
            return True

        except Exception as e:
            logger.error(f"风控服务启动失败: {e}")
            self.status = ServiceStatus.ERROR
            return False

    def stop(self) -> None:
        """停止服务"""
        try:
            if self.status == ServiceStatus.STOPPED:
                return

            self.status = ServiceStatus.STOPPING

            # 清理数据
            self.position_limits.clear()
            self.current_positions.clear()
            self.risk_callbacks.clear()

            # 重置风险状态
            self.is_trading_halted = False
            self.halt_reason = ""
            self.risk_level = "LOW"

            self.status = ServiceStatus.STOPPED
            logger.info("风控服务已停止")

        except Exception as e:
            logger.error(f"停止风控服务失败: {e}")
            self.status = ServiceStatus.ERROR

    def _check_fund_limit(self, order_req: OrderRequest) -> Dict:
        """检查资金限制（重写以使用账户服务）"""
        try:
            # 计算所需保证金
            required_margin = order_req.volume * order_req.price * 0.1  # 假设10%保证金

            # 从账户服务获取可用资金
            if self.account_service:
                available_funds = self.account_service.get_available_funds()
            else:
                available_funds = 100000  # 默认值

            if required_margin > available_funds * self.max_position_ratio:
                return {
                    'passed': False,
                    'reason': f"资金使用率超限: 需要 {required_margin}, 可用 {available_funds}, 限制比例 {self.max_position_ratio}"
                }

            return {'passed': True}

        except Exception as e:
            logger.error(f"检查资金限制异常: {e}")
            return {'passed': False, 'reason': f"资金检查异常: {e}"}
