<template>
  <div class="dashboard">
    <!-- 系统概览卡片 -->
    <a-row :gutter="[16, 16]">
      <!-- 系统状态卡片 -->
      <a-col :xs="24" :sm="12" :md="6">
        <a-card class="status-card">
          <div class="card-content">
            <div class="card-icon system-status" :class="systemStatusClass">
              <RocketOutlined />
            </div>
            <div class="card-info">
              <div class="card-title">系统状态</div>
              <div class="card-value">{{ systemStatusText }}</div>
              <div class="card-extra">运行时长: {{ uptime }}</div>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- 运行模式卡片 -->
      <a-col :xs="24" :sm="12" :md="6">
        <a-card class="status-card">
          <div class="card-content">
            <div class="card-icon mode-status">
              <SettingOutlined />
            </div>
            <div class="card-info">
              <div class="card-title">运行模式</div>
              <div class="card-value">{{ currentModeText }}</div>
              <div class="card-extra">
                <a-button type="link" size="small" @click="showModeModal = true">
                  切换模式
                </a-button>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- 服务状态卡片 -->
      <a-col :xs="24" :sm="12" :md="6">
        <a-card class="status-card">
          <div class="card-content">
            <div class="card-icon services-status">
              <AppstoreOutlined />
            </div>
            <div class="card-info">
              <div class="card-title">服务状态</div>
              <div class="card-value">{{ runningServicesCount }}/{{ totalServicesCount }}</div>
              <div class="card-extra">{{ stoppedServicesCount }}个已停止</div>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- CTP连接状态卡片 -->
      <a-col :xs="24" :sm="12" :md="6">
        <a-card class="status-card">
          <div class="card-content">
            <div class="card-icon ctp-status" :class="ctpStatusClass">
              <ApiOutlined />
            </div>
            <div class="card-info">
              <div class="card-title">CTP连接</div>
              <div class="card-value">{{ ctpStatusText }}</div>
              <div class="card-extra">延迟: {{ ctpLatency }}</div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 主要功能区域 -->
    <a-row :gutter="[16, 16]" style="margin-top: 16px">
      <!-- 系统控制面板 -->
      <a-col :xs="24" :lg="12">
        <a-card title="系统控制" class="control-panel">
          <div class="control-buttons">
            <a-space direction="vertical" style="width: 100%">
              <a-button 
                type="primary" 
                size="large" 
                block
                :loading="systemStore.loading"
                :disabled="systemStore.isSystemRunning"
                @click="handleStartSystem"
              >
                <PlayCircleOutlined />
                启动系统
              </a-button>
              
              <a-button 
                size="large" 
                block
                :loading="systemStore.loading"
                :disabled="!systemStore.isSystemRunning"
                @click="handleStopSystem"
              >
                <PauseCircleOutlined />
                停止系统
              </a-button>
              
              <a-button 
                type="primary" 
                danger 
                size="large" 
                block
                @click="showEmergencyModal = true"
              >
                <StopOutlined />
                紧急停止
              </a-button>
            </a-space>
          </div>
        </a-card>
      </a-col>

      <!-- 服务管理面板 -->
      <a-col :xs="24" :lg="12">
        <a-card title="服务管理" class="services-panel">
          <div class="services-list">
            <div 
              v-for="service in systemStore.services" 
              :key="service.name"
              class="service-item"
            >
              <div class="service-info">
                <span class="status-indicator" :class="service.status"></span>
                <span class="service-name">{{ service.display_name }}</span>
              </div>
              <div class="service-actions">
                <a-button 
                  v-if="service.status === 'stopped'"
                  type="primary" 
                  size="small"
                  @click="handleStartService(service.name)"
                >
                  启动
                </a-button>
                <a-button 
                  v-else-if="service.status === 'running'"
                  size="small"
                  @click="handleStopService(service.name)"
                >
                  停止
                </a-button>
                <a-button 
                  v-else
                  size="small"
                  disabled
                >
                  {{ service.status }}
                </a-button>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 快速导航 -->
    <a-row :gutter="[16, 16]" style="margin-top: 16px">
      <a-col :span="24">
        <a-card title="快速导航" class="quick-nav">
          <a-row :gutter="[16, 16]">
            <a-col :xs="12" :sm="8" :md="6" :lg="4">
              <div class="nav-item" @click="$router.push('/market')">
                <LineChartOutlined class="nav-icon" />
                <div class="nav-text">行情数据</div>
              </div>
            </a-col>
            <a-col :xs="12" :sm="8" :md="6" :lg="4">
              <div class="nav-item" @click="$router.push('/account')">
                <WalletOutlined class="nav-icon" />
                <div class="nav-text">账户资金</div>
              </div>
            </a-col>
            <a-col :xs="12" :sm="8" :md="6" :lg="4">
              <div class="nav-item" @click="$router.push('/positions')">
                <PieChartOutlined class="nav-icon" />
                <div class="nav-text">持仓管理</div>
              </div>
            </a-col>
            <a-col :xs="12" :sm="8" :md="6" :lg="4">
              <div class="nav-item" @click="$router.push('/strategies')">
                <RocketOutlined class="nav-icon" />
                <div class="nav-text">策略管理</div>
              </div>
            </a-col>
            <a-col :xs="12" :sm="8" :md="6" :lg="4">
              <div class="nav-item" @click="$router.push('/risk')">
                <SafetyOutlined class="nav-icon" />
                <div class="nav-text">风险控制</div>
              </div>
            </a-col>
            <a-col :xs="12" :sm="8" :md="6" :lg="4">
              <div class="nav-item" @click="$router.push('/logs')">
                <FileTextOutlined class="nav-icon" />
                <div class="nav-text">系统日志</div>
              </div>
            </a-col>
          </a-row>
        </a-card>
      </a-col>
    </a-row>

    <!-- 模式切换弹窗 -->
    <a-modal
      v-model:open="showModeModal"
      title="切换运行模式"
      @ok="handleSwitchMode"
    >
      <a-form layout="vertical">
        <a-form-item label="选择运行模式">
          <a-radio-group v-model:value="selectedMode">
            <a-radio value="FULL_TRADING">完整交易模式</a-radio>
            <a-radio value="MONITOR_ONLY">仅监控模式</a-radio>
            <a-radio value="MARKET_DATA_ONLY">仅行情模式</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="切换原因">
          <a-textarea v-model:value="modeReason" placeholder="请输入切换原因..." />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 紧急停止弹窗 -->
    <a-modal
      v-model:open="showEmergencyModal"
      title="紧急停止确认"
      :confirm-loading="emergencyLoading"
      @ok="handleEmergencyStop"
    >
      <a-alert
        message="警告"
        description="紧急停止将立即停止所有交易活动，请确认操作原因。"
        type="warning"
        show-icon
        style="margin-bottom: 16px"
      />
      
      <a-form layout="vertical">
        <a-form-item label="停止原因" required>
          <a-textarea
            v-model:value="emergencyReason"
            placeholder="请输入紧急停止的原因..."
            :rows="3"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  RocketOutlined,
  SettingOutlined,
  AppstoreOutlined,
  ApiOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  LineChartOutlined,
  WalletOutlined,
  PieChartOutlined,
  SafetyOutlined,
  FileTextOutlined
} from '@ant-design/icons-vue'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()

