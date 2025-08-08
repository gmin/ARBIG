"""
交易操作API接口
提供平仓、策略控制等交易操作功能
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from shared.database.connection import get_db_manager
from shared.models.trading import PositionInfo, StrategyTrigger, ExecutionResult, SignalType
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/trading", tags=["trading_operations"])

@router.post("/close_position")
async def close_position(request: Dict[str, Any]):
    """
    平仓操作
    
    Args:
        request: {
            "position_id": int,
            "account_id": str,
            "symbol": str,
            "direction": str,  # "buy" or "sell"
            "volume": int
        }
    """
    try:
        position_id = request.get("position_id")
        account_id = request.get("account_id")
        symbol = request.get("symbol")
        direction = request.get("direction")
        volume = request.get("volume")
        
        if not all([position_id, account_id, symbol, direction, volume]):
            raise HTTPException(status_code=400, detail="缺少必要参数")
        
        # 验证持仓是否存在
        db_manager = get_db_manager()
        position_result = await db_manager.execute_query("""
            SELECT id, account_id, symbol, direction, volume, avg_price
            FROM positions
            WHERE id = %s AND account_id = %s AND volume > 0
        """, (position_id, account_id))
        
        if not position_result:
            raise HTTPException(status_code=404, detail="持仓不存在或已平仓")
        
        position = position_result[0]
        
        # 生成订单ID
        order_id = f"CLOSE_{uuid.uuid4().hex[:8].upper()}"
        
        # 记录策略触发（平仓操作）
        signal_type = "close_long" if position['direction'] == 'long' else "close_short"
        trigger_id = await db_manager.execute_insert("""
            INSERT INTO strategy_triggers
            (strategy_name, trigger_time, trigger_condition, trigger_price,
             signal_type, action_type, execution_result, order_id, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "ManualClose",
            datetime.now(),
            f"手动平仓操作 - 持仓ID: {position_id}",
            position['avg_price'],
            signal_type,
            "close",  # action_type使用'close'
            "success",
            order_id,
            volume
        ))
        
        # 先创建订单记录
        order_time = datetime.now()
        await db_manager.execute_insert("""
            INSERT INTO orders
            (order_id, account_id, symbol, direction, volume, price, order_type, status, order_time, create_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            order_id,
            account_id,
            symbol,
            direction,
            volume,
            position['avg_price'],
            "market",
            "filled",
            order_time,
            order_time
        ))

        # 模拟订单执行（实际应该调用CTP接口）
        # 这里我们直接更新持仓数量
        await db_manager.execute_update("""
            UPDATE positions
            SET volume = volume - %s, update_time = %s
            WHERE id = %s
        """, (volume, datetime.now(), position_id))

        # 插入交易记录
        trade_id = f"TRADE_{uuid.uuid4().hex[:8].upper()}"
        await db_manager.execute_insert("""
            INSERT INTO trades
            (trade_id, order_id, account_id, symbol, direction, volume, price, trade_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            trade_id,
            order_id,
            account_id,
            symbol,
            direction,
            volume,
            position['avg_price'],  # 使用成本价作为平仓价格（简化处理）
            datetime.now()
        ))
        
        logger.info(f"平仓操作成功: 持仓ID={position_id}, 订单ID={order_id}, 数量={volume}")
        
        return {
            "success": True,
            "message": "平仓指令执行成功",
            "order_id": order_id,
            "trade_id": trade_id,
            "trigger_id": trigger_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"平仓操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"平仓操作失败: {str(e)}")

# 策略管理API - 使用统一策略管理器，消除冗余代码
from services.trading_service.core.unified_strategy_manager import get_unified_strategy_manager

@router.get("/strategy/status")
async def get_strategy_status():
    """获取策略运行状态 - 使用统一管理器"""
    try:
        manager = get_unified_strategy_manager()
        return await manager.get_strategy_status()
    except Exception as e:
        logger.error(f"获取策略状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略状态失败: {str(e)}")

@router.post("/strategy/{strategy_name}/start")
async def start_strategy(strategy_name: str):
    """启动策略 - 使用统一管理器"""
    try:
        manager = get_unified_strategy_manager()
        result = await manager.start_strategy(strategy_name)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动策略失败: {str(e)}")

@router.post("/strategy/{strategy_name}/stop")
async def stop_strategy(strategy_name: str):
    """停止策略 - 使用统一管理器"""
    try:
        manager = get_unified_strategy_manager()
        result = await manager.stop_strategy(strategy_name)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止策略失败: {str(e)}")

@router.post("/emergency_stop")
async def emergency_stop():
    """系统紧急停止 - 使用统一管理器"""
    try:
        manager = get_unified_strategy_manager()
        result = await manager.emergency_stop_all()

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])

        return result
    except Exception as e:
        logger.error(f"系统紧急停止失败: {e}")
        raise HTTPException(status_code=500, detail=f"系统紧急停止失败: {str(e)}")

@router.get("/strategy/triggers")
async def get_strategy_triggers(limit: int = 50, strategy_name: Optional[str] = None):
    """获取策略触发记录 - 使用统一管理器"""
    try:
        manager = get_unified_strategy_manager()
        return await manager.get_strategy_triggers(limit, strategy_name)
    except Exception as e:
        logger.error(f"获取策略触发记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略触发记录失败: {str(e)}")
