"""
交易日志数据模型
记录所有交易相关的操作和事件
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import json

Base = declarative_base()


class TradingLog(Base):
    """交易日志表"""
    __tablename__ = 'trading_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 基本信息
    timestamp = Column(DateTime, default=func.now(), nullable=False, comment='时间戳')
    log_type = Column(String(50), nullable=False, comment='日志类型: ORDER, TRADE, SIGNAL, ERROR, INFO')
    level = Column(String(20), default='INFO', comment='日志级别: DEBUG, INFO, WARNING, ERROR')
    
    # 策略信息
    strategy_name = Column(String(100), comment='策略名称')
    strategy_id = Column(String(100), comment='策略ID')
    
    # 交易信息
    symbol = Column(String(50), comment='交易品种')
    direction = Column(String(10), comment='交易方向: BUY, SELL')
    offset = Column(String(20), comment='开平仓: OPEN, CLOSE, CLOSETODAY, CLOSEYESTERDAY')
    volume = Column(Integer, comment='交易数量')
    price = Column(Float, comment='交易价格')
    order_id = Column(String(100), comment='订单ID')
    trade_id = Column(String(100), comment='成交ID')
    
    # 账户信息
    balance = Column(Float, comment='账户余额')
    available = Column(Float, comment='可用资金')
    position = Column(Integer, comment='持仓数量')
    pnl = Column(Float, comment='盈亏')
    
    # 详细信息
    message = Column(Text, comment='日志消息')
    details = Column(Text, comment='详细信息JSON')
    
    # 状态信息
    is_success = Column(Boolean, default=True, comment='是否成功')
    error_code = Column(String(50), comment='错误代码')
    error_message = Column(Text, comment='错误信息')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'log_type': self.log_type,
            'level': self.level,
            'strategy_name': self.strategy_name,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'direction': self.direction,
            'offset': self.offset,
            'volume': self.volume,
            'price': self.price,
            'order_id': self.order_id,
            'trade_id': self.trade_id,
            'balance': self.balance,
            'available': self.available,
            'position': self.position,
            'pnl': self.pnl,
            'message': self.message,
            'details': json.loads(self.details) if self.details else None,
            'is_success': self.is_success,
            'error_code': self.error_code,
            'error_message': self.error_message
        }


class StrategyPerformance(Base):
    """策略性能统计表"""
    __tablename__ = 'strategy_performance'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 基本信息
    strategy_name = Column(String(100), nullable=False, comment='策略名称')
    date = Column(DateTime, default=func.now(), comment='统计日期')
    
    # 交易统计
    total_trades = Column(Integer, default=0, comment='总交易次数')
    winning_trades = Column(Integer, default=0, comment='盈利交易次数')
    losing_trades = Column(Integer, default=0, comment='亏损交易次数')
    
    # 盈亏统计
    total_pnl = Column(Float, default=0.0, comment='总盈亏')
    max_profit = Column(Float, default=0.0, comment='最大盈利')
    max_loss = Column(Float, default=0.0, comment='最大亏损')
    
    # 风险指标
    max_drawdown = Column(Float, default=0.0, comment='最大回撤')
    sharpe_ratio = Column(Float, comment='夏普比率')
    win_rate = Column(Float, comment='胜率')
    
    # 持仓统计
    max_position = Column(Integer, default=0, comment='最大持仓')
    avg_holding_time = Column(Float, comment='平均持仓时间(分钟)')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'strategy_name': self.strategy_name,
            'date': self.date.isoformat() if self.date else None,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_pnl': self.total_pnl,
            'max_profit': self.max_profit,
            'max_loss': self.max_loss,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'win_rate': self.win_rate,
            'max_position': self.max_position,
            'avg_holding_time': self.avg_holding_time
        }


def create_tables(engine):
    """创建数据库表"""
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    # 测试代码
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # 创建数据库引擎
    engine = create_engine('sqlite:///trading_logs.db', echo=True)
    create_tables(engine)
    
    # 创建会话
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 创建测试日志
    log = TradingLog(
        log_type='ORDER',
        level='INFO',
        strategy_name='test_strategy',
        symbol='au2602',
        direction='BUY',
        offset='OPEN',
        volume=1,
        price=775.5,
        order_id='TEST_001',
        message='测试订单',
        is_success=True
    )
    
    session.add(log)
    session.commit()
    
    print("交易日志测试完成")
    session.close()