// 响应式数据
const showModeModal = ref(false)
const showEmergencyModal = ref(false)
const selectedMode = ref('')
const modeReason = ref('')
const emergencyReason = ref('')
const emergencyLoading = ref(false)

// 计算属性
const systemStatusClass = computed(() => {
  if (systemStore.isSystemRunning) return 'running'
  if (systemStore.error) return 'error'
  return 'stopped'
})

const systemStatusText = computed(() => {
  if (systemStore.loading) return '检查中...'
  if (systemStore.isSystemRunning) return '运行中'
  if (systemStore.error) return '异常'
  return '已停止'
})

const uptime = computed(() => systemStore.uptime)

const currentModeText = computed(() => {
  const modeMap: Record<string, string> = {
    'FULL_TRADING': '完整交易',
    'MONITOR_ONLY': '仅监控',
    'MARKET_DATA_ONLY': '仅行情'
  }
  return modeMap[systemStore.currentMode] || systemStore.currentMode
})

const totalServicesCount = computed(() => systemStore.servicesSummary.total)
const runningServicesCount = computed(() => systemStore.servicesSummary.running)
const stoppedServicesCount = computed(() => systemStore.servicesSummary.stopped)

const ctpStatusClass = computed(() => {
  const { marketData, trading } = systemStore.ctpStatus
  if (marketData.connected && trading.connected) return 'running'
  if (marketData.connected || trading.connected) return 'warning'
  return 'stopped'
})

const ctpStatusText = computed(() => {
  const { marketData, trading } = systemStore.ctpStatus
  if (marketData.connected && trading.connected) return '全部连接'
  if (marketData.connected) return '行情连接'
  if (trading.connected) return '交易连接'
  return '未连接'
})

