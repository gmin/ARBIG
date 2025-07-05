/**
 * API相关类型定义
 */

// 通用API响应
export interface APIResponse<T = any> {
  success: boolean
  message: string
  data?: T
  timestamp: string
  request_id?: string
}

// 错误响应
export interface ErrorResponse {
  success: false
  error: {
    code: string
    message: string
    details?: string
  }
  timestamp: string
  request_id?: string
}

// 系统状态
export interface SystemStatus {
  system_status: string
  running_mode: string
  start_time: string
  uptime: string
  ctp_status: {
    market_data: {
      connected: boolean
      server: string
      latency?: string
    }
    trading: {
      connected: boolean
      server: string
      latency?: string
    }
  }
  services_summary: {
    total: number
    running: number
    stopped: number
    error: number
  }
  version: string
}

// 服务信息
export interface ServiceInfo {
  name: string
  display_name: string
  status: 'running' | 'stopped' | 'error' | 'starting' | 'stopping'
  start_time?: string
  uptime?: string
  cpu_usage?: string
  memory_usage?: string
  last_heartbeat?: string
  required: boolean
  dependencies: string[]
  error_message?: string
}

// 策略信息
export interface StrategyInfo {
  name: string
  display_name: string
  description: string
  version: string
  risk_level: string
  status: string
  author: string
}

// 当前策略信息
export interface CurrentStrategyInfo {
  strategy_name: string
  display_name: string
  status: string
  start_time: string
  runtime: string
  statistics: {
    signals_generated: number
    orders_executed: number
    successful_trades: number
    failed_trades: number
    current_profit: number
    today_profit: number
    win_rate: number
    sharpe_ratio: number
    max_drawdown: number
  }
}

// 行情数据
export interface TickData {
  symbol: string
  datetime: string
  last_price: number
  bid_price: number
  ask_price: number
  volume: number
  open_interest: number
  change: number
  change_percent: number
}

// 账户信息
export interface AccountInfo {
  account_id: string
  total_assets: number
  available: number
  margin: number
  frozen: number
  profit: number
  today_profit: number
  commission: number
  currency: string
  update_time: string
}

// 持仓信息
export interface PositionInfo {
  symbol: string
  direction: string
  volume: number
  avg_price: number
  current_price: number
  profit: number
  margin: number
  open_time: string
}

// 风险指标
export interface RiskMetrics {
  risk_level: string
  position_ratio: number
  daily_loss: number
  max_drawdown: number
  var_95: number
  leverage: number
  concentration: Record<string, number>
}

// 请求类型
export interface ServiceControlRequest {
  service_name: string
  action?: 'start' | 'stop' | 'restart'
  force?: boolean
  config?: Record<string, any>
}

export interface StrategyControlRequest {
  from_strategy?: string
  to_strategy: string
  config?: Record<string, any>
  switch_mode?: 'safe' | 'force'
  reason?: string
}

export interface SystemModeRequest {
  mode: 'FULL_TRADING' | 'MONITOR_ONLY' | 'MARKET_DATA_ONLY'
  reason?: string
  operator?: string
}

export interface EmergencyRequest {
  action: 'stop' | 'close'
  reason: string
  operator: string
  confirmation_code?: string
}
