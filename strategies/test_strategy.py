"""
测试策略 - 用于系统集成测试
极简的策略逻辑，专注于测试系统功能
"""

import time
import random
from typing import Dict, Any, Optional
from datetime import datetime


class TestStrategy:
    """
    测试策略 - 极简版本
    
    策略逻辑：
    1. 每隔N秒生成一个随机信号
    2. 买入/卖出概率各50%
    3. 固定手数交易
    4. 无复杂指标计算
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = "测试策略"
        self.symbol = config.get('symbol', 'au2510')
        
        # 策略参数
        self.signal_interval = config.get('signal_interval', 30)  # 信号间隔(秒)
        self.trade_volume = config.get('trade_volume', 1)  # 交易手数
        self.max_position = config.get('max_position', 3)  # 最大持仓
        
        # 状态变量
        self.current_position = 0  # 当前持仓 (正数=多头, 负数=空头)
        self.last_signal_time = 0
        self.signal_count = 0
        self.is_running = False
        
        print(f"✅ {self.name} 初始化完成")
        print(f"   交易品种: {self.symbol}")
        print(f"   信号间隔: {self.signal_interval}秒")
        print(f"   交易手数: {self.trade_volume}")
        print(f"   最大持仓: {self.max_position}")
    
    def start(self):
        """启动策略"""
        self.is_running = True
        self.last_signal_time = time.time()
        print(f"🚀 {self.name} 已启动")
    
    def stop(self):
        """停止策略"""
        self.is_running = False
        print(f"⏹️ {self.name} 已停止")
    
    def on_tick(self, tick_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理tick数据
        
        Args:
            tick_data: {
                'symbol': 'au2510',
                'price': 775.5,
                'volume': 100,
                'timestamp': 1642123456.789
            }
        
        Returns:
            交易信号或None
        """
        if not self.is_running:
            return None
        
        current_time = time.time()
        
        # 检查是否到了生成信号的时间
        if current_time - self.last_signal_time < self.signal_interval:
            return None
        
        # 生成随机信号
        signal = self._generate_test_signal(tick_data)
        
        if signal:
            self.last_signal_time = current_time
            self.signal_count += 1
            print(f"📊 {self.name} 生成信号 #{self.signal_count}: {signal}")
        
        return signal
    
    def _generate_test_signal(self, tick_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """生成测试信号"""
        current_price = tick_data.get('price', 775.0)
        
        # 30%概率不生成信号
        if random.random() < 0.3:
            return None
        
        # 检查持仓限制
        if abs(self.current_position) >= self.max_position:
            # 如果已达最大持仓，只能平仓
            if self.current_position > 0:
                action = 'SELL'
                reason = "多头持仓已满，平仓"
            elif self.current_position < 0:
                action = 'BUY'
                reason = "空头持仓已满，平仓"
            else:
                return None
        else:
            # 随机选择买入或卖出
            action = random.choice(['BUY', 'SELL'])
            reason = f"随机信号 - {action}"
        
        # 更新模拟持仓
        if action == 'BUY':
            self.current_position += self.trade_volume
        else:
            self.current_position -= self.trade_volume
        
        return {
            'action': action,
            'symbol': self.symbol,
            'volume': self.trade_volume,
            'price': current_price,
            'order_type': 'MARKET',
            'reason': reason,
            'timestamp': time.time(),
            'strategy': self.name,
            'signal_id': self.signal_count,
            'position_after': self.current_position
        }
    
    def on_order_filled(self, order_info: Dict[str, Any]):
        """订单成交回调"""
        print(f"✅ {self.name} 订单成交: {order_info}")
    
    def on_order_rejected(self, order_info: Dict[str, Any], reason: str):
        """订单拒绝回调"""
        print(f"❌ {self.name} 订单被拒: {reason}")
        
        # 回滚持仓状态
        action = order_info.get('action')
        volume = order_info.get('volume', 1)
        if action == 'BUY':
            self.current_position -= volume
        else:
            self.current_position += volume
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        return {
            'name': self.name,
            'symbol': self.symbol,
            'is_running': self.is_running,
            'current_position': self.current_position,
            'signal_count': self.signal_count,
            'last_signal_time': self.last_signal_time,
            'config': self.config
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新策略配置"""
        self.config.update(new_config)
        
        # 更新关键参数
        self.signal_interval = self.config.get('signal_interval', 30)
        self.trade_volume = self.config.get('trade_volume', 1)
        self.max_position = self.config.get('max_position', 3)
        
        print(f"⚙️ {self.name} 配置已更新: {new_config}")


def create_strategy(config: Dict[str, Any]) -> TestStrategy:
    """策略工厂函数"""
    return TestStrategy(config)


# 测试代码
if __name__ == "__main__":
    # 测试策略
    config = {
        'symbol': 'au2510',
        'signal_interval': 10,  # 10秒生成一次信号
        'trade_volume': 1,
        'max_position': 2
    }
    
    strategy = TestStrategy(config)
    strategy.start()
    
    # 模拟tick数据
    for i in range(5):
        tick = {
            'symbol': 'au2510',
            'price': 775.0 + random.uniform(-2, 2),
            'volume': random.randint(1, 10),
            'timestamp': time.time()
        }
        
        signal = strategy.on_tick(tick)
        if signal:
            print(f"生成信号: {signal}")
        
        time.sleep(2)
    
    print(f"策略状态: {strategy.get_status()}")
    strategy.stop()
