"""
策略管理服务
负责策略的生命周期管理、参数配置、回测等功能
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Dict, Any, List
import json
import os
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ARBIG策略管理服务",
    description="量化交易策略管理和回测服务",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 策略配置存储
STRATEGY_CONFIG_PATH = "config/strategies.json"
strategy_configs = {}
active_strategy = None
strategy_status = "STOPPED"

def load_strategy_configs():
    """加载策略配置"""
    global strategy_configs
    try:
        if os.path.exists(STRATEGY_CONFIG_PATH):
            with open(STRATEGY_CONFIG_PATH, 'r', encoding='utf-8') as f:
                strategy_configs = json.load(f)
        else:
            # 默认策略配置
            strategy_configs = {
                "shfe_quant": {
                    "name": "上期所量化策略",
                    "description": "基于技术指标的黄金期货量化交易策略",
                    "symbol": "au2510",
                    "params": {
                        "ma_short": 5,
                        "ma_long": 20,
                        "rsi_period": 14,
                        "rsi_overbought": 70,
                        "rsi_oversold": 30,
                        "stop_loss": 0.05,
                        "take_profit": 0.08,
                        "max_position": 1000,
                        "initial_capital": 100000
                    },
                    "enabled": True
                },
                "simple_shfe": {
                    "name": "简单SHFE策略",
                    "description": "简单的移动平均策略",
                    "symbol": "au2510",
                    "params": {
                        "ma_short": 10,
                        "ma_long": 30,
                        "initial_capital": 50000
                    },
                    "enabled": False
                }
            }
            save_strategy_configs()
    except Exception as e:
        logger.error(f"加载策略配置失败: {e}")
        strategy_configs = {}

def save_strategy_configs():
    """保存策略配置"""
    try:
        os.makedirs(os.path.dirname(STRATEGY_CONFIG_PATH), exist_ok=True)
        with open(STRATEGY_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(strategy_configs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存策略配置失败: {e}")

@app.on_event("startup")
async def startup_event():
    """服务启动事件"""
    logger.info("策略管理服务启动中...")
    load_strategy_configs()
    logger.info("策略管理服务启动完成")

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "ARBIG策略管理服务",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/strategies")
async def get_strategies():
    """获取所有策略列表"""
    return {
        "success": True,
        "data": {
            "strategies": strategy_configs,
            "active_strategy": active_strategy,
            "status": strategy_status
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/strategies/{strategy_name}")
async def get_strategy(strategy_name: str):
    """获取指定策略详情"""
    if strategy_name not in strategy_configs:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    return {
        "success": True,
        "data": strategy_configs[strategy_name],
        "timestamp": datetime.now().isoformat()
    }

@app.post("/strategies/{strategy_name}/params")
async def update_strategy_params(strategy_name: str, params: dict):
    """更新策略参数"""
    if strategy_name not in strategy_configs:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    try:
        # 更新参数
        strategy_configs[strategy_name]["params"].update(params)
        save_strategy_configs()
        
        return {
            "success": True,
            "message": "策略参数更新成功",
            "data": strategy_configs[strategy_name],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"参数更新失败: {str(e)}")

@app.post("/strategies/{strategy_name}/start")
async def start_strategy(strategy_name: str):
    """启动策略"""
    global active_strategy, strategy_status
    
    if strategy_name not in strategy_configs:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    if strategy_status == "RUNNING":
        raise HTTPException(status_code=400, detail=f"策略 {active_strategy} 正在运行，请先停止")
    
    try:
        active_strategy = strategy_name
        strategy_status = "RUNNING"
        
        logger.info(f"启动策略: {strategy_name}")
        
        return {
            "success": True,
            "message": f"策略 {strategy_name} 启动成功",
            "data": {
                "active_strategy": active_strategy,
                "status": strategy_status
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        strategy_status = "STOPPED"
        active_strategy = None
        raise HTTPException(status_code=500, detail=f"策略启动失败: {str(e)}")

@app.post("/strategies/{strategy_name}/stop")
async def stop_strategy(strategy_name: str):
    """停止策略"""
    global active_strategy, strategy_status
    
    if active_strategy != strategy_name:
        raise HTTPException(status_code=400, detail="该策略未在运行")
    
    try:
        logger.info(f"停止策略: {strategy_name}")
        
        active_strategy = None
        strategy_status = "STOPPED"
        
        return {
            "success": True,
            "message": f"策略 {strategy_name} 停止成功",
            "data": {
                "active_strategy": active_strategy,
                "status": strategy_status
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"策略停止失败: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