const ctpLatency = computed(() => {
  const { marketData, trading } = systemStore.ctpStatus
  return marketData.latency || trading.latency || '--'
})

// 方法
const handleStartSystem = async () => {
  const success = await systemStore.startSystem()
  if (success) {
    message.success('系统启动成功')
  }
}

const handleStopSystem = async () => {
  const success = await systemStore.stopSystem()
  if (success) {
    message.success('系统停止成功')
  }
}

const handleStartService = async (serviceName: string) => {
  const success = await systemStore.startService(serviceName)
  if (success) {
    message.success(`${serviceName}启动成功`)
  }
}

const handleStopService = async (serviceName: string) => {
  const success = await systemStore.stopService(serviceName)
  if (success) {
    message.success(`${serviceName}停止成功`)
  }
}

const handleSwitchMode = async () => {
  if (!selectedMode.value) {
    message.error('请选择运行模式')
    return
  }

  const success = await systemStore.switchMode(selectedMode.value, modeReason.value)
  if (success) {
    message.success('运行模式切换成功')
    showModeModal.value = false
    modeReason.value = ''
  }
}

const handleEmergencyStop = async () => {
  if (!emergencyReason.value.trim()) {
    message.error('请输入停止原因')
    return
  }

  try {
    emergencyLoading.value = true
    const success = await systemStore.emergencyStop(emergencyReason.value)
    
    if (success) {
      message.success('紧急停止执行成功')
      showEmergencyModal.value = false
      emergencyReason.value = ''
    }
  } finally {
    emergencyLoading.value = false
  }
}

// 定时刷新
let refreshTimer: number | null = null

onMounted(() => {
  // 初始化当前模式
  selectedMode.value = systemStore.currentMode
  
  // 启动定时刷新
  refreshTimer = window.setInterval(() => {
    systemStore.fetchSystemStatus()
    systemStore.fetchServices()
  }, 3000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped lang="scss">
.dashboard {
  padding: 24px;
  background: #f5f5f5;
  min-height: 100%;
}

.status-card {
  .card-content {
    display: flex;
    align-items: center;
    
    .card-icon {
      width: 48px;
      height: 48px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      margin-right: 16px;
      
      &.system-status {
        &.running {
          background: #f6ffed;
          color: #52c41a;
        }
        &.stopped {
          background: #f5f5f5;
          color: #8c8c8c;
        }
        &.error {
          background: #fff2f0;
          color: #f5222d;
        }
      }
      
      &.mode-status {
        background: #e6f7ff;
        color: #1890ff;
      }
      
      &.services-status {
        background: #f9f0ff;
        color: #722ed1;
      }
      
      &.ctp-status {
        &.running {
          background: #f6ffed;
          color: #52c41a;
        }
        &.warning {
          background: #fffbe6;
          color: #faad14;
        }
        &.stopped {
          background: #fff2f0;
          color: #f5222d;
        }
      }
    }
    
    .card-info {
      flex: 1;
      
      .card-title {
        font-size: 14px;
        color: #8c8c8c;
        margin-bottom: 4px;
      }
      
      .card-value {
        font-size: 18px;
        font-weight: 600;
        color: #262626;
        margin-bottom: 4px;
      }
      
      .card-extra {
        font-size: 12px;
        color: #8c8c8c;
      }
    }
  }
}

.control-panel {
  .control-buttons {
    .ant-btn {
      height: 48px;
      font-size: 16px;
    }
  }
}

.services-panel {
  .services-list {
    .service-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #f0f0f0;
      
      &:last-child {
        border-bottom: none;
      }
      
      .service-info {
        display: flex;
        align-items: center;
        
        .status-indicator {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          margin-right: 8px;
          
          &.running {
            background-color: #52c41a;
          }
          
          &.stopped {
            background-color: #8c8c8c;
          }
          
          &.error {
            background-color: #f5222d;
          }
        }
        
        .service-name {
          font-weight: 500;
        }
      }
    }
  }
}

.quick-nav {
  .nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s;
    
    &:hover {
      background: #f0f0f0;
      transform: translateY(-2px);
    }
    
    .nav-icon {
      font-size: 24px;
      color: #1890ff;
      margin-bottom: 8px;
    }
    
    .nav-text {
      font-size: 14px;
      color: #262626;
    }
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: 16px;
  }
  
  .status-card .card-content {
    .card-icon {
      width: 40px;
      height: 40px;
      font-size: 20px;
      margin-right: 12px;
    }
    
    .card-info .card-value {
      font-size: 16px;
    }
  }
}
</style>
