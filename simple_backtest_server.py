#!/usr/bin/env python3
"""
简化的回测服务器
用于测试回测API是否可用
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="ARBIG简化回测服务", version="1.0.0")

@app.get("/")
async def root():
    """根路径"""
    return {"message": "ARBIG简化回测服务运行中", "status": "ok"}

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "service": "simple_backtest"}

@app.get("/backtest/health")
async def backtest_health():
    """回测健康检查"""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "message": "简化回测服务运行正常"
        }
    }

@app.get("/backtest/strategies")
async def get_strategies():
    """获取策略列表"""
    return {
        "success": True,
        "data": {
            "strategies": ["TestStrategy", "SimpleStrategy"],
            "count": 2
        },
        "message": "获取策略列表成功"
    }

@app.post("/backtest/quick")
async def quick_backtest(request: dict):
    """快速回测"""
    return {
        "success": True,
        "data": {
            "strategy_name": request.get("strategy_name", "unknown"),
            "result": "模拟回测结果",
            "total_return": 0.05,
            "max_drawdown": -0.02,
            "message": "这是模拟的回测结果"
        },
        "message": "快速回测完成"
    }

if __name__ == "__main__":
    print("🚀 启动简化回测服务...")
    print("📍 服务地址: http://localhost:8003")
    print("📍 健康检查: http://localhost:8003/backtest/health")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8003,  # 使用不同的端口避免冲突
            log_level="info"
        )
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
