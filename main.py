"""
主程序
系统入口
"""

import time
from datetime import datetime

from config.config import CONFIG
from core.data import DataManager
from core.strategy import ArbitrageStrategy
from core.trader import Trader
from core.risk import RiskManager
from monitor.monitor import Monitor
from utils.logger import get_logger

logger = get_logger(__name__)

class ArbitrageSystem:
    """
    套利系统主类
    """
    
    def __init__(self, config=None):
        """
        初始化系统
        
        Args:
            config: 配置字典，如果为None则使用默认配置
        """
        self.config = config or CONFIG
        self.data_manager = DataManager()
        self.strategy = ArbitrageStrategy(self.config)
        self.trader = Trader(self.config)
        self.risk_manager = RiskManager(self.config)
        self.monitor = Monitor()
        
    def run(self):
        """
        运行系统
        """
        logger.info("系统启动")
        
        while True:
            try:
                # 1. 更新数据
                if not self.data_manager.update_prices():
                    logger.warning("更新价格数据失败")
                    time.sleep(1)
                    continue
                    
                # 2. 计算基差
                spread = self.data_manager.calculate_spread()
                if spread is None:
                    logger.warning("无法计算基差")
                    time.sleep(1)
                    continue
                    
                # 3. 生成信号
                signal = self.strategy.generate_signal(spread)
                if signal is None:
                    logger.info("无交易信号")
                    time.sleep(1)
                    continue
                    
                # 4. 计算仓位
                position = self.strategy.calculate_position(
                    signal,
                    self.trader.positions
                )
                
                # 5. 风险检查
                if not self.risk_manager.check_risk(
                    signal,
                    position,
                    self.trader.positions
                ):
                    logger.warning("未通过风险检查")
                    time.sleep(1)
                    continue
                    
                # 6. 执行交易
                if not self.trader.execute_trade(signal, position):
                    logger.error("执行交易失败")
                    time.sleep(1)
                    continue
                    
                # 7. 更新持仓
                self.trader.update_positions()
                
                # 8. 记录日志
                self.monitor.log_trade({
                    'signal': signal,
                    'position': position,
                    'spread': spread,
                    'timestamp': datetime.now()
                })
                
                self.monitor.log_position(self.trader.positions)
                
                # 9. 等待下一次循环
                time.sleep(self.config.get('trade_interval', 1))
                
            except Exception as e:
                logger.error(f"系统运行异常: {str(e)}")
                time.sleep(1)
                
    def stop(self):
        """
        停止系统
        """
        logger.info("系统停止")
        # TODO: 实现系统停止逻辑
        
if __name__ == '__main__':
    system = ArbitrageSystem()
    try:
        system.run()
    except KeyboardInterrupt:
        system.stop()
