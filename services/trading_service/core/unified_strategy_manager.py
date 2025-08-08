"""
统一策略管理器
整合所有策略管理功能，消除冗余代码
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import importlib
import threading

from shared.database.connection import get_db_manager
from shared.models.trading import StrategyConfig, StrategyTrigger
from utils.logger import get_logger

logger = get_logger(__name__)

class UnifiedStrategyManager:
    """统一策略管理器 - 消除冗余，统一管理所有策略"""
    
    def __init__(self):
        """初始化策略管理器"""
        self.strategies: Dict[str, Any] = {}  # 运行中的策略实例
        self.strategy_configs: Dict[str, Dict] = {}  # 策略配置缓存
        self.running = False
        self._lock = threading.RLock()
        
        # 策略类映射 - 统一管理所有策略类型
        self.strategy_classes = {
            'ArbitrageStrategy': 'core.strategy.ArbitrageStrategy',
            'SHFEQuantStrategy': 'strategies.shfe_quant.SHFEQuantStrategy',
            # 未来可以轻松添加新策略
        }
    
    async def initialize(self) -> bool:
        """初始化策略管理器"""
        try:
            await self._load_strategy_configs()
            self.running = True
            logger.info("✅ 统一策略管理器初始化成功")
            return True
        except Exception as e:
            logger.error(f"❌ 策略管理器初始化失败: {e}")
            return False
    
    async def shutdown(self):
        """关闭策略管理器"""
        self.running = False
        
        # 停止所有运行中的策略
        for strategy_name in list(self.strategies.keys()):
            await self.stop_strategy(strategy_name)
        
        logger.info("✅ 统一策略管理器已关闭")
    
    async def _load_strategy_configs(self):
        """从数据库加载策略配置"""
        try:
            db_manager = get_db_manager()
            configs = await db_manager.execute_query("""
                SELECT strategy_name, strategy_class, config_data, is_active, description
                FROM strategy_configs
                ORDER BY strategy_name
            """)
            
            self.strategy_configs.clear()
            for config in configs:
                self.strategy_configs[config['strategy_name']] = {
                    'strategy_class': config['strategy_class'],
                    'config_data': config['config_data'],
                    'is_active': bool(config['is_active']),
                    'description': config['description']
                }
            
            logger.info(f"加载了 {len(self.strategy_configs)} 个策略配置")
            
        except Exception as e:
            logger.error(f"加载策略配置失败: {e}")
            # 使用默认配置
            self.strategy_configs = {
                'ArbitrageStrategy': {
                    'strategy_class': 'ArbitrageStrategy',
                    'config_data': {'symbol': 'au2509', 'max_position': 1000},
                    'is_active': False,
                    'description': '套利策略'
                }
            }
    
    async def get_strategy_status(self) -> List[Dict[str, Any]]:
        """获取所有策略状态 - 统一接口"""
        try:
            db_manager = get_db_manager()
            strategy_status = []
            
            for strategy_name, config in self.strategy_configs.items():
                # 获取今日触发统计
                today_stats = await db_manager.execute_query("""
                    SELECT COUNT(*) as total_count,
                           SUM(CASE WHEN execution_result = 'success' THEN 1 ELSE 0 END) as success_count
                    FROM strategy_triggers
                    WHERE strategy_name = %s AND DATE(trigger_time) = CURDATE()
                """, (strategy_name,))
                
                stats = today_stats[0] if today_stats else {'total_count': 0, 'success_count': 0}
                total_count = stats['total_count'] or 0
                success_count = stats['success_count'] or 0
                
                # 获取最后触发时间
                last_trigger = await db_manager.execute_query("""
                    SELECT trigger_time
                    FROM strategy_triggers
                    WHERE strategy_name = %s
                    ORDER BY trigger_time DESC
                    LIMIT 1
                """, (strategy_name,))
                
                strategy_status.append({
                    'strategy_name': strategy_name,
                    'is_active': strategy_name in self.strategies,
                    'description': config.get('description', ''),
                    'trigger_count_today': total_count,
                    'success_count_today': success_count,
                    'success_rate': success_count / max(total_count, 1),
                    'last_trigger_time': last_trigger[0]['trigger_time'] if last_trigger else None,
                    'update_time': datetime.now()
                })
            
            return strategy_status
            
        except Exception as e:
            logger.error(f"获取策略状态失败: {e}")
            return []
    
    async def start_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """启动策略 - 统一接口"""
        try:
            with self._lock:
                if strategy_name in self.strategies:
                    return {"success": True, "message": f"策略 {strategy_name} 已经在运行中"}
                
                if strategy_name not in self.strategy_configs:
                    return {"success": False, "message": f"策略 {strategy_name} 配置不存在"}
                
                # 创建策略实例（简化版本，不依赖复杂的事件引擎）
                strategy_instance = await self._create_simple_strategy(strategy_name)
                if not strategy_instance:
                    return {"success": False, "message": f"创建策略 {strategy_name} 实例失败"}
                
                # 启动策略
                self.strategies[strategy_name] = strategy_instance
                
                # 更新数据库状态
                await self._update_strategy_status(strategy_name, True)
                
                # 记录启动事件
                await self._record_strategy_trigger(
                    strategy_name, "手动启动策略", "hold", "hold", "success"
                )
                
                logger.info(f"✅ 策略 {strategy_name} 启动成功")
                return {"success": True, "message": f"策略 {strategy_name} 启动成功"}
                
        except Exception as e:
            logger.error(f"启动策略失败: {e}")
            return {"success": False, "message": f"启动策略失败: {str(e)}"}
    
    async def stop_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """停止策略 - 统一接口"""
        try:
            with self._lock:
                if strategy_name not in self.strategies:
                    return {"success": True, "message": f"策略 {strategy_name} 已经停止"}
                
                # 停止策略
                del self.strategies[strategy_name]
                
                # 更新数据库状态
                await self._update_strategy_status(strategy_name, False)
                
                # 记录停止事件
                await self._record_strategy_trigger(
                    strategy_name, "手动停止策略", "hold", "hold", "success"
                )
                
                logger.info(f"✅ 策略 {strategy_name} 已停止")
                return {"success": True, "message": f"策略 {strategy_name} 停止成功"}
                
        except Exception as e:
            logger.error(f"停止策略失败: {e}")
            return {"success": False, "message": f"停止策略失败: {str(e)}"}
    
    async def emergency_stop_all(self) -> Dict[str, Any]:
        """紧急停止所有策略 - 统一接口"""
        try:
            stopped_strategies = list(self.strategies.keys())
            
            # 停止所有策略
            for strategy_name in stopped_strategies:
                await self.stop_strategy(strategy_name)
            
            # 批量更新数据库
            if stopped_strategies:
                db_manager = get_db_manager()
                await db_manager.execute_update("""
                    UPDATE strategy_configs
                    SET is_active = FALSE, update_time = %s
                    WHERE strategy_name IN ({})
                """.format(','.join(['%s'] * len(stopped_strategies))), 
                [datetime.now()] + stopped_strategies)
            
            # 记录紧急停止事件
            await self._record_strategy_trigger(
                "SYSTEM", "系统紧急停止 - 所有策略已停止", "hold", "hold", "success"
            )
            
            logger.warning(f"🚨 紧急停止了 {len(stopped_strategies)} 个策略")
            return {
                "success": True,
                "message": f"系统紧急停止成功，停止了 {len(stopped_strategies)} 个策略",
                "stopped_strategies": stopped_strategies,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"紧急停止失败: {e}")
            return {"success": False, "message": f"紧急停止失败: {str(e)}"}
    
    async def get_strategy_triggers(self, limit: int = 50, strategy_name: Optional[str] = None) -> List[Dict]:
        """获取策略触发记录 - 统一接口"""
        try:
            db_manager = get_db_manager()
            
            if strategy_name:
                query = """
                    SELECT id, strategy_name, trigger_time, trigger_condition, trigger_price,
                           signal_type, action_type, execution_result, order_id, volume, error_message
                    FROM strategy_triggers
                    WHERE strategy_name = %s
                    ORDER BY trigger_time DESC
                    LIMIT %s
                """
                params = (strategy_name, limit)
            else:
                query = """
                    SELECT id, strategy_name, trigger_time, trigger_condition, trigger_price,
                           signal_type, action_type, execution_result, order_id, volume, error_message
                    FROM strategy_triggers
                    ORDER BY trigger_time DESC
                    LIMIT %s
                """
                params = (limit,)
            
            triggers = await db_manager.execute_query(query, params)
            
            return [
                {
                    "id": trigger["id"],
                    "strategy_name": trigger["strategy_name"],
                    "trigger_time": trigger["trigger_time"].isoformat() if trigger["trigger_time"] else None,
                    "trigger_condition": trigger["trigger_condition"],
                    "trigger_price": float(trigger["trigger_price"]) if trigger["trigger_price"] else None,
                    "signal_type": trigger["signal_type"],
                    "action_type": trigger["action_type"],
                    "execution_result": trigger["execution_result"],
                    "order_id": trigger["order_id"],
                    "volume": trigger["volume"],
                    "error_message": trigger["error_message"]
                }
                for trigger in triggers
            ]
            
        except Exception as e:
            logger.error(f"获取策略触发记录失败: {e}")
            return []
    
    async def _create_simple_strategy(self, strategy_name: str):
        """创建简化的策略实例"""
        try:
            config = self.strategy_configs[strategy_name]
            # 简化版本：只记录策略运行状态，不依赖复杂的事件引擎
            return {
                'name': strategy_name,
                'config': config,
                'start_time': datetime.now(),
                'status': 'running'
            }
        except Exception as e:
            logger.error(f"创建策略实例失败: {e}")
            return None
    
    async def _update_strategy_status(self, strategy_name: str, is_active: bool):
        """更新策略状态到数据库"""
        try:
            db_manager = get_db_manager()
            await db_manager.execute_update("""
                UPDATE strategy_configs
                SET is_active = %s, update_time = %s
                WHERE strategy_name = %s
            """, (is_active, datetime.now(), strategy_name))
        except Exception as e:
            logger.error(f"更新策略状态失败: {e}")
    
    async def _record_strategy_trigger(self, strategy_name: str, condition: str, 
                                     signal_type: str, action_type: str, result: str):
        """记录策略触发事件"""
        try:
            db_manager = get_db_manager()
            await db_manager.execute_insert("""
                INSERT INTO strategy_triggers 
                (strategy_name, trigger_time, trigger_condition, signal_type, action_type, execution_result)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (strategy_name, datetime.now(), condition, signal_type, action_type, result))
        except Exception as e:
            logger.error(f"记录策略触发失败: {e}")

# 全局实例
_unified_strategy_manager = None

def get_unified_strategy_manager() -> UnifiedStrategyManager:
    """获取统一策略管理器实例"""
    global _unified_strategy_manager
    if _unified_strategy_manager is None:
        _unified_strategy_manager = UnifiedStrategyManager()
    return _unified_strategy_manager
