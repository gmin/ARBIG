"""
仓位管理模块
实现不同的开仓模式算法
"""

import math
import numpy as np
from typing import Dict, Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class PositionManager:
    """
    仓位管理器
    负责根据不同的开仓模式计算仓位大小
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化仓位管理器
        
        Args:
            config: 仓位管理配置
        """
        self.config = config
        
        # 基础参数
        self.position_size = config.get('position_size', 1)  # 基础开仓手数
        self.max_position = config.get('max_position', 5)    # 最大持仓手数
        self.risk_factor = config.get('risk_factor', 0.02)   # 风险系数
        self.position_mode = config.get('position_mode', 'fixed')  # 开仓模式
        self.position_multiplier = config.get('position_multiplier', 1.0)  # 仓位倍数
        self.add_interval = config.get('add_interval', 50)   # 加仓间隔(点)
        
        # 凯利公式参数
        self.win_rate = config.get('win_rate', 0.6)          # 胜率
        self.avg_win = config.get('avg_win', 1.5)            # 平均盈利比例
        self.avg_loss = config.get('avg_loss', 1.0)          # 平均亏损比例
        
        # 马丁格尔参数
        self.martingale_multiplier = config.get('martingale_multiplier', 2.0)  # 马丁格尔倍数
        self.consecutive_losses = 0  # 连续亏损次数
        
        # 账户信息
        self.account_balance = 100000  # 账户余额，应该从账户服务获取
        
        logger.info(f"仓位管理器初始化完成，模式: {self.position_mode}")
    
    def calculate_position_size(self, signal: str, current_position: int = 0, 
                              price: float = 0, account_info: Optional[Dict] = None) -> int:
        """
        根据开仓模式计算仓位大小
        
        Args:
            signal: 交易信号 ('BUY', 'SELL', 'CLOSE_LONG', 'CLOSE_SHORT')
            current_position: 当前持仓
            price: 当前价格
            account_info: 账户信息
            
        Returns:
            int: 计算出的仓位大小
        """
        try:
            # 更新账户信息
            if account_info:
                self.account_balance = account_info.get('balance', self.account_balance)
            
            # 平仓信号直接返回平仓数量
            if signal in ['CLOSE_LONG', 'CLOSE_SHORT']:
                return self._calculate_close_position(signal, current_position)
            
            # 根据不同模式计算开仓数量
            if self.position_mode == 'fixed':
                position = self._calculate_fixed_position()
            elif self.position_mode == 'risk_based':
                position = self._calculate_risk_based_position(price)
            elif self.position_mode == 'kelly':
                position = self._calculate_kelly_position()
            elif self.position_mode == 'martingale':
                position = self._calculate_martingale_position()
            else:
                logger.warning(f"未知的开仓模式: {self.position_mode}，使用固定手数模式")
                position = self._calculate_fixed_position()
            
            # 应用仓位倍数
            position = int(position * self.position_multiplier)
            
            # 检查仓位限制
            position = self._apply_position_limits(position, current_position, signal)
            
            logger.info(f"计算仓位: 模式={self.position_mode}, 信号={signal}, "
                       f"当前持仓={current_position}, 计算结果={position}")
            
            return position
            
        except Exception as e:
            logger.error(f"计算仓位失败: {e}")
            return 0
    
    def _calculate_fixed_position(self) -> int:
        """固定手数模式"""
        return self.position_size
    
    def _calculate_risk_based_position(self, price: float) -> int:
        """风险比例模式"""
        if price <= 0:
            return self.position_size
        
        # 计算基于风险的仓位
        # 风险金额 = 账户余额 * 风险系数
        risk_amount = self.account_balance * self.risk_factor
        
        # 假设止损比例为5%，计算每手的风险金额
        stop_loss_ratio = 0.05
        risk_per_lot = price * stop_loss_ratio * 1000  # 假设每手1000克
        
        if risk_per_lot > 0:
            position = int(risk_amount / risk_per_lot)
            return max(1, position)  # 至少1手
        
        return self.position_size
    
    def _calculate_kelly_position(self) -> int:
        """凯利公式模式"""
        # 凯利公式: f = (bp - q) / b
        # 其中: b = 平均盈利/平均亏损, p = 胜率, q = 败率
        
        if self.avg_loss <= 0:
            return self.position_size
        
        b = self.avg_win / self.avg_loss  # 盈亏比
        p = self.win_rate  # 胜率
        q = 1 - p  # 败率
        
        # 计算凯利比例
        kelly_fraction = (b * p - q) / b
        
        # 限制凯利比例在合理范围内
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 最大25%
        
        # 计算仓位
        position = int(kelly_fraction * self.account_balance / 10000)  # 假设每手需要10000资金
        
        return max(1, position)
    
    def _calculate_martingale_position(self) -> int:
        """马丁格尔模式"""
        # 基础仓位
        base_position = self.position_size
        
        # 根据连续亏损次数计算倍数
        multiplier = self.martingale_multiplier ** self.consecutive_losses
        
        # 限制最大倍数，避免过度风险
        max_multiplier = 8  # 最大8倍
        multiplier = min(multiplier, max_multiplier)
        
        position = int(base_position * multiplier)
        
        logger.info(f"马丁格尔计算: 连续亏损={self.consecutive_losses}, "
                   f"倍数={multiplier}, 仓位={position}")
        
        return position
    
    def _calculate_close_position(self, signal: str, current_position: int) -> int:
        """计算平仓数量"""
        if signal == 'CLOSE_LONG' and current_position > 0:
            return -current_position  # 全部平多
        elif signal == 'CLOSE_SHORT' and current_position < 0:
            return -current_position  # 全部平空
        
        return 0
    
    def _apply_position_limits(self, position: int, current_position: int, signal: str) -> int:
        """应用仓位限制"""
        # 计算交易后的总持仓
        if signal == 'BUY':
            new_position = current_position + position
        elif signal == 'SELL':
            new_position = current_position - position
        else:
            return position
        
        # 检查是否超过最大持仓
        if abs(new_position) > self.max_position:
            # 调整仓位以不超过限制
            if signal == 'BUY':
                position = max(0, self.max_position - current_position)
            else:  # SELL
                position = max(0, self.max_position + current_position)
        
        return position
    
    def update_trade_result(self, is_win: bool, pnl: float):
        """
        更新交易结果，用于马丁格尔和凯利公式的参数调整
        
        Args:
            is_win: 是否盈利
            pnl: 盈亏金额
        """
        if self.position_mode == 'martingale':
            if is_win:
                self.consecutive_losses = 0  # 重置连续亏损
            else:
                self.consecutive_losses += 1
                
        # 可以在这里更新胜率和盈亏比等统计数据
        logger.info(f"交易结果更新: 盈利={is_win}, 盈亏={pnl}, "
                   f"连续亏损={self.consecutive_losses}")
    
    def can_add_position(self, current_price: float, entry_price: float, 
                        current_position: int) -> bool:
        """
        判断是否可以加仓
        
        Args:
            current_price: 当前价格
            entry_price: 入场价格
            current_position: 当前持仓
            
        Returns:
            bool: 是否可以加仓
        """
        if abs(current_position) >= self.max_position:
            return False
        
        # 检查价格变动是否达到加仓间隔
        price_diff = abs(current_price - entry_price)
        
        # 将加仓间隔从点转换为价格差
        interval_price = self.add_interval * 0.01  # 假设1点=0.01
        
        return price_diff >= interval_price
    
    def get_position_info(self) -> Dict[str, Any]:
        """获取仓位管理信息"""
        return {
            'position_mode': self.position_mode,
            'position_size': self.position_size,
            'max_position': self.max_position,
            'risk_factor': self.risk_factor,
            'position_multiplier': self.position_multiplier,
            'consecutive_losses': self.consecutive_losses,
            'win_rate': self.win_rate,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss
        }
