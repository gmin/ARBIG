"""
系统层面监控模块
监控服务状态、延时、系统资源等
"""

import asyncio
import time
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ServiceStatus:
    """服务状态"""
    name: str
    status: str  # "running", "stopped", "error", "connecting"
    last_heartbeat: datetime
    uptime: float  # 运行时间（秒）
    error_message: Optional[str] = None
    connection_count: int = 0
    reconnect_count: int = 0

@dataclass
class LatencyMetrics:
    """延时指标"""
    market_data_latency: float  # 行情延时（毫秒）
    order_latency: float  # 下单延时（毫秒）
    network_latency: float  # 网络延时（毫秒）
    last_update: datetime
    avg_latency_1min: float = 0.0
    avg_latency_5min: float = 0.0
    max_latency_1min: float = 0.0

@dataclass
class SystemResources:
    """系统资源"""
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    timestamp: datetime

@dataclass
class ConnectionQuality:
    """连接质量"""
    ctp_md_connected: bool  # CTP行情连接
    ctp_td_connected: bool  # CTP交易连接
    connection_stability: float  # 连接稳定性（0-1）
    packet_loss_rate: float  # 丢包率
    last_disconnect_time: Optional[datetime] = None
    total_disconnects: int = 0

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.services: Dict[str, ServiceStatus] = {}
        self.latency_history: List[LatencyMetrics] = []
        self.resource_history: List[SystemResources] = []
        self.connection_quality = ConnectionQuality(
            ctp_md_connected=False,
            ctp_td_connected=False,
            connection_stability=0.0,
            packet_loss_rate=0.0
        )
        
        # 监控配置
        self.max_history_size = 1000  # 最大历史记录数
        self.update_interval = 1.0  # 更新间隔（秒）
        
        # 启动时间
        self.start_time = datetime.now()
        
        # 网络统计基准
        self.network_baseline = None
        
    async def start_monitoring(self):
        """启动监控"""
        logger.info("启动系统监控...")
        
        # 初始化网络基准
        self._init_network_baseline()
        
        # 启动监控任务
        asyncio.create_task(self._monitor_loop())
        
    async def _monitor_loop(self):
        """监控主循环"""
        while True:
            try:
                # 更新系统资源
                await self._update_system_resources()
                
                # 更新服务状态
                await self._update_service_status()
                
                # 更新延时指标
                await self._update_latency_metrics()
                
                # 清理历史数据
                self._cleanup_history()
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(5)
    
    async def _update_system_resources(self):
        """更新系统资源"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # 网络使用情况
            network = psutil.net_io_counters()
            if self.network_baseline:
                network_sent_mb = (network.bytes_sent - self.network_baseline['sent']) / (1024**2)
                network_recv_mb = (network.bytes_recv - self.network_baseline['recv']) / (1024**2)
            else:
                network_sent_mb = network.bytes_sent / (1024**2)
                network_recv_mb = network.bytes_recv / (1024**2)
            
            # 进程数量
            process_count = len(psutil.pids())
            
            # 创建资源记录
            resource = SystemResources(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_gb=memory_used_gb,
                memory_total_gb=memory_total_gb,
                disk_percent=disk.percent,
                disk_used_gb=disk_used_gb,
                disk_total_gb=disk_total_gb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                process_count=process_count,
                timestamp=datetime.now()
            )
            
            self.resource_history.append(resource)
            
        except Exception as e:
            logger.error(f"更新系统资源失败: {e}")
    
    async def _update_service_status(self):
        """更新服务状态"""
        try:
            # 检查CTP服务状态
            await self._check_ctp_status()
            
            # 检查其他核心服务
            await self._check_core_services()
            
        except Exception as e:
            logger.error(f"更新服务状态失败: {e}")
    
    async def _check_ctp_status(self):
        """检查CTP服务状态"""
        # 这里需要与实际的CTP服务通信
        # 暂时模拟状态
        now = datetime.now()
        
        # CTP行情服务
        if "ctp_market_data" not in self.services:
            self.services["ctp_market_data"] = ServiceStatus(
                name="CTP行情服务",
                status="running",
                last_heartbeat=now,
                uptime=(now - self.start_time).total_seconds()
            )
        
        # CTP交易服务
        if "ctp_trading" not in self.services:
            self.services["ctp_trading"] = ServiceStatus(
                name="CTP交易服务", 
                status="running",
                last_heartbeat=now,
                uptime=(now - self.start_time).total_seconds()
            )
    
    async def _check_core_services(self):
        """检查核心服务状态"""
        services_to_check = [
            ("data_service", "数据服务"),
            ("trading_service", "交易服务"),
            ("risk_service", "风控服务"),
            ("strategy_service", "策略服务")
        ]
        
        now = datetime.now()
        
        for service_id, service_name in services_to_check:
            if service_id not in self.services:
                self.services[service_id] = ServiceStatus(
                    name=service_name,
                    status="running",  # 实际应该检查真实状态
                    last_heartbeat=now,
                    uptime=(now - self.start_time).total_seconds()
                )
    
    async def _update_latency_metrics(self):
        """更新延时指标"""
        try:
            now = datetime.now()
            
            # 模拟延时数据（实际应该从真实系统获取）
            latency = LatencyMetrics(
                market_data_latency=5.2,  # 毫秒
                order_latency=12.8,
                network_latency=3.1,
                last_update=now
            )
            
            # 计算平均延时
            if len(self.latency_history) > 0:
                recent_1min = [l for l in self.latency_history if (now - l.last_update).total_seconds() <= 60]
                recent_5min = [l for l in self.latency_history if (now - l.last_update).total_seconds() <= 300]
                
                if recent_1min:
                    latency.avg_latency_1min = sum(l.market_data_latency for l in recent_1min) / len(recent_1min)
                    latency.max_latency_1min = max(l.market_data_latency for l in recent_1min)
                
                if recent_5min:
                    latency.avg_latency_5min = sum(l.market_data_latency for l in recent_5min) / len(recent_5min)
            
            self.latency_history.append(latency)
            
        except Exception as e:
            logger.error(f"更新延时指标失败: {e}")
    
    def _init_network_baseline(self):
        """初始化网络基准"""
        try:
            network = psutil.net_io_counters()
            self.network_baseline = {
                'sent': network.bytes_sent,
                'recv': network.bytes_recv
            }
        except Exception as e:
            logger.error(f"初始化网络基准失败: {e}")
    
    def _cleanup_history(self):
        """清理历史数据"""
        if len(self.resource_history) > self.max_history_size:
            self.resource_history = self.resource_history[-self.max_history_size:]
        
        if len(self.latency_history) > self.max_history_size:
            self.latency_history = self.latency_history[-self.max_history_size:]
    
    # ========== 对外接口 ==========
    
    def get_system_overview(self) -> Dict[str, Any]:
        """获取系统概览"""
        current_resource = self.resource_history[-1] if self.resource_history else None
        current_latency = self.latency_history[-1] if self.latency_history else None
        
        return {
            "system_uptime": (datetime.now() - self.start_time).total_seconds(),
            "services": {k: asdict(v) for k, v in self.services.items()},
            "current_resources": asdict(current_resource) if current_resource else None,
            "current_latency": asdict(current_latency) if current_latency else None,
            "connection_quality": asdict(self.connection_quality),
            "last_update": datetime.now().isoformat()
        }
    
    def get_resource_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """获取资源使用历史"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_resources = [
            asdict(r) for r in self.resource_history 
            if r.timestamp >= cutoff_time
        ]
        return recent_resources
    
    def get_latency_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """获取延时历史"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_latency = [
            asdict(l) for l in self.latency_history 
            if l.last_update >= cutoff_time
        ]
        return recent_latency
    
    def update_service_status(self, service_id: str, status: str, error_message: str = None):
        """更新服务状态"""
        if service_id in self.services:
            self.services[service_id].status = status
            self.services[service_id].last_heartbeat = datetime.now()
            if error_message:
                self.services[service_id].error_message = error_message
    
    def record_connection_event(self, service: str, connected: bool):
        """记录连接事件"""
        if service == "ctp_md":
            self.connection_quality.ctp_md_connected = connected
        elif service == "ctp_td":
            self.connection_quality.ctp_td_connected = connected
        
        if not connected:
            self.connection_quality.last_disconnect_time = datetime.now()
            self.connection_quality.total_disconnects += 1

# 全局系统监控实例
system_monitor = SystemMonitor()
