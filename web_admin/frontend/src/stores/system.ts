/**
 * 系统状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { systemAPI, servicesAPI } from '@/api/services'
import type { SystemStatus, ServiceInfo } from '@/types/api'

export const useSystemStore = defineStore('system', () => {
  // 状态
  const systemStatus = ref<SystemStatus | null>(null)
  const services = ref<ServiceInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const isSystemRunning = computed(() => {
    // 如果系统状态为null或API失败，认为系统没有运行
    if (!systemStatus.value) return false
    return systemStatus.value.system_status === 'running'
  })
  const currentMode = computed(() => systemStatus.value?.running_mode || 'UNKNOWN')
  const uptime = computed(() => systemStatus.value?.uptime || '0h 0m 0s')
  
  const ctpStatus = computed(() => ({
    marketData: systemStatus.value?.ctp_status?.market_data || { connected: false, server: '', latency: '' },
    trading: systemStatus.value?.ctp_status?.trading || { connected: false, server: '', latency: '' }
  }))

  const servicesSummary = computed(() => systemStatus.value?.services_summary || {
    total: 0,
    running: 0,
    stopped: 0,
    error: 0
  })

  const runningServices = computed(() => services.value.filter(s => s.status === 'running'))
  const stoppedServices = computed(() => services.value.filter(s => s.status === 'stopped'))
  const errorServices = computed(() => services.value.filter(s => s.status === 'error'))

  // 方法
  const fetchSystemStatus = async () => {
    try {
      loading.value = true
      error.value = null
      const response = await systemAPI.getStatus()
      systemStatus.value = response.data!
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取系统状态失败'
      console.error('获取系统状态失败:', err)
    } finally {
      loading.value = false
    }
  }

  const fetchServices = async () => {
    try {
      const response = await servicesAPI.getList()
      services.value = response.data?.services || []
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取服务列表失败'
      console.error('获取服务列表失败:', err)
    }
  }

  const startSystem = async () => {
    try {
      loading.value = true
      await systemAPI.start()
      await fetchSystemStatus()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : '启动系统失败'
      return false
    } finally {
      loading.value = false
    }
  }

  const stopSystem = async () => {
    try {
      loading.value = true
      await systemAPI.stop()
      await fetchSystemStatus()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : '停止系统失败'
      return false
    } finally {
      loading.value = false
    }
  }

  const switchMode = async (mode: string, reason?: string) => {
    try {
      loading.value = true
      await systemAPI.switchMode({
        mode: mode as any,
        reason,
        operator: 'admin'
      })
      await fetchSystemStatus()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : '切换模式失败'
      return false
    } finally {
      loading.value = false
    }
  }

  const startService = async (serviceName: string, config?: any) => {
    try {
      await servicesAPI.start({
        service_name: serviceName,
        action: 'start',
        config
      })
      await fetchServices()
      await fetchSystemStatus()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : `启动${serviceName}失败`
      return false
    }
  }

  const stopService = async (serviceName: string, force = false) => {
    try {
      await servicesAPI.stop({
        service_name: serviceName,
        action: 'stop',
        force
      })
      await fetchServices()
      await fetchSystemStatus()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : `停止${serviceName}失败`
      return false
    }
  }

  const restartService = async (serviceName: string, config?: any) => {
    try {
      await servicesAPI.restart({
        service_name: serviceName,
        action: 'restart',
        config
      })
      await fetchServices()
      await fetchSystemStatus()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : `重启${serviceName}失败`
      return false
    }
  }

  const emergencyStop = async (reason: string) => {
    try {
      loading.value = true
      await systemAPI.emergencyStop({
        action: 'stop',
        reason,
        operator: 'admin'
      })
      await fetchSystemStatus()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : '紧急停止失败'
      return false
    } finally {
      loading.value = false
    }
  }

  const emergencyClose = async (reason: string, confirmationCode: string) => {
    try {
      loading.value = true
      await systemAPI.emergencyClose({
        action: 'close',
        reason,
        operator: 'admin',
        confirmation_code: confirmationCode
      })
      await fetchSystemStatus()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : '紧急平仓失败'
      return false
    } finally {
      loading.value = false
    }
  }

  const clearError = () => {
    error.value = null
  }

  // 初始化
  const init = async () => {
    await Promise.all([
      fetchSystemStatus(),
      fetchServices()
    ])
  }

  return {
    // 状态
    systemStatus,
    services,
    loading,
    error,
    
    // 计算属性
    isSystemRunning,
    currentMode,
    uptime,
    ctpStatus,
    servicesSummary,
    runningServices,
    stoppedServices,
    errorServices,
    
    // 方法
    fetchSystemStatus,
    fetchServices,
    startSystem,
    stopSystem,
    switchMode,
    startService,
    stopService,
    restartService,
    emergencyStop,
    emergencyClose,
    clearError,
    init
  }
})
