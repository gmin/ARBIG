"""
信号发送器
负责将策略信号发送到交易服务
"""

import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import SignalData
from utils.logger import get_logger

logger = get_logger(__name__)

class SignalSender:
    """
    信号发送器
    负责将策略信号通过HTTP请求发送到交易服务
    """
    
    def __init__(self, trading_service_url: str = "http://localhost:8001"):
        """
        初始化信号发送器
        
        Args:
            trading_service_url: 交易服务URL
        """
        self.trading_service_url = trading_service_url
        self.session = requests.Session()
        self.order_counter = 0
        
        logger.info(f"信号发送器初始化完成，交易服务URL: {trading_service_url}")
    
    def send_signal(self, signal: SignalData, time_condition: str = "GFD") -> str:
        """
        发送交易信号到交易服务

        Args:
            signal: 信号数据
            time_condition: 订单有效期类型
                - "GFD": 当日有效 (默认)
                - "GFD": Good For Day - 当日有效 (使用激进价格确保立即成交)
                - "GFS": 本节有效

        Returns:
            订单ID
        """
        try:
            # 生成订单ID
            self.order_counter += 1
            order_id = f"{signal.strategy_name}_{signal.action}_{datetime.now().strftime('%H%M%S')}_{self.order_counter:03d}"

            # 构造请求数据
            request_data = {
                "strategy_name": signal.strategy_name,
                "symbol": signal.symbol,
                "direction": signal.direction.value,
                "action": signal.action,
                "volume": signal.volume,
                "price": signal.price,
                "signal_type": signal.signal_type,
                "stop_order": getattr(signal, 'stop_order', False),
                "time_condition": time_condition,  # 添加订单有效期参数
                "timestamp": signal.timestamp.isoformat() if signal.timestamp else datetime.now().isoformat(),
                "order_id": order_id
            }
            
            # 发送HTTP请求到交易服务
            url = f"{self.trading_service_url}/real_trading/strategy_signal"
            response = self.session.post(
                url,
                json=request_data,
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info(f"信号发送成功: {signal.strategy_name} {signal.action} {signal.volume}@{signal.price}")
                    return result.get("order_id", order_id)
                else:
                    logger.error(f"信号发送失败: {result.get('message', '未知错误')}")
                    return ""
            else:
                logger.error(f"信号发送HTTP错误: {response.status_code} {response.text}")
                return ""
                
        except requests.exceptions.Timeout:
            logger.error(f"信号发送超时: {signal.strategy_name} {signal.action}")
            return ""
        except requests.exceptions.ConnectionError:
            logger.error(f"无法连接到交易服务: {self.trading_service_url}")
            return ""
        except Exception as e:
            logger.error(f"信号发送异常: {e}")
            return ""
    
    def send_risk_signal(self, signal: SignalData) -> bool:
        """
        发送风险信号到交易服务
        
        Args:
            signal: 风险信号数据
            
        Returns:
            是否发送成功
        """
        try:
            request_data = {
                "strategy_name": signal.strategy_name,
                "symbol": signal.symbol,
                "signal_type": "RISK",
                "action": signal.action,
                "message": getattr(signal, 'message', ''),
                "timestamp": signal.timestamp.isoformat() if signal.timestamp else datetime.now().isoformat()
            }
            
            url = f"{self.trading_service_url}/real_trading/risk_signal"
            response = self.session.post(
                url,
                json=request_data,
                timeout=3.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info(f"风险信号发送成功: {signal.strategy_name} {signal.action}")
                    return True
                else:
                    logger.error(f"风险信号发送失败: {result.get('message', '未知错误')}")
                    return False
            else:
                logger.error(f"风险信号发送HTTP错误: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"风险信号发送异常: {e}")
            return False
    
    def get_trading_status(self) -> Dict[str, Any]:
        """
        获取交易服务状态
        
        Returns:
            交易服务状态信息
        """
        try:
            url = f"{self.trading_service_url}/real_trading/status"
            response = self.session.get(url, timeout=3.0)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"获取交易状态失败: {response.status_code}")
                return {"success": False, "message": "交易服务不可用"}
                
        except Exception as e:
            logger.error(f"获取交易状态异常: {e}")
            return {"success": False, "message": "连接异常: " + str(e)}
    
    def get_positions(self) -> Dict[str, Any]:
        """
        获取持仓信息
        
        Returns:
            持仓信息
        """
        try:
            url = f"{self.trading_service_url}/real_trading/positions"
            response = self.session.get(url, timeout=3.0)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"获取持仓信息失败: {response.status_code}")
                return {"success": False, "message": "获取持仓失败"}
                
        except Exception as e:
            logger.error(f"获取持仓信息异常: {e}")
            return {"success": False, "message": "连接异常: " + str(e)}
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            交易服务是否健康
        """
        try:
            status = self.get_trading_status()
            return status.get("success", False)
        except:
            return False
