/**
 * API服务层
 */

import { get, post } from './client'
import type {
  SystemStatus,
  ServiceInfo,
  StrategyInfo,
  CurrentStrategyInfo,
  AccountInfo,
  PositionInfo,
  RiskMetrics,
  TickData,
  ServiceControlRequest,
  StrategyControlRequest,
  SystemModeRequest,
  EmergencyRequest,
} from '@/types/api'

// 系统控制API
export const systemAPI = {
  // 获取系统状态
  getStatus: () => get<SystemStatus>('/system/status'),
  
  // 启动系统
  start: () => post('/system/start'),
  
  // 停止系统
  stop: () => post('/system/stop'),
  
  // 切换运行模式
  switchMode: (data: SystemModeRequest) => post('/system/mode', data),
  
  // 紧急停止
  emergencyStop: (data: EmergencyRequest) => post('/system/emergency/stop', data),
  
  // 紧急平仓
  emergencyClose: (data: EmergencyRequest) => post('/system/emergency/close', data),
  
  // 健康检查
  health: () => get('/system/health'),
}

// 服务管理API
export const servicesAPI = {
  // 获取服务列表
  getList: () => get<{ services: ServiceInfo[] }>('/services/list'),
  
  // 获取服务状态
  getStatus: (serviceName: string) => get<ServiceInfo>(`/services/status?service_name=${serviceName}`),
  
  // 启动服务
  start: (data: ServiceControlRequest) => post('/services/start', data),
  
  // 停止服务
  stop: (data: ServiceControlRequest) => post('/services/stop', data),
  
  // 重启服务
  restart: (data: ServiceControlRequest) => post('/services/restart', data),
  
  // 获取服务配置
  getConfig: (serviceName: string) => get(`/services/${serviceName}/config`),
  
  // 更新服务配置
  updateConfig: (serviceName: string, config: any) => post(`/services/${serviceName}/config`, config),
  
  // 获取服务日志
  getLogs: (serviceName: string, lines = 100, level = 'INFO') => 
    get(`/services/${serviceName}/logs?lines=${lines}&level=${level}`),
}

// 策略管理API
export const strategiesAPI = {
  // 获取策略列表
  getList: () => get<{ strategies: StrategyInfo[] }>('/strategies/list'),
  
  // 获取当前策略
  getCurrent: () => get<CurrentStrategyInfo>('/strategies/current'),
  
  // 切换策略
  switch: (data: StrategyControlRequest) => post('/strategies/switch', data),
  
  // 暂停策略
  pause: () => post('/strategies/pause'),
  
  // 恢复策略
  resume: () => post('/strategies/resume'),
  
  // 获取策略配置
  getConfig: (strategyName: string) => get(`/strategies/${strategyName}/config`),
  
  // 更新策略配置
  updateConfig: (strategyName: string, config: any) => post(`/strategies/${strategyName}/config`, config),
}

// 数据查询API
export const dataAPI = {
  // 获取实时行情
  getTicks: (symbols: string[], limit = 100) => 
    get<{ ticks: TickData[] }>(`/data/market/ticks?symbols=${symbols.join(',')}&limit=${limit}`),
  
  // 获取K线数据
  getKlines: (symbol: string, interval = '1m', limit = 100) =>
    get(`/data/market/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`),
  
  // 获取账户信息
  getAccountInfo: () => get<AccountInfo>('/data/account/info'),
  
  // 获取持仓信息
  getPositions: () => get<{ positions: PositionInfo[] }>('/data/account/positions'),
  
  // 获取风险指标
  getRiskMetrics: () => get<RiskMetrics>('/data/risk/metrics'),
  
  // 获取合约列表
  getSymbols: () => get('/data/symbols'),
}

// WebSocket连接管理
export class WebSocketManager {
  private ws: WebSocket | null = null
  private reconnectTimer: number | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectInterval = 3000

  constructor(private url: string) {}

  connect(onMessage?: (data: any) => void, onError?: (error: Event) => void) {
    try {
      this.ws = new WebSocket(this.url)
      
      this.ws.onopen = () => {
        console.log('WebSocket连接已建立')
        this.reconnectAttempts = 0
      }
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          onMessage?.(data)
        } catch (error) {
          console.error('WebSocket消息解析失败:', error)
        }
      }
      
      this.ws.onclose = () => {
        console.log('WebSocket连接已关闭')
        this.reconnect()
      }
      
      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
        onError?.(error)
      }
      
    } catch (error) {
      console.error('WebSocket连接失败:', error)
      onError?.(error as Event)
    }
  }

  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('WebSocket重连次数已达上限')
      return
    }

    this.reconnectAttempts++
    console.log(`WebSocket重连中... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    this.reconnectTimer = window.setTimeout(() => {
      this.connect()
    }, this.reconnectInterval)
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket未连接，无法发送消息')
    }
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

// 创建WebSocket管理器实例
export const createWebSocketManager = (channel: string) => {
  const wsUrl = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/v1/${channel}`
  return new WebSocketManager(wsUrl)
}
