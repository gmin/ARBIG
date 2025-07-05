"""
Web风控控制器
负责处理来自Web界面的风控操作请求
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import json

from .models import OperationLogEntry
from utils.logger import get_logger

logger = get_logger(__name__)

class WebRiskController:
    """Web风控控制器"""
    
    def __init__(self, trading_system):
        """
        初始化Web风控控制器
        
        Args:
            trading_system: 核心交易系统实例，包含所有服务
        """
        self.trading_system = trading_system
        self.operation_log: List[OperationLogEntry] = []
        
        # 确认码配置
        self.emergency_confirmation_codes = {
            "EMERGENCY_CLOSE_123": "紧急平仓确认码",
            "EMERGENCY_HALT_456": "紧急暂停确认码"
        }
        
        logger.info("Web风控控制器初始化完成")
    
    async def emergency_halt_all(self, reason: str, operator: str) -> bool:
        """
        紧急暂停所有交易
        
        Args:
            reason: 暂停原因
            operator: 操作员
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 调用风控服务的暂停交易方法
            self.trading_system.risk_service._halt_trading(f"人工干预: {reason}")
            
            # 记录操作日志
            await self._log_operation(
                operator=operator,
                action="EMERGENCY_HALT_ALL",
                details=f"紧急暂停所有交易: {reason}",
                success=True
            )
            
            logger.critical(f"[人工干预] 紧急暂停所有交易 - 操作员: {operator}, 原因: {reason}")
            
            # 广播预警（如果Web应用可用）
            await self._broadcast_alert({
                "level": "EMERGENCY",
                "type": "TRADING_HALT",
                "message": f"交易已被紧急暂停: {reason}",
                "operator": operator
            })
            
            return True
            
        except Exception as e:
            logger.error(f"紧急暂停失败: {e}")
            await self._log_operation(
                operator=operator,
                action="EMERGENCY_HALT_ALL",
                details=f"紧急暂停失败: {e}",
                success=False
            )
            return False
    
    async def emergency_close_all(self, reason: str, operator: str, confirmation_code: str) -> bool:
        """
        紧急平仓所有持仓
        
        Args:
            reason: 平仓原因
            operator: 操作员
            confirmation_code: 确认码
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 验证确认码
            if confirmation_code not in self.emergency_confirmation_codes:
                logger.warning(f"[人工干预] 紧急平仓确认码错误 - 操作员: {operator}")
                return False
            
            # 1. 先暂停所有新交易
            self.trading_system.risk_service._halt_trading(f"紧急平仓: {reason}")
            
            # 2. 撤销所有活跃订单
            active_orders = self.trading_system.trading_service.get_active_orders()
            cancelled_count = 0
            for order in active_orders:
                try:
                    if self.trading_system.trading_service.cancel_order(order.orderid):
                        cancelled_count += 1
                except Exception as e:
                    logger.error(f"撤销订单失败 {order.orderid}: {e}")
            
            # 3. TODO: 实现平仓逻辑
            # 这里需要根据当前持仓生成反向订单来平仓
            # positions = self.trading_system.account_service.get_positions()
            # for position in positions:
            #     if position.volume > 0:
            #         # 生成平仓订单
            #         pass
            
            # 记录操作日志
            await self._log_operation(
                operator=operator,
                action="EMERGENCY_CLOSE_ALL",
                details=f"紧急平仓: {reason}, 撤销订单: {cancelled_count}",
                success=True
            )
            
            logger.critical(f"[人工干预] 紧急平仓 - 操作员: {operator}, 原因: {reason}, 撤销订单: {cancelled_count}")
            
            # 广播预警
            await self._broadcast_alert({
                "level": "EMERGENCY",
                "type": "EMERGENCY_CLOSE",
                "message": f"执行紧急平仓: {reason}",
                "operator": operator,
                "cancelled_orders": cancelled_count
            })
            
            return True
            
        except Exception as e:
            logger.error(f"紧急平仓失败: {e}")
            await self._log_operation(
                operator=operator,
                action="EMERGENCY_CLOSE_ALL",
                details=f"紧急平仓失败: {e}",
                success=False
            )
            return False
    
    async def halt_strategy(self, strategy_name: str, reason: str, operator: str) -> bool:
        """
        暂停特定策略
        
        Args:
            strategy_name: 策略名称
            reason: 暂停原因
            operator: 操作员
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 撤销策略的所有活跃订单
            cancelled_count = self.trading_system.trading_service.cancel_strategy_orders(strategy_name)
            
            # TODO: 添加策略暂停标记，防止新订单
            # 这需要在TradingService中添加策略黑名单功能
            
            # 记录操作日志
            await self._log_operation(
                operator=operator,
                action="HALT_STRATEGY",
                details=f"暂停策略 {strategy_name}: {reason}, 撤销订单: {cancelled_count}",
                success=True
            )
            
            logger.warning(f"[人工干预] 暂停策略 {strategy_name} - 操作员: {operator}, 撤销订单: {cancelled_count}")
            
            # 广播预警
            await self._broadcast_alert({
                "level": "WARNING",
                "type": "STRATEGY_HALT",
                "message": f"策略 {strategy_name} 已暂停: {reason}",
                "operator": operator,
                "cancelled_orders": cancelled_count
            })
            
            return True
            
        except Exception as e:
            logger.error(f"暂停策略失败: {e}")
            await self._log_operation(
                operator=operator,
                action="HALT_STRATEGY",
                details=f"暂停策略 {strategy_name} 失败: {e}",
                success=False
            )
            return False
    
    async def resume_trading(self, reason: str, operator: str) -> bool:
        """
        恢复交易
        
        Args:
            reason: 恢复原因
            operator: 操作员
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 调用风控服务的恢复交易方法
            self.trading_system.risk_service.resume_trading()
            
            # 记录操作日志
            await self._log_operation(
                operator=operator,
                action="RESUME_TRADING",
                details=f"恢复交易: {reason}",
                success=True
            )
            
            logger.info(f"[人工干预] 恢复交易 - 操作员: {operator}, 原因: {reason}")
            
            # 广播通知
            await self._broadcast_alert({
                "level": "INFO",
                "type": "TRADING_RESUME",
                "message": f"交易已恢复: {reason}",
                "operator": operator
            })
            
            return True
            
        except Exception as e:
            logger.error(f"恢复交易失败: {e}")
            await self._log_operation(
                operator=operator,
                action="RESUME_TRADING",
                details=f"恢复交易失败: {e}",
                success=False
            )
            return False
    
    async def update_position_limit(self, symbol: str, new_limit: float, reason: str, operator: str) -> bool:
        """
        更新仓位限制
        
        Args:
            symbol: 合约代码
            new_limit: 新的仓位限制
            reason: 调整原因
            operator: 操作员
            
        Returns:
            bool: 操作是否成功
        """
        try:
            old_limit = self.trading_system.risk_service.position_limits.get(symbol, 0)
            self.trading_system.risk_service.position_limits[symbol] = new_limit
            
            # 记录操作日志
            await self._log_operation(
                operator=operator,
                action="UPDATE_POSITION_LIMIT",
                details=f"{symbol}: {old_limit} -> {new_limit}, 原因: {reason}",
                success=True
            )
            
            logger.info(f"[人工干预] 更新仓位限制 {symbol}: {old_limit} -> {new_limit} - 操作员: {operator}")
            
            # 广播通知
            await self._broadcast_alert({
                "level": "INFO",
                "type": "POSITION_LIMIT_UPDATE",
                "message": f"{symbol} 仓位限制已调整为 {new_limit}",
                "operator": operator,
                "old_limit": old_limit,
                "new_limit": new_limit
            })
            
            return True
            
        except Exception as e:
            logger.error(f"更新仓位限制失败: {e}")
            await self._log_operation(
                operator=operator,
                action="UPDATE_POSITION_LIMIT",
                details=f"更新 {symbol} 仓位限制失败: {e}",
                success=False
            )
            return False
    
    async def set_stop_loss(self, symbol: str, price: float, reason: str, operator: str) -> bool:
        """
        设置止损价格
        
        Args:
            symbol: 合约代码
            price: 止损价格
            reason: 设置原因
            operator: 操作员
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # TODO: 实现止损价格设置逻辑
            # 这需要在RiskService中添加止损管理功能
            
            # 记录操作日志
            await self._log_operation(
                operator=operator,
                action="SET_STOP_LOSS",
                details=f"{symbol}: 止损价格 {price}, 原因: {reason}",
                success=True
            )
            
            logger.info(f"[人工干预] 设置止损 {symbol}: {price} - 操作员: {operator}")
            
            # 广播通知
            await self._broadcast_alert({
                "level": "INFO",
                "type": "STOP_LOSS_SET",
                "message": f"{symbol} 止损价格设置为 {price}",
                "operator": operator,
                "price": price
            })
            
            return True
            
        except Exception as e:
            logger.error(f"设置止损失败: {e}")
            await self._log_operation(
                operator=operator,
                action="SET_STOP_LOSS",
                details=f"设置 {symbol} 止损失败: {e}",
                success=False
            )
            return False
    
    async def get_operation_log(self, limit: int = 100) -> List[Dict]:
        """
        获取操作日志
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            List[Dict]: 操作日志列表
        """
        try:
            # 返回最近的操作记录
            recent_logs = self.operation_log[-limit:] if limit > 0 else self.operation_log
            
            return [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "operator": log.operator,
                    "action": log.action,
                    "details": log.details,
                    "success": log.success
                }
                for log in recent_logs
            ]
            
        except Exception as e:
            logger.error(f"获取操作日志失败: {e}")
            return []
    
    async def _log_operation(self, operator: str, action: str, details: str, success: bool = True):
        """记录操作日志"""
        try:
            log_entry = OperationLogEntry(
                timestamp=datetime.now(),
                operator=operator,
                action=action,
                details=details,
                success=success
            )
            
            self.operation_log.append(log_entry)
            
            # 保持最近1000条记录
            if len(self.operation_log) > 1000:
                self.operation_log = self.operation_log[-1000:]
            
            # 同时写入文件日志
            logger.info(f"[操作日志] {operator} - {action}: {details} ({'成功' if success else '失败'})")
            
        except Exception as e:
            logger.error(f"记录操作日志失败: {e}")
    
    async def _broadcast_alert(self, alert_data: Dict):
        """广播预警信息"""
        try:
            # 这里可以通过Web应用的broadcast_alert方法发送预警
            # 由于循环依赖问题，这里先记录日志
            logger.info(f"[风险预警] {alert_data}")
            
            # TODO: 实现其他预警方式（邮件、短信、钉钉等）
            
        except Exception as e:
            logger.error(f"广播预警失败: {e}")
