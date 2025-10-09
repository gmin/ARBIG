"""
ARBIG专业回测引擎
基于vnpy BacktestingEngine的专业回测系统
支持策略回测、参数优化、性能分析
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Type
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

try:
    # 使用检测到的正确导入路径
    from vnpy_ctastrategy.backtesting import BacktestingEngine
    from vnpy_ctastrategy.template import CtaTemplate
    from vnpy.trader.constant import Interval, Exchange
    from vnpy.trader.object import BarData
    from vnpy.trader.utility import load_json, save_json

    # 尝试导入SQLite数据库模块
    try:
        from vnpy_sqlite import SqliteDatabase
        SQLITE_AVAILABLE = True
        print("✅ vnpy_sqlite模块导入成功")
    except ImportError:
        SqliteDatabase = None
        SQLITE_AVAILABLE = False
        print("⚠️ vnpy_sqlite模块未安装，将使用默认数据源")

    print("✅ vnpy回测模块导入成功")

except ImportError as e:
    print(f"⚠️ vnpy回测模块导入失败: {e}")
    print("正在尝试替代方案...")
    BacktestingEngine = None
    CtaTemplate = None
    SQLITE_AVAILABLE = False

from utils.logger import get_logger
from services.strategy_service.core.cta_template import ARBIGCtaTemplate

logger = get_logger(__name__)


class ARBIGBacktestEngine:
    """
    ARBIG专业回测引擎
    
    功能特点:
    1. 基于vnpy专业回测引擎
    2. 支持多策略并行回测
    3. 完整的性能分析报告
    4. 参数优化功能
    5. 风险指标计算
    """
    
    def __init__(self):
        """初始化回测引擎"""
        if BacktestingEngine is None:
            raise ImportError("vnpy_ctastrategy未安装，无法使用专业回测功能")
        
        self.engine = BacktestingEngine()
        self.results = {}
        self.strategies = {}
        
        # 默认回测参数
        self.default_settings = {
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 12, 31),
            "symbol": "au2512.SHFE",
            "interval": Interval.MINUTE,
            "rate": 2/10000,        # 手续费率 0.02%
            "slippage": 0.2,        # 滑点 0.2元
            "size": 1000,           # 合约乘数
            "pricetick": 0.02,      # 最小价格变动
            "capital": 1000000      # 初始资金100万
        }
        
        logger.info("ARBIG专业回测引擎初始化完成")
    
    def setup_backtest(self, 
                      start_date: datetime = None,
                      end_date: datetime = None,
                      symbol: str = "au2512.SHFE",
                      interval: Interval = Interval.MINUTE,
                      rate: float = 2/10000,
                      slippage: float = 0.2,
                      size: int = 1000,
                      pricetick: float = 0.02,
                      capital: int = 1000000):
        """
        设置回测参数
        
        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期
            symbol: 交易品种
            interval: 数据周期
            rate: 手续费率
            slippage: 滑点
            size: 合约乘数
            pricetick: 最小价格变动
            capital: 初始资金
        """
        try:
            # 使用默认值
            if start_date is None:
                start_date = self.default_settings["start_date"]
            if end_date is None:
                end_date = self.default_settings["end_date"]
            
            # 设置回测参数
            self.engine.set_parameters(
                vt_symbol=symbol,
                interval=interval,
                start=start_date,
                end=end_date,
                rate=rate,
                slippage=slippage,
                size=size,
                pricetick=pricetick,
                capital=capital
            )
            
            # 保存设置
            self.current_settings = {
                "start_date": start_date,
                "end_date": end_date,
                "symbol": symbol,
                "interval": interval,
                "rate": rate,
                "slippage": slippage,
                "size": size,
                "pricetick": pricetick,
                "capital": capital
            }
            
            logger.info(f"回测参数设置完成: {symbol} {start_date} - {end_date}")
            return True
            
        except Exception as e:
            logger.error(f"设置回测参数失败: {e}")
            return False
    
    def add_strategy(self, strategy_class: Type, strategy_setting: Dict[str, Any], strategy_name: str = None):
        """
        添加策略到回测引擎
        
        Args:
            strategy_class: 策略类
            strategy_setting: 策略参数
            strategy_name: 策略名称
        """
        try:
            if strategy_name is None:
                strategy_name = strategy_class.__name__
            
            # 检查策略类是否兼容
            if not issubclass(strategy_class, (CtaTemplate, ARBIGCtaTemplate)):
                logger.warning(f"策略 {strategy_name} 可能不兼容vnpy回测引擎")
            
            # 添加策略
            self.engine.add_strategy(strategy_class, strategy_setting)
            self.strategies[strategy_name] = {
                "class": strategy_class,
                "setting": strategy_setting.copy()
            }
            
            logger.info(f"策略添加成功: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加策略失败: {e}")
            return False
    
    def load_data(self, data_source: str = "vnpy"):
        """
        加载历史数据
        
        Args:
            data_source: 数据源 ("vnpy", "file", "database")
        """
        try:
            if data_source == "vnpy":
                # 使用vnpy内置数据源
                logger.info("使用vnpy内置数据源加载历史数据...")
                self.engine.load_data()
                
            elif data_source == "file":
                # 从文件加载数据
                logger.info("从文件加载历史数据...")
                # TODO: 实现文件数据加载
                pass
                
            elif data_source == "database":
                # 从数据库加载数据
                logger.info("从数据库加载历史数据...")
                # TODO: 实现数据库数据加载
                pass
            
            logger.info("历史数据加载完成")
            return True
            
        except Exception as e:
            logger.error(f"加载历史数据失败: {e}")
            return False
    
    def run_backtesting(self) -> Dict[str, Any]:
        """
        运行回测
        
        Returns:
            回测结果字典
        """
        try:
            logger.info("开始运行回测...")
            
            # 运行回测
            self.engine.run_backtesting()
            
            # 计算结果
            result = self.engine.calculate_result()
            
            # 计算统计指标
            statistics = self.engine.calculate_statistics()
            
            # 整合结果
            backtest_result = {
                "basic_result": result,
                "statistics": statistics,
                "settings": self.current_settings.copy(),
                "strategies": self.strategies.copy(),
                "timestamp": datetime.now().isoformat()
            }
            
            # 保存结果
            self.results[datetime.now().strftime("%Y%m%d_%H%M%S")] = backtest_result
            
            logger.info("回测完成")
            return backtest_result
            
        except Exception as e:
            logger.error(f"回测运行失败: {e}")
            return {"error": str(e)}
    
    def optimize_parameters(self, 
                          strategy_class: Type,
                          optimization_setting: Dict[str, Any],
                          target_name: str = "sharpe_ratio") -> Dict[str, Any]:
        """
        参数优化
        
        Args:
            strategy_class: 策略类
            optimization_setting: 优化参数设置
            target_name: 优化目标 (sharpe_ratio, total_return, max_drawdown等)
        
        Returns:
            优化结果
        """
        try:
            logger.info(f"开始参数优化，目标: {target_name}")
            
            # 使用vnpy的参数优化功能
            optimization_result = self.engine.run_optimization(
                optimization_setting=optimization_setting,
                target_name=target_name
            )
            
            logger.info("参数优化完成")
            return optimization_result
            
        except Exception as e:
            logger.error(f"参数优化失败: {e}")
            return {"error": str(e)}
    
    def generate_report(self, result: Dict[str, Any]) -> str:
        """
        生成回测报告
        
        Args:
            result: 回测结果
            
        Returns:
            报告内容
        """
        try:
            if "error" in result:
                return f"回测失败: {result['error']}"
            
            basic = result.get("basic_result", {})
            stats = result.get("statistics", {})
            settings = result.get("settings", {})
            
            report = f"""
