"""
交易日志管理器
负责记录和管理所有交易相关的日志
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc, and_, func

from shared.database.connection import get_db_manager
from shared.models.trading_log import TradingLog, StrategyPerformance, create_tables
from utils.logger import get_logger

logger = get_logger(__name__)


class TradingLogger:
    """交易日志管理器"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.session = None
        self._ensure_tables()
    
    def _ensure_tables(self):
        """确保数据库表存在"""
        try:
            create_tables(self.db_manager.engine)
            logger.info("交易日志表初始化完成")
        except Exception as e:
            logger.error(f"交易日志表初始化失败: {e}")
    
    def _get_session(self):
        """获取数据库会话"""
        if not self.session:
            Session = sessionmaker(bind=self.db_manager.engine)
            self.session = Session()
        return self.session
    
    def log_order(self, strategy_name: str, symbol: str, direction: str, 
                  offset: str, volume: int, price: float, order_id: str,
                  message: str = "", details: Dict = None, is_success: bool = True,
                  error_code: str = None, error_message: str = None):
        """记录订单日志"""
        try:
            session = self._get_session()
            
            log = TradingLog(
                log_type='ORDER',
                level='INFO' if is_success else 'ERROR',
                strategy_name=strategy_name,
                symbol=symbol,
                direction=direction,
                offset=offset,
                volume=volume,
                price=price,
                order_id=order_id,
                message=message,
                details=json.dumps(details) if details else None,
                is_success=is_success,
                error_code=error_code,
                error_message=error_message
            )
            
            session.add(log)
            session.commit()
            
            logger.info(f"订单日志记录成功: {strategy_name} {symbol} {direction} {volume}@{price}")
            
        except Exception as e:
            logger.error(f"记录订单日志失败: {e}")
            if self.session:
                self.session.rollback()
    
    def log_trade(self, strategy_name: str, symbol: str, direction: str,
                  volume: int, price: float, trade_id: str, order_id: str = None,
                  pnl: float = None, balance: float = None, available: float = None,
                  position: int = None, message: str = "", details: Dict = None):
        """记录成交日志"""
        try:
            session = self._get_session()
            
            log = TradingLog(
                log_type='TRADE',
                level='INFO',
                strategy_name=strategy_name,
                symbol=symbol,
                direction=direction,
                volume=volume,
                price=price,
                trade_id=trade_id,
                order_id=order_id,
                pnl=pnl,
                balance=balance,
                available=available,
                position=position,
                message=message,
                details=json.dumps(details) if details else None,
                is_success=True
            )
            
            session.add(log)
            session.commit()
            
            logger.info(f"成交日志记录成功: {strategy_name} {symbol} {direction} {volume}@{price}")
            
        except Exception as e:
            logger.error(f"记录成交日志失败: {e}")
            if self.session:
                self.session.rollback()
    
    def log_signal(self, strategy_name: str, symbol: str, signal_type: str,
                   signal_data: Dict, message: str = ""):
        """记录策略信号日志"""
        try:
            session = self._get_session()
            
            log = TradingLog(
                log_type='SIGNAL',
                level='INFO',
                strategy_name=strategy_name,
                symbol=symbol,
                message=message,
                details=json.dumps({
                    'signal_type': signal_type,
                    'signal_data': signal_data
                }),
                is_success=True
            )
            
            session.add(log)
            session.commit()
            
            logger.debug(f"信号日志记录成功: {strategy_name} {signal_type}")
            
        except Exception as e:
            logger.error(f"记录信号日志失败: {e}")
            if self.session:
                self.session.rollback()
    
    def log_error(self, strategy_name: str, error_type: str, error_message: str,
                  details: Dict = None, symbol: str = None):
        """记录错误日志"""
        try:
            session = self._get_session()
            
            log = TradingLog(
                log_type='ERROR',
                level='ERROR',
                strategy_name=strategy_name,
                symbol=symbol,
                message=error_message,
                details=json.dumps(details) if details else None,
                is_success=False,
                error_code=error_type,
                error_message=error_message
            )
            
            session.add(log)
            session.commit()
            
            logger.error(f"错误日志记录成功: {strategy_name} {error_type}")
            
        except Exception as e:
            logger.error(f"记录错误日志失败: {e}")
            if self.session:
                self.session.rollback()
    
    def log_info(self, strategy_name: str, message: str, details: Dict = None,
                 symbol: str = None):
        """记录信息日志"""
        try:
            session = self._get_session()
            
            log = TradingLog(
                log_type='INFO',
                level='INFO',
                strategy_name=strategy_name,
                symbol=symbol,
                message=message,
                details=json.dumps(details) if details else None,
                is_success=True
            )
            
            session.add(log)
            session.commit()
            
            logger.debug(f"信息日志记录成功: {strategy_name}")
            
        except Exception as e:
            logger.error(f"记录信息日志失败: {e}")
            if self.session:
                self.session.rollback()
    
    def get_logs(self, strategy_name: str = None, log_type: str = None,
                 start_time: datetime = None, end_time: datetime = None,
                 limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取交易日志"""
        try:
            session = self._get_session()
            
            query = session.query(TradingLog)
            
            # 添加过滤条件
            if strategy_name:
                query = query.filter(TradingLog.strategy_name == strategy_name)
            
            if log_type:
                query = query.filter(TradingLog.log_type == log_type)
            
            if start_time:
                query = query.filter(TradingLog.timestamp >= start_time)
            
            if end_time:
                query = query.filter(TradingLog.timestamp <= end_time)
            
            # 排序和分页
            query = query.order_by(desc(TradingLog.timestamp))
            query = query.offset(offset).limit(limit)
            
            logs = query.all()
            return [log.to_dict() for log in logs]
            
        except Exception as e:
            logger.error(f"获取交易日志失败: {e}")
            return []
    
    def get_strategy_performance(self, strategy_name: str, 
                               days: int = 30) -> Dict:
        """获取策略性能统计"""
        try:
            session = self._get_session()
            
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # 获取交易日志
            trades = session.query(TradingLog).filter(
                and_(
                    TradingLog.strategy_name == strategy_name,
                    TradingLog.log_type == 'TRADE',
                    TradingLog.timestamp >= start_time,
                    TradingLog.timestamp <= end_time
                )
            ).all()
            
            if not trades:
                return {
                    'strategy_name': strategy_name,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_pnl': 0.0,
                    'win_rate': 0.0,
                    'max_profit': 0.0,
                    'max_loss': 0.0
                }
            
            # 计算统计数据
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
            losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
            total_pnl = sum([t.pnl for t in trades if t.pnl])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            pnl_list = [t.pnl for t in trades if t.pnl]
            max_profit = max(pnl_list) if pnl_list else 0
            max_loss = min(pnl_list) if pnl_list else 0
            
            return {
                'strategy_name': strategy_name,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'total_pnl': round(total_pnl, 2),
                'win_rate': round(win_rate * 100, 2),
                'max_profit': round(max_profit, 2),
                'max_loss': round(max_loss, 2),
                'avg_profit': round(total_pnl / total_trades, 2) if total_trades > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取策略性能统计失败: {e}")
            return {}
    
    def close(self):
        """关闭数据库连接"""
        if self.session:
            self.session.close()
            self.session = None


# 全局交易日志管理器实例
_trading_logger = None


def get_trading_logger() -> TradingLogger:
    """获取交易日志管理器实例"""
    global _trading_logger
    if _trading_logger is None:
        _trading_logger = TradingLogger()
    return _trading_logger
