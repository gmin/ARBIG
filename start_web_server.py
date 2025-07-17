#!/usr/bin/env python3
"""
简单的Web服务器启动脚本
解决导入问题并直接启动Web服务
"""

import sys
import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 添加项目根目录到Python路径
sys.path.append('/root/ARBIG')

# 创建FastAPI应用
app = FastAPI(
    title="ARBIG Web管理系统",
    description="ARBIG量化交易系统Web管理界面",
    version="1.0.0"
)

# 挂载静态文件
static_path = "/root/ARBIG/web_admin/static"
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    print(f"✅ 静态文件目录已挂载: {static_path}")
else:
    print(f"❌ 静态文件目录不存在: {static_path}")

@app.get("/")
async def read_root():
    """主页"""
    index_file = "/root/ARBIG/web_admin/static/index.html"
    if os.path.exists(index_file):
        return FileResponse(index_file)
    else:
        return {"message": "ARBIG Web管理系统", "status": "running", "error": f"index.html not found at {index_file}"}

@app.get("/strategy_monitor.html")
async def strategy_monitor():
    """策略监控页面"""
    monitor_file = "/root/ARBIG/web_admin/static/strategy_monitor.html"
    if os.path.exists(monitor_file):
        return FileResponse(monitor_file)
    else:
        return {"error": f"strategy_monitor.html not found at {monitor_file}"}

@app.get("/test.html")
async def test_page():
    """测试页面"""
    test_file = "/root/ARBIG/web_admin/static/test.html"
    if os.path.exists(test_file):
        return FileResponse(test_file)
    else:
        return {"error": f"test.html not found at {test_file}"}

@app.get("/api/v1/system/status")
async def system_status():
    """系统状态API"""
    return {
        "success": True,
        "message": "系统状态获取成功",
        "data": {
            "system_status": "running",
            "running_mode": "DEMO_MODE",
            "start_time": "2025-07-16T16:00:00",
            "uptime": "0h 30m",
            "services_summary": {
                "total": 3,
                "running": 3,
                "stopped": 0,
                "error": 0
            },
            "version": "1.0.0"
        },
        "timestamp": "2025-07-16T16:30:00",
        "request_id": "demo-request-001"
    }

@app.get("/api/v1/strategies/shfe_quant/params")
async def get_strategy_params():
    """获取策略参数"""
    return {
        "success": True,
        "message": "获取策略参数成功",
        "data": {
            "ma_short": 5,
            "ma_long": 20,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "stop_loss": 0.05,
            "take_profit": 0.08,
            "position_size": 1,
            "max_position": 5,
            "risk_factor": 0.02,
            "add_interval": 50,
            "position_mode": "fixed",
            "position_multiplier": 1.0,
            "win_rate": 0.6,
            "avg_win": 1.5,
            "avg_loss": 1.0,
            "martingale_multiplier": 2.0
        },
        "timestamp": "2025-07-16T16:30:00",
        "request_id": "demo-request-002"
    }

@app.post("/api/v1/strategies/shfe_quant/params")
async def update_strategy_params(params: dict):
    """更新策略参数"""
    return {
        "success": True,
        "message": "策略参数更新成功（演示模式）",
        "data": {
            "updated_params": params
        },
        "timestamp": "2025-07-16T16:30:00",
        "request_id": "demo-request-003"
    }

@app.post("/api/v1/strategies/shfe_quant/backtest")
async def run_backtest(params: dict):
    """运行回测"""
    return {
        "success": True,
        "message": "回测完成（演示模式）",
        "data": {
            "total_return": 0.0205,
            "annual_return": 0.0796,
            "max_drawdown": 0.0245,
            "sharpe_ratio": 2.19,
            "win_rate": 0.48,
            "total_trades": 180,
            "start_date": params.get("start_date", "2024-01-01"),
            "end_date": params.get("end_date", "2024-12-31"),
            "initial_capital": params.get("initial_capital", 100000)
        },
        "timestamp": "2025-07-16T16:30:00",
        "request_id": "demo-request-004"
    }

@app.get("/api/v1/strategies/shfe_quant/triggers")
async def get_strategy_triggers():
    """获取策略触发记录"""
    import time
    import random
    
    # 生成一些模拟触发记录
    triggers = []
    for i in range(5):
        triggers.append({
            "id": f"trigger_{i+1}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": random.choice(["BUY", "SELL", "CLOSE"]),
            "price": round(450 + random.uniform(-10, 10), 2),
            "condition": "MA交叉 + RSI确认",
            "status": "success",
            "position_mode": "fixed",
            "position_size": 1
        })
    
    return {
        "success": True,
        "data": triggers,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "request_id": "demo-request-005"
    }

@app.get("/api/v1/strategies/shfe_quant/performance")
async def get_strategy_performance():
    """获取策略性能数据"""
    import random
    
    return {
        "success": True,
        "data": {
            "total_pnl": round(random.uniform(1000, 5000), 2),
            "today_pnl": round(random.uniform(-500, 500), 2),
            "position": random.randint(0, 3),
            "win_rate": round(random.uniform(0.5, 0.8), 2),
            "total_trades": random.randint(50, 200),
            "avg_profit": round(random.uniform(100, 300), 2)
        },
        "timestamp": "2025-07-16T16:30:00",
        "request_id": "demo-request-006"
    }

if __name__ == "__main__":
    print("🚀 启动ARBIG Web服务器...")
    print("📁 检查静态文件...")
    
    # 检查关键文件
    files_to_check = [
        "/root/ARBIG/web_admin/static/index.html",
        "/root/ARBIG/web_admin/static/strategy_monitor.html"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
    
    print("\n🌐 启动服务器...")
    print("访问地址: http://您的转发地址:8000")
    print("策略监控: http://您的转发地址:8000/strategy_monitor.html?strategy=shfe_quant")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
