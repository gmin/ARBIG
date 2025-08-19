"""
回测管理器
统一管理策略回测、参数优化、结果分析
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Type
import asyncio
import json

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

try:
    from vnpy.trader.constant import Interval
except ImportError:
    Interval = None

from .backtest_engine import ARBIGBacktestEngine
from .strategy_adapter import get_adapted_strategies, create_vnpy_compatible_strategy
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from utils.logger import get_logger

logger = get_logger(__name__)


class BacktestManager:
    """
    回测管理器
    
    功能:
    1. 统一管理所有策略的回测
    2. 批量回测和对比分析
    3. 参数优化管理
    4. 回测结果存储和查询
    """
    
    def __init__(self):
        """初始化回测管理器"""
        self.engine = ARBIGBacktestEngine()
        self.adapted_strategies = {}
        self.backtest_results = {}
        
        # 加载适配策略
        self._load_adapted_strategies()
        
        logger.info("回测管理器初始化完成")
    
    def _load_adapted_strategies(self):
        """加载适配后的策略"""
        try:
            self.adapted_strategies = get_adapted_strategies()
            logger.info(f"加载了 {len(self.adapted_strategies)} 个适配策略")
        except Exception as e:
            logger.error(f"加载适配策略失败: {e}")
    
    async def run_single_backtest(self, 
                                 strategy_name: str,
                                 strategy_setting: Dict[str, Any],
                                 backtest_setting: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        运行单个策略回测
        
        Args:
            strategy_name: 策略名称
            strategy_setting: 策略参数
            backtest_setting: 回测设置
            
        Returns:
            回测结果
        """
        try:
            logger.info(f"开始回测策略: {strategy_name}")
            
            # 检查策略是否存在
            if strategy_name not in self.adapted_strategies:
                raise ValueError(f"策略 {strategy_name} 不存在")
            
            # 设置回测参数
            if backtest_setting:
                self.engine.setup_backtest(**backtest_setting)
            else:
                # 使用默认设置
                self.engine.setup_backtest()
            
            # 添加策略
            strategy_class = self.adapted_strategies[strategy_name]
            self.engine.add_strategy(strategy_class, strategy_setting, strategy_name)
            
            # 加载数据
            self.engine.load_data()
            
            # 运行回测
            result = self.engine.run_backtesting()
            
            # 保存结果
            result_key = f"{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.backtest_results[result_key] = result
            
            logger.info(f"策略 {strategy_name} 回测完成")
            return result
            
        except Exception as e:
            logger.error(f"策略 {strategy_name} 回测失败: {e}")
            return {"error": str(e), "strategy": strategy_name}
    
    async def run_batch_backtest(self, 
                                strategies_config: List[Dict[str, Any]],
                                backtest_setting: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        批量回测多个策略
        
        Args:
            strategies_config: 策略配置列表
            backtest_setting: 回测设置
            
        Returns:
            批量回测结果
        """
        try:
            logger.info(f"开始批量回测 {len(strategies_config)} 个策略")
            
            batch_results = {}
            
            for config in strategies_config:
                strategy_name = config.get("strategy_name")
                strategy_setting = config.get("strategy_setting", {})
                
                if not strategy_name:
                    logger.warning("策略配置缺少strategy_name，跳过")
                    continue
                
                # 运行单个回测
                result = await self.run_single_backtest(
                    strategy_name, strategy_setting, backtest_setting
                )
                
                batch_results[strategy_name] = result
                
                # 添加延迟避免资源占用过高
                await asyncio.sleep(0.1)
            
            # 生成对比分析
            comparison = self._generate_comparison_report(batch_results)
            
            final_result = {
                "individual_results": batch_results,
                "comparison": comparison,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("批量回测完成")
            return final_result
            
        except Exception as e:
            logger.error(f"批量回测失败: {e}")
            return {"error": str(e)}
    
    def _generate_comparison_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成策略对比报告"""
        try:
            comparison = {
                "summary": {},
                "rankings": {},
                "metrics": {}
            }
            
            valid_results = {k: v for k, v in results.items() if "error" not in v}
            
            if not valid_results:
                return {"error": "没有有效的回测结果"}
            
            # 提取关键指标
            metrics = ["total_return", "annual_return", "max_drawdown", "sharpe_ratio", "win_rate"]
            
            for metric in metrics:
                metric_values = {}
                for strategy_name, result in valid_results.items():
                    basic_result = result.get("basic_result", {})
                    if metric in basic_result:
                        metric_values[strategy_name] = basic_result[metric]
                
                if metric_values:
                    # 排序
                    if metric == "max_drawdown":
                        # 回撤越小越好
                        sorted_strategies = sorted(metric_values.items(), key=lambda x: abs(x[1]))
                    else:
                        # 其他指标越大越好
                        sorted_strategies = sorted(metric_values.items(), key=lambda x: x[1], reverse=True)
                    
                    comparison["rankings"][metric] = sorted_strategies
                    comparison["metrics"][metric] = metric_values
            
            # 综合评分
            comparison["summary"] = self._calculate_overall_score(valid_results)
            
            return comparison
            
        except Exception as e:
            logger.error(f"生成对比报告失败: {e}")
            return {"error": str(e)}
    
    def _calculate_overall_score(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """计算综合评分"""
        try:
            scores = {}
            
            for strategy_name, result in results.items():
                basic_result = result.get("basic_result", {})
                
                # 简单的评分算法
                score = 0
                
                # 收益率权重 40%
                annual_return = basic_result.get("annual_return", 0)
                score += annual_return * 0.4
                
                # 夏普比率权重 30%
                sharpe_ratio = basic_result.get("sharpe_ratio", 0)
                score += sharpe_ratio * 0.3
                
                # 最大回撤权重 20% (负向指标)
                max_drawdown = basic_result.get("max_drawdown", 0)
                score -= abs(max_drawdown) * 0.2
                
                # 胜率权重 10%
                win_rate = basic_result.get("win_rate", 0)
                score += win_rate * 0.1
                
                scores[strategy_name] = round(score, 4)
            
            # 排序
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "scores": scores,
                "ranking": sorted_scores,
                "best_strategy": sorted_scores[0][0] if sorted_scores else None
            }
            
        except Exception as e:
            logger.error(f"计算综合评分失败: {e}")
            return {"error": str(e)}
    
    async def optimize_strategy_parameters(self, 
                                         strategy_name: str,
                                         optimization_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化策略参数
        
        Args:
            strategy_name: 策略名称
            optimization_config: 优化配置
            
        Returns:
            优化结果
        """
        try:
            logger.info(f"开始优化策略参数: {strategy_name}")
            
            if strategy_name not in self.adapted_strategies:
                raise ValueError(f"策略 {strategy_name} 不存在")
            
            strategy_class = self.adapted_strategies[strategy_name]
            
            # 运行参数优化
            result = self.engine.optimize_parameters(
                strategy_class=strategy_class,
                optimization_setting=optimization_config.get("optimization_setting", {}),
                target_name=optimization_config.get("target_name", "sharpe_ratio")
            )
            
            logger.info(f"策略 {strategy_name} 参数优化完成")
            return result
            
        except Exception as e:
            logger.error(f"策略 {strategy_name} 参数优化失败: {e}")
            return {"error": str(e)}
    
    def get_backtest_results(self, strategy_name: str = None) -> Dict[str, Any]:
        """获取回测结果"""
        if strategy_name:
            # 返回特定策略的结果
            filtered_results = {k: v for k, v in self.backtest_results.items() 
                              if k.startswith(strategy_name)}
            return filtered_results
        else:
            # 返回所有结果
            return self.backtest_results.copy()
    
    def generate_report(self, result_key: str) -> str:
        """生成回测报告"""
        if result_key not in self.backtest_results:
            return f"回测结果 {result_key} 不存在"
        
        result = self.backtest_results[result_key]
        return self.engine.generate_report(result)
    
    def save_results(self, filename: str = None):
        """保存所有回测结果"""
        try:
            if filename is None:
                filename = f"batch_backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.backtest_results, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"回测结果已保存: {filename}")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
    
    def get_available_strategies(self) -> List[str]:
        """获取可用的策略列表"""
        return list(self.adapted_strategies.keys())


# 便捷函数
async def quick_backtest(strategy_name: str, 
                        strategy_setting: Dict[str, Any] = None,
                        days: int = 30) -> Dict[str, Any]:
    """
    快速回测函数
    
    Args:
        strategy_name: 策略名称
        strategy_setting: 策略参数
        days: 回测天数
        
    Returns:
        回测结果
    """
    manager = BacktestManager()
    
    # 设置回测时间范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    backtest_setting = {
        "start_date": start_date,
        "end_date": end_date,
        "capital": 1000000  # 100万初始资金
    }
    
    if strategy_setting is None:
        strategy_setting = {}
    
    return await manager.run_single_backtest(
        strategy_name, strategy_setting, backtest_setting
    )


if __name__ == "__main__":
    # 测试回测管理器
    async def test_backtest():
        manager = BacktestManager()
        
        print("可用策略:")
        for strategy in manager.get_available_strategies():
            print(f"  - {strategy}")
        
        # 快速回测示例
        if manager.get_available_strategies():
            strategy_name = manager.get_available_strategies()[0]
            result = await quick_backtest(strategy_name, {}, 7)  # 回测7天
            print(f"\n{strategy_name} 回测结果:")
            print(manager.engine.generate_report(result))
    
    asyncio.run(test_backtest())
