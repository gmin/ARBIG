"""
简单回测模块
用于策略参数优化和历史表现分析
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SimpleBacktester:
    """
    简单回测器
    用于快速验证策略参数的历史表现
    """
    
    def __init__(self, initial_capital: float = 100000):
        """
        初始化回测器
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = []
        
    def run_backtest(self, strategy_params: Dict[str, Any], 
                    start_date: str, end_date: str) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            strategy_params: 策略参数
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict: 回测结果
        """
        try:
            # 生成模拟价格数据
            price_data = self._generate_mock_data(start_date, end_date)
            
            # 运行策略
            signals = self._generate_signals(price_data, strategy_params)
            
            # 执行交易
            self._execute_trades(price_data, signals, strategy_params)
            
            # 计算回测指标
            results = self._calculate_metrics()
            
            logger.info(f"回测完成: {start_date} 到 {end_date}, 总收益: {results['total_return']:.2%}")
            
            return results
            
        except Exception as e:
            logger.error(f"回测失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_mock_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟价格数据"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # 生成日期序列
        dates = pd.date_range(start=start, end=end, freq='D')
        
        # 生成模拟价格（随机游走 + 趋势）
        np.random.seed(42)  # 固定随机种子，确保结果可重现
        
        base_price = 450.0  # 黄金基础价格
        returns = np.random.normal(0.0001, 0.02, len(dates))  # 日收益率
        
        # 添加一些趋势和周期性
        trend = np.linspace(0, 0.1, len(dates))  # 轻微上升趋势
        cycle = 0.05 * np.sin(np.arange(len(dates)) * 2 * np.pi / 30)  # 30天周期
        
        returns += trend / len(dates) + cycle / len(dates)
        
        # 计算价格
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # 生成OHLC数据
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # 简单的OHLC生成
            volatility = abs(np.random.normal(0, 0.01))
            high = price * (1 + volatility)
            low = price * (1 - volatility)
            open_price = prices[i-1] if i > 0 else price
            close_price = price
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': np.random.randint(1000, 10000)
            })
        
        return pd.DataFrame(data)
    
    def _generate_signals(self, data: pd.DataFrame, params: Dict[str, Any]) -> List[str]:
        """根据策略参数生成交易信号"""
        signals = []
        
        # 计算技术指标
        ma_short = params.get('ma_short', 5)
        ma_long = params.get('ma_long', 20)
        rsi_period = params.get('rsi_period', 14)
        rsi_overbought = params.get('rsi_overbought', 70)
        rsi_oversold = params.get('rsi_oversold', 30)
        
        # 计算移动平均线
        data['ma_short'] = data['close'].rolling(window=ma_short).mean()
        data['ma_long'] = data['close'].rolling(window=ma_long).mean()
        
        # 计算RSI
        data['rsi'] = self._calculate_rsi(data['close'], rsi_period)
        
        # 生成信号
        position = 0  # 当前持仓状态：0=空仓，1=多头，-1=空头
        
        for i in range(len(data)):
            if i < max(ma_long, rsi_period):
                signals.append('HOLD')
                continue
            
            ma_short_val = data.iloc[i]['ma_short']
            ma_long_val = data.iloc[i]['ma_long']
            rsi_val = data.iloc[i]['rsi']
            
            signal = 'HOLD'
            
            # 趋势跟踪策略
            if position == 0:  # 空仓时寻找开仓机会
                if ma_short_val > ma_long_val and rsi_val < rsi_overbought:
                    signal = 'BUY'
                    position = 1
                elif ma_short_val < ma_long_val and rsi_val > rsi_oversold:
                    signal = 'SELL'
                    position = -1
            elif position == 1:  # 持多头时寻找平仓机会
                if ma_short_val < ma_long_val or rsi_val > rsi_overbought:
                    signal = 'CLOSE_LONG'
                    position = 0
            elif position == -1:  # 持空头时寻找平仓机会
                if ma_short_val > ma_long_val or rsi_val < rsi_oversold:
                    signal = 'CLOSE_SHORT'
                    position = 0
            
            signals.append(signal)
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _execute_trades(self, data: pd.DataFrame, signals: List[str], params: Dict[str, Any]):
        """执行交易"""
        position = 0
        entry_price = 0
        
        for i, signal in enumerate(signals):
            if signal in ['BUY', 'SELL']:
                if position == 0:  # 开仓
                    entry_price = data.iloc[i]['close']
                    position = 1 if signal == 'BUY' else -1
                    
                    trade = {
                        'type': 'OPEN',
                        'direction': signal,
                        'price': entry_price,
                        'date': data.iloc[i]['date'],
                        'position': position
                    }
                    self.trades.append(trade)
                    
            elif signal in ['CLOSE_LONG', 'CLOSE_SHORT']:
                if position != 0:  # 平仓
                    exit_price = data.iloc[i]['close']
                    pnl = (exit_price - entry_price) * position
                    
                    trade = {
                        'type': 'CLOSE',
                        'direction': signal,
                        'price': exit_price,
                        'date': data.iloc[i]['date'],
                        'pnl': pnl,
                        'entry_price': entry_price
                    }
                    self.trades.append(trade)
                    
                    # 更新资金
                    self.current_capital += pnl
                    position = 0
            
            # 记录权益曲线
            self.equity_curve.append({
                'date': data.iloc[i]['date'],
                'equity': self.current_capital,
                'position': position
            })
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """计算回测指标"""
        if not self.trades:
            return {
                "total_return": 0.0,
                "annual_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "win_rate": 0.0,
                "total_trades": 0
            }
        
        # 计算基本指标
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        
        # 计算最大回撤
        equity_values = [point['equity'] for point in self.equity_curve]
        peak = equity_values[0]
        max_drawdown = 0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 计算胜率
        closed_trades = [t for t in self.trades if t['type'] == 'CLOSE']
        if closed_trades:
            winning_trades = [t for t in closed_trades if t['pnl'] > 0]
            win_rate = len(winning_trades) / len(closed_trades)
        else:
            win_rate = 0
        
        # 简化的年化收益率计算
        days = len(self.equity_curve)
        if days > 0:
            annual_return = total_return * (365 / days)
        else:
            annual_return = 0
        
        # 简化的夏普比率计算
        if len(equity_values) > 1:
            returns = np.diff(equity_values) / equity_values[:-1]
            if np.std(returns) > 0:
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        return {
            "total_return": round(total_return, 4),
            "annual_return": round(annual_return, 4),
            "max_drawdown": round(max_drawdown, 4),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "win_rate": round(win_rate, 2),
            "total_trades": len(closed_trades),
            "final_capital": round(self.current_capital, 2),
            "total_pnl": round(self.current_capital - self.initial_capital, 2)
        }
