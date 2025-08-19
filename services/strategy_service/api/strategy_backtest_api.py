"""
策略轻量回测API
集成到策略管理页面的简单回测功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import sys
import os
import requests

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from utils.logger import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/strategies", tags=["策略回测"])

# 专业回测服务配置
PROFESSIONAL_BACKTEST_URL = "http://localhost:8003"


# 请求模型
class QuickTestRequest(BaseModel):
    """快速测试请求"""
    test_days: Optional[int] = Field(7, description="测试天数")
    capital: Optional[int] = Field(100000, description="测试资金")
    max_position: Optional[int] = Field(5, description="最大仓位")


class BacktestProxyRequest(BaseModel):
    """回测代理请求"""
    backtest_type: str = Field(..., description="回测类型: quick/comprehensive/optimization")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="回测参数")


# API接口
@router.post("/{strategy_id}/quick_test")
async def quick_strategy_test(strategy_id: str, request: QuickTestRequest):
    """
    策略快速测试
    用于策略开发阶段的快速验证
    """
    try:
        logger.info(f"开始快速测试策略: {strategy_id}")
        
        # 获取策略信息
        strategy_info = await get_strategy_info(strategy_id)
        if not strategy_info:
            raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
        
        # 构建回测请求
        backtest_request = {
            "strategy_name": strategy_info.get("class_name", strategy_id),
            "strategy_setting": {
                "max_position": request.max_position,
                **strategy_info.get("parameters", {})
            },
            "days": request.test_days
        }
        
        # 调用专业回测服务
        try:
            response = requests.post(
                f"{PROFESSIONAL_BACKTEST_URL}/backtest/quick",
                json=backtest_request,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 简化结果，只返回关键指标
                simplified_result = {
                    "success": True,
                    "strategy_id": strategy_id,
                    "test_period": f"{request.test_days}天",
                    "capital": request.capital,
                    "key_metrics": extract_key_metrics(result.get("data", {})),
                    "recommendation": generate_recommendation(result.get("data", {})),
                    "timestamp": datetime.now().isoformat()
                }
                
                return simplified_result
            else:
                raise HTTPException(status_code=500, detail="专业回测服务调用失败")
                
        except requests.exceptions.ConnectionError:
            # 如果专业回测服务不可用，返回模拟结果
            logger.warning("专业回测服务不可用，返回模拟结果")
            return generate_mock_test_result(strategy_id, request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"快速测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"快速测试失败: {str(e)}")


@router.get("/{strategy_id}/backtest_history")
async def get_strategy_backtest_history(strategy_id: str):
    """获取策略回测历史"""
    try:
        # 从专业回测服务获取历史记录
        response = requests.get(
            f"{PROFESSIONAL_BACKTEST_URL}/backtest/results",
            params={"strategy_name": strategy_id},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", {}).get("results", {})
            
            # 整理历史记录
            history = []
            for key, result in results.items():
                if strategy_id in key:
                    history.append({
                        "test_id": key,
                        "timestamp": result.get("timestamp"),
                        "metrics": extract_key_metrics(result.get("basic_result", {})),
                        "settings": result.get("settings", {})
                    })
            
            return {
                "success": True,
                "strategy_id": strategy_id,
                "history": sorted(history, key=lambda x: x["timestamp"], reverse=True)[:10]  # 最近10次
            }
        else:
            return {"success": True, "strategy_id": strategy_id, "history": []}
            
    except Exception as e:
        logger.error(f"获取回测历史失败: {e}")
        return {"success": True, "strategy_id": strategy_id, "history": []}


@router.post("/{strategy_id}/backtest_proxy")
async def backtest_proxy(strategy_id: str, request: BacktestProxyRequest):
    """
    回测代理
    转发到专业回测服务进行深度分析
    """
    try:
        logger.info(f"代理回测请求: {strategy_id} - {request.backtest_type}")
        
        # 获取策略信息
        strategy_info = await get_strategy_info(strategy_id)
        if not strategy_info:
            raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
        
        # 根据回测类型构建请求
        if request.backtest_type == "quick":
            endpoint = "/backtest/quick"
            payload = {
                "strategy_name": strategy_info.get("class_name", strategy_id),
                "strategy_setting": {**strategy_info.get("parameters", {}), **request.parameters},
                "days": request.parameters.get("days", 30)
            }
        elif request.backtest_type == "comprehensive":
            endpoint = "/backtest/run"
            payload = {
                "strategy_name": strategy_info.get("class_name", strategy_id),
                "strategy_setting": {**strategy_info.get("parameters", {}), **request.parameters},
                **request.parameters
            }
        elif request.backtest_type == "optimization":
            endpoint = "/backtest/optimize"
            payload = {
                "strategy_name": strategy_info.get("class_name", strategy_id),
                **request.parameters
            }
        else:
            raise HTTPException(status_code=400, detail="不支持的回测类型")
        
        # 转发请求到专业回测服务
        response = requests.post(
            f"{PROFESSIONAL_BACKTEST_URL}{endpoint}",
            json=payload,
            timeout=300  # 5分钟超时
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "strategy_id": strategy_id,
                "backtest_type": request.backtest_type,
                "result": result,
                "professional_service_url": f"{PROFESSIONAL_BACKTEST_URL}/backtest/results"
            }
        else:
            raise HTTPException(status_code=500, detail="专业回测服务调用失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回测代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"回测代理失败: {str(e)}")


@router.post("/{strategy_id}/sync_to_backtest")
async def sync_strategy_to_backtest(strategy_id: str):
    """同步策略配置到专业回测服务"""
    try:
        logger.info(f"同步策略到回测服务: {strategy_id}")
        
        # 获取策略完整信息
        strategy_info = await get_strategy_info(strategy_id)
        if not strategy_info:
            raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
        
        # 发送到专业回测服务
        sync_data = {
            "strategy_id": strategy_id,
            "strategy_info": strategy_info,
            "sync_timestamp": datetime.now().isoformat()
        }
        
        try:
            response = requests.post(
                f"{PROFESSIONAL_BACKTEST_URL}/strategies/sync",
                json=sync_data,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "策略同步成功",
                    "strategy_id": strategy_id
                }
            else:
                logger.warning(f"策略同步失败: HTTP {response.status_code}")
                return {
                    "success": False,
                    "message": "策略同步失败，但不影响本地使用",
                    "strategy_id": strategy_id
                }
        except requests.exceptions.ConnectionError:
            logger.warning("专业回测服务不可用，跳过同步")
            return {
                "success": False,
                "message": "专业回测服务不可用，跳过同步",
                "strategy_id": strategy_id
            }
            
    except Exception as e:
        logger.error(f"策略同步失败: {e}")
        raise HTTPException(status_code=500, detail=f"策略同步失败: {str(e)}")


# 辅助函数
async def get_strategy_info(strategy_id: str) -> Optional[Dict[str, Any]]:
    """获取策略信息"""
    # 这里应该从策略管理系统获取策略信息
    # 暂时返回模拟数据
    strategy_mapping = {
        "large_order_following": {
            "class_name": "LargeOrderFollowing",
            "parameters": {"max_position": 10, "large_order_threshold": 3.0}
        },
        "vwap_deviation_reversion": {
            "class_name": "VWAPDeviationReversion", 
            "parameters": {"max_position": 8, "vwap_deviation_threshold": 0.002}
        },
        "double_ma": {
            "class_name": "DoubleMa",
            "parameters": {"max_position": 6, "fast_period": 5, "slow_period": 20}
        },
        "test": {
            "class_name": "Test",
            "parameters": {"max_position": 5}
        }
    }
    
    return strategy_mapping.get(strategy_id)


def extract_key_metrics(backtest_result: Dict[str, Any]) -> Dict[str, Any]:
    """提取关键指标"""
    return {
        "total_return": backtest_result.get("total_return", 0),
        "annual_return": backtest_result.get("annual_return", 0),
        "max_drawdown": backtest_result.get("max_drawdown", 0),
        "sharpe_ratio": backtest_result.get("sharpe_ratio", 0),
        "win_rate": backtest_result.get("win_rate", 0),
        "total_trades": backtest_result.get("total_trade_count", 0)
    }


def generate_recommendation(backtest_result: Dict[str, Any]) -> str:
    """生成推荐建议"""
    metrics = extract_key_metrics(backtest_result)
    
    total_return = metrics.get("total_return", 0)
    max_drawdown = abs(metrics.get("max_drawdown", 0))
    sharpe_ratio = metrics.get("sharpe_ratio", 0)
    win_rate = metrics.get("win_rate", 0)
    
    if total_return > 0.1 and sharpe_ratio > 1.5 and win_rate > 0.6:
        return "🎉 策略表现优秀，建议进行实盘测试"
    elif total_return > 0.05 and sharpe_ratio > 1.0:
        return "✅ 策略表现良好，可考虑参数优化"
    elif total_return > 0:
        return "⚠️ 策略有盈利但表现一般，建议优化"
    else:
        return "❌ 策略表现不佳，需要重新设计"


def generate_mock_test_result(strategy_id: str, request: QuickTestRequest) -> Dict[str, Any]:
    """生成模拟测试结果"""
    import random
    
    # 生成模拟数据
    total_return = random.uniform(-0.05, 0.15)
    max_drawdown = random.uniform(-0.1, -0.01)
    sharpe_ratio = random.uniform(0.5, 2.5)
    win_rate = random.uniform(0.4, 0.8)
    
    return {
        "success": True,
        "strategy_id": strategy_id,
        "test_period": f"{request.test_days}天",
        "capital": request.capital,
        "key_metrics": {
            "total_return": total_return,
            "annual_return": total_return * (365 / request.test_days),
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate,
            "total_trades": random.randint(5, 50)
        },
        "recommendation": "📊 模拟测试结果，请启动专业回测服务获取真实数据",
        "timestamp": datetime.now().isoformat(),
        "note": "专业回测服务不可用，这是模拟结果"
    }