# ARBIG策略回测报告

## 回测设置
- 交易品种: {settings.get('symbol', 'N/A')}
- 回测期间: {settings.get('start_date', 'N/A')} - {settings.get('end_date', 'N/A')}
- 初始资金: {settings.get('capital', 'N/A'):,}元
- 手续费率: {settings.get('rate', 'N/A'):.4%}
- 滑点设置: {settings.get('slippage', 'N/A')}元

## 基础指标
- 总收益率: {basic.get('total_return', 0):.2%}
- 年化收益率: {basic.get('annual_return', 0):.2%}
- 最大回撤: {basic.get('max_drawdown', 0):.2%}
- 夏普比率: {basic.get('sharpe_ratio', 0):.2f}

## 交易统计
- 总交易次数: {basic.get('total_trade_count', 0)}
- 盈利交易: {basic.get('winning_trade_count', 0)}
- 亏损交易: {basic.get('losing_trade_count', 0)}
- 胜率: {basic.get('win_rate', 0):.2%}
- 盈亏比: {basic.get('profit_loss_ratio', 0):.2f}

## 风险指标
- 波动率: {stats.get('volatility', 0):.2%}
- 卡尔马比率: {stats.get('calmar_ratio', 0):.2f}
- 索提诺比率: {stats.get('sortino_ratio', 0):.2f}

---
报告生成时间: {result.get('timestamp', 'N/A')}
            """
            
            return report.strip()
            
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            return f"报告生成失败: {e}"
    
    def save_results(self, filename: str = None):
        """保存回测结果到文件"""
        try:
            if filename is None:
                filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            save_json(filename, self.results)
            logger.info(f"回测结果已保存: {filename}")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
    
    def load_results(self, filename: str):
        """从文件加载回测结果"""
        try:
            self.results = load_json(filename)
            logger.info(f"回测结果已加载: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"加载结果失败: {e}")
            return False
