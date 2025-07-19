"""
API依赖注入
提供API路由所需的依赖项
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 全局变量，用于存储系统组件的引用
# 连接到重构后的main.py服务容器
_service_container = None
_system_manager = None
_service_manager = None
_strategy_manager = None
_data_manager = None

# 安全认证
security = HTTPBearer(auto_error=False)

class SystemManager:
    """系统管理器接口"""
    
    def __init__(self):
        self.running = False
        self.mode = "FULL_TRADING"
        
    def get_status(self):
        """获取系统状态"""
        return {
            "running": self.running,
            "mode": self.mode
        }
    
    def start_system(self):
        """启动系统"""
        self.running = True
        return True
    
    def stop_system(self):
        """停止系统"""
        self.running = False
        return True
    
    def switch_mode(self, mode: str):
        """切换运行模式"""
        self.mode = mode
        return True

class ServiceManager:
    """服务管理器接口"""
    
    def __init__(self):
        self.services = {}
        
    def get_service_status(self, service_name: str):
        """获取服务状态"""
        return self.services.get(service_name, {"status": "unknown"})
    
    def start_service(self, service_name: str, config: dict = None):
        """启动服务"""
        self.services[service_name] = {"status": "running", "config": config}
        return True
    
    def stop_service(self, service_name: str, force: bool = False):
        """停止服务"""
        if service_name in self.services:
            self.services[service_name]["status"] = "stopped"
        return True
    
    def restart_service(self, service_name: str, config: dict = None):
        """重启服务"""
        return self.stop_service(service_name) and self.start_service(service_name, config)

class StrategyManager:
    """策略管理器接口"""
    
    def __init__(self):
        self.current_strategy = None
        self.available_strategies = {}
        
    def get_current_strategy(self):
        """获取当前策略"""
        return self.current_strategy
    
    def get_available_strategies(self):
        """获取可用策略列表"""
        return self.available_strategies
    
    def switch_strategy(self, from_strategy: str, to_strategy: str, config: dict = None):
        """切换策略"""
        self.current_strategy = {
            "name": to_strategy,
            "config": config,
            "status": "running"
        }
        return True
    
    def pause_strategy(self):
        """暂停策略"""
        if self.current_strategy:
            self.current_strategy["status"] = "paused"
        return True
    
    def resume_strategy(self):
        """恢复策略"""
        if self.current_strategy:
            self.current_strategy["status"] = "running"
        return True

class DataManager:
    """数据管理器接口"""

    def __init__(self):
        self.market_data = {}
        self.account_data = {}
        self.data_provider = None

    def set_data_provider(self, data_provider):
        """设置数据提供器"""
        self.data_provider = data_provider

    def get_market_data(self, symbols: list, data_type: str = "tick"):
        """获取行情数据"""
        return {"symbols": symbols, "data_type": data_type, "data": []}

    def get_account_info(self):
        """获取账户信息"""
        return self.account_data

    def get_positions(self):
        """获取持仓信息"""
        return []

    def get_orders(self):
        """获取订单信息"""
        return []

# 初始化管理器实例
def init_managers():
    """初始化管理器实例"""
    global _system_manager, _service_manager, _strategy_manager, _data_manager
    
    if _system_manager is None:
        _system_manager = SystemManager()
    if _service_manager is None:
        _service_manager = ServiceManager()
    if _strategy_manager is None:
        _strategy_manager = StrategyManager()
    if _data_manager is None:
        _data_manager = DataManager()

# 依赖注入函数
def get_system_manager():
    """获取系统管理器"""
    # 如果有真实的服务容器，返回服务容器，否则返回模拟的管理器
    if _service_container:
        return _service_container

    init_managers()
    return _system_manager

def get_service_manager():
    """获取服务管理器"""
    # 如果有真实的服务容器，返回服务容器，否则返回模拟的管理器
    if _service_container:
        return _service_container

    init_managers()
    return _service_manager

def get_strategy_manager() -> StrategyManager:
    """获取策略管理器"""
    init_managers()
    return _strategy_manager

def get_data_manager():
    """获取数据管理器"""
    # 如果有真实的服务容器，返回服务容器，否则返回模拟的管理器
    if _service_container:
        return _service_container

    init_managers()
    return _data_manager

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户（认证）"""
    # 这里暂时跳过认证，后续可以添加JWT或API Key认证
    if credentials is None:
        # 在开发阶段允许无认证访问
        return {"username": "admin", "role": "admin"}
    
    # 简单的API Key验证示例
    if credentials.credentials == "arbig_api_key_123":
        return {"username": "admin", "role": "admin"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

def require_admin(current_user: dict = Depends(get_current_user)):
    """要求管理员权限"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

# 设置管理器引用的函数（供main.py调用）
def set_service_container(container):
    """设置服务容器引用"""
    global _service_container
    _service_container = container

def set_system_manager(manager):
    """设置系统管理器引用"""
    global _system_manager
    _system_manager = manager

def set_service_manager(manager):
    """设置服务管理器引用"""
    global _service_manager
    _service_manager = manager

def set_strategy_manager(manager):
    """设置策略管理器引用"""
    global _strategy_manager
    _strategy_manager = manager

def set_data_manager(manager):
    """设置数据管理器引用"""
    global _data_manager
    _data_manager = manager

def set_data_provider(data_provider):
    """设置数据提供器引用"""
    global _data_manager
    if _data_manager is None:
        init_managers()
    _data_manager.set_data_provider(data_provider)
