<template>
  <div class="dashboard">
    <!-- 顶部状态栏 - 固定显示关键状态 -->
    <div class="status-bar">
    <a-row :gutter="[16, 16]">
        <a-col :xs="12" :sm="6" :md="4" :lg="3">
          <div class="status-item" :class="systemStatusClass">
            <div class="status-icon">
              <RocketOutlined />
            </div>
            <div class="status-info">
              <div class="status-label">系统状态</div>
              <div class="status-value">{{ systemStatusText }}</div>
            </div>
          </div>
      </a-col>

        <a-col :xs="12" :sm="6" :md="4" :lg="3">
          <div class="status-item">
            <div class="status-icon mode-status">
              <SettingOutlined />
            </div>
            <div class="status-info">
              <div class="status-label">运行模式</div>
              <div class="status-value">{{ currentModeText }}</div>
              </div>
            </div>
      </a-col>

        <a-col :xs="12" :sm="6" :md="4" :lg="3">
          <div class="status-item">
            <div class="status-icon services-status">
              <AppstoreOutlined />
            </div>
            <div class="status-info">
              <div class="status-label">服务状态</div>
              <div class="status-value">{{ runningServicesCount }}/{{ totalServicesCount }}</div>
            </div>
          </div>
      </a-col>

        <a-col :xs="12" :sm="6" :md="4" :lg="3">
          <div class="status-item" :class="ctpStatusClass">
            <div class="status-icon">
              <ApiOutlined />
            </div>
            <div class="status-info">
              <div class="status-label">CTP连接</div>
              <div class="status-value">{{ ctpStatusText }}</div>
            </div>
          </div>
        </a-col>
        
        <a-col :xs="12" :sm="6" :md="4" :lg="3">
          <div class="status-item" :class="commStatusClass">
            <div class="status-icon">
              <ApiOutlined />
            </div>
            <div class="status-info">
              <div class="status-label">主系统通信</div>
              <div class="status-value">{{ commStatusText }}</div>
            </div>
          </div>
        </a-col>
        
        <a-col :xs="12" :sm="6" :md="4" :lg="3">
          <div class="status-item">
            <div class="status-icon uptime-status">
              <ClockCircleOutlined />
            </div>
            <div class="status-info">
              <div class="status-label">运行时长</div>
              <div class="status-value">{{ uptime }}</div>
            </div>
          </div>
      </a-col>
    </a-row>
    </div>

    <!-- 控制面板区域 -->
    <div class="control-section">
      <a-row :gutter="[16, 16]">
        <!-- 系统控制卡片 -->
        <a-col :xs="24" :lg="8">
          <a-card title="ARBIG主系统控制" class="control-card">
            <template #extra>
              <a-tag :color="systemStore.isSystemRunning ? 'green' : 'red'">
                {{ systemStore.isSystemRunning ? '运行中' : '已停止' }}
              </a-tag>
            </template>
            
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
              
              <a-button 
                type="dashed" 
                size="large" 
                block
                @click="showModeModal = true"
              >
                <SettingOutlined />
                切换模式
              </a-button>
            </a-space>
        </a-card>
      </a-col>

        <!-- 服务管理卡片 -->
        <a-col :xs="24" :lg="8">
          <a-card title="服务管理" class="control-card">
            <template #extra>
              <a-button type="link" size="small" @click="refreshServices">
                <ReloadOutlined />
              </a-button>
            </template>
            
          <div class="services-list">
            <div v-if="systemStore.services.length === 0" class="empty-services">
              <a-empty 
                description="暂无服务信息" 
                :image="Empty.PRESENTED_IMAGE_SIMPLE"
              >
                <template #description>
                  <span>ARBIG主系统未运行</span>
                  <br>
                  <span style="font-size: 12px; color: #999;">启动主系统后可管理以下服务：</span>
                  <br>
                  <span style="font-size: 11px; color: #666; margin-top: 8px; display: block;">
                    • CTP网关服务<br>
                    • 行情数据服务<br>
                    • 交易执行服务<br>
                    • 风险控制服务<br>
                    • 策略管理服务
                  </span>
                </template>
              </a-empty>
            </div>
            <div 
              v-else
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

        <!-- 快速操作卡片 -->
        <a-col :xs="24" :lg="8">
          <a-card title="快速操作" class="control-card">
            <template #extra>
              <a-tag color="blue">快捷入口</a-tag>
            </template>
            
            <a-space direction="vertical" style="width: 100%">
              <a-button 
                type="primary" 
                ghost
                size="large" 
                block
                @click="$router.push('/trading')"
              >
                <ShoppingCartOutlined />
                交易操作
              </a-button>
              
              <a-button 
                type="primary" 
                ghost
                size="large" 
                block
                @click="$router.push('/strategies')"
              >
                <RocketOutlined />
                策略管理
              </a-button>
              
              <a-button 
                type="primary" 
                ghost
                size="large" 
                block
                @click="$router.push('/risk')"
              >
                <SafetyOutlined />
                风险控制
              </a-button>
              
              <a-button 
                type="primary" 
                ghost
                size="large" 
                block
                @click="$router.push('/logs')"
              >
                <FileTextOutlined />
                系统日志
              </a-button>
            </a-space>
          </a-card>
        </a-col>
    </a-row>
    </div>

    <!-- 数据概览区域 -->
    <div class="data-section">
      <a-row :gutter="[16, 16]">
        <!-- 账户概览卡片 -->
        <a-col :xs="24" :lg="8">
          <a-card title="账户概览" class="data-card">
            <template #extra>
              <a-button type="link" size="small" @click="$router.push('/account')">
                详情
              </a-button>
            </template>
            
            <div class="account-overview">
              <div class="overview-item">
                <div class="overview-label">总资金</div>
                <div class="overview-value">¥{{ accountInfo.balance?.toLocaleString() || '--' }}</div>
              </div>
              <div class="overview-item">
                <div class="overview-label">可用资金</div>
                <div class="overview-value">¥{{ accountInfo.available?.toLocaleString() || '--' }}</div>
              </div>
              <div class="overview-item">
                <div class="overview-label">冻结资金</div>
                <div class="overview-value">¥{{ accountInfo.frozen?.toLocaleString() || '--' }}</div>
              </div>
              <div class="overview-item">
                <div class="overview-label">保证金</div>
                <div class="overview-value">¥{{ accountInfo.margin?.toLocaleString() || '--' }}</div>
              </div>
            </div>
          </a-card>
        </a-col>

        <!-- 风险监控卡片 -->
        <a-col :xs="24" :lg="8">
          <a-card title="风险监控" class="data-card">
            <template #extra>
              <a-button type="link" size="small" @click="$router.push('/risk')">
                详情
              </a-button>
            </template>
            
            <div class="risk-overview">
              <div class="overview-item">
                <div class="overview-label">总盈亏</div>
                <div class="overview-value" :class="getPnLClass(riskMetrics.total_pnl)">
                  {{ riskMetrics.total_pnl > 0 ? '+' : '' }}¥{{ riskMetrics.total_pnl?.toLocaleString() || '--' }}
                </div>
              </div>
              <div class="overview-item">
                <div class="overview-label">今日盈亏</div>
                <div class="overview-value" :class="getPnLClass(riskMetrics.today_pnl)">
                  {{ riskMetrics.today_pnl > 0 ? '+' : '' }}¥{{ riskMetrics.today_pnl?.toLocaleString() || '--' }}
                </div>
              </div>
              <div class="overview-item">
                <div class="overview-label">最大回撤</div>
                <div class="overview-value risk-warning">
                  ¥{{ riskMetrics.max_drawdown?.toLocaleString() || '--' }}
                </div>
              </div>
              <div class="overview-item">
                <div class="overview-label">风险等级</div>
                <div class="overview-value">
                  <a-tag :color="getRiskLevelColor(riskMetrics.risk_level)">
                    {{ riskMetrics.risk_level || '--' }}
                  </a-tag>
                </div>
              </div>
            </div>
          </a-card>
        </a-col>

        <!-- 交易统计卡片 -->
        <a-col :xs="24" :lg="8">
          <a-card title="交易统计" class="data-card">
            <template #extra>
              <a-button type="link" size="small" @click="$router.push('/trading')">
                详情
              </a-button>
            </template>
            
            <div class="trading-overview">
              <div class="overview-item">
                <div class="overview-label">总交易次数</div>
                <div class="overview-value">{{ tradingSummary.total_trades || '--' }}</div>
              </div>
              <div class="overview-item">
                <div class="overview-label">胜率</div>
                <div class="overview-value">{{ tradingSummary.win_rate || '--' }}%</div>
              </div>
              <div class="overview-item">
                <div class="overview-label">平均盈亏</div>
                <div class="overview-value" :class="getPnLClass(tradingSummary.avg_trade_pnl)">
                  {{ tradingSummary.avg_trade_pnl > 0 ? '+' : '' }}¥{{ tradingSummary.avg_trade_pnl?.toLocaleString() || '--' }}
                </div>
              </div>
              <div class="overview-item">
                <div class="overview-label">持仓数量</div>
                <div class="overview-value">{{ positions.length || '--' }}</div>
              </div>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </div>

    <!-- 实时行情区域 - 可折叠 -->
    <div class="market-section">
      <a-card 
        title="实时行情" 
        class="market-card"
        :bordered="false"
      >
        <template #extra>
          <a-space>
            <!-- 合约输入和订阅 -->
            <a-space>
              <a-select
                v-model:value="selectedContract"
                placeholder="选择合约"
                style="width: 150px"
                :loading="contractsLoading"
                @change="handleContractChange"
                show-search
                filter-option
              >
                <a-select-option 
                  v-for="contract in availableContracts" 
                  :key="contract.symbol" 
                  :value="contract.symbol"
                >
                  {{ contract.symbol }} - {{ contract.name }}
                </a-select-option>
              </a-select>
              <a-input
                v-model:value="customContract"
                placeholder="或输入合约代码"
                style="width: 120px"
                @pressEnter="handleCustomContract"
              />
              <a-button 
                type="primary" 
                @click="subscribeContract"
                :loading="subscribeLoading"
              >
                订阅
              </a-button>
            </a-space>
            
            <a-tag :color="marketDataLoading ? 'blue' : 'green'">
              {{ marketDataLoading ? '更新中...' : '实时' }}
            </a-tag>
            <a-button 
              type="link" 
              size="small" 
              @click="fetchMarketData"
              :loading="marketDataLoading"
            >
              刷新
            </a-button>
            <a-button 
              type="link" 
              size="small" 
              @click="toggleMarketSection"
            >
              {{ marketSectionCollapsed ? '展开' : '收起' }}
            </a-button>
          </a-space>
        </template>
        
        <a-collapse :activeKey="marketSectionCollapsed ? [] : ['market']">
          <a-collapse-panel key="market" :show-arrow="false">
            <a-table 
              :columns="marketColumns" 
              :data-source="marketData" 
              :pagination="false"
              size="small"
              :loading="marketDataLoading"
              row-key="symbol"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'symbol'">
                  <a-tag color="gold">{{ record.symbol }}</a-tag>
                </template>
                <template v-else-if="column.key === 'last_price'">
                  <span class="price" :class="getPriceClass(record.change)">
                    {{ record.last_price }}
                  </span>
                </template>
                <template v-else-if="column.key === 'change'">
                  <span :class="getPriceClass(record.change)">
                    {{ record.change > 0 ? '+' : '' }}{{ record.change }}
                  </span>
                </template>
                <template v-else-if="column.key === 'change_percent'">
                  <span :class="getPriceClass(record.change)">
                    {{ record.change > 0 ? '+' : '' }}{{ record.change_percent }}%
                  </span>
                </template>
                <template v-else-if="column.key === 'bid_ask'">
                  <div class="bid-ask">
                    <div class="bid">{{ record.bid_price }}</div>
                    <div class="ask">{{ record.ask_price }}</div>
                  </div>
                </template>
                <template v-else-if="column.key === 'volume'">
                  <span class="volume">{{ record.volume }}</span>
                </template>
                <template v-else-if="column.key === 'timestamp'">
                  <span class="timestamp">{{ record.timestamp }}</span>
                </template>
              </template>
            </a-table>
          </a-collapse-panel>
        </a-collapse>
      </a-card>
    </div>

    <!-- 快速导航区域 - 可折叠 -->
    <div class="nav-section">
      <a-card title="快速导航" class="nav-card" :bordered="false">
        <template #extra>
          <a-button 
            type="link" 
            size="small" 
            @click="toggleNavSection"
          >
            {{ navSectionCollapsed ? '展开' : '收起' }}
          </a-button>
        </template>
        
        <a-collapse :activeKey="navSectionCollapsed ? [] : ['nav']">
          <a-collapse-panel key="nav" :show-arrow="false">
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
          </a-collapse-panel>
        </a-collapse>
        </a-card>
    </div>

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
import { message, Empty } from 'ant-design-vue'
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
  FileTextOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  ShoppingCartOutlined
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

// 行情数据相关
const marketData = ref([])
const marketDataLoading = ref(false)
const marketTimer = ref<number | null>(null)

// 合约订阅相关
interface Contract {
  symbol: string
  name: string
  exchange: string
  category: string
}

const availableContracts = ref<Contract[]>([])
const contractsLoading = ref(false)
const selectedContract = ref('au2507')
const customContract = ref('')
const subscribedContracts = ref(['au2507']) // 当前订阅的合约列表
const subscribeLoading = ref(false)

// 通信状态相关
const commStats = ref({
  connection_status: 'disconnected',
  total_requests: 0,
  successful_requests: 0,
  failed_requests: 0,
  current_endpoint: null
})
const commTimer = ref<number | null>(null)

// 可折叠区域控制
const marketSectionCollapsed = ref(false)
const navSectionCollapsed = ref(false)

// 账户和风险数据
const accountInfo = ref({
  balance: 0,
  available: 0,
  frozen: 0,
  margin: 0
})

const riskMetrics = ref({
  total_pnl: 0,
  today_pnl: 0,
  max_drawdown: 0,
  risk_level: 'LOW'
})

const tradingSummary = ref({
  total_trades: 0,
  win_rate: 0,
  avg_trade_pnl: 0
})

const positions = ref([])

// 行情表格列定义
const marketColumns = [
  {
    title: '合约',
    key: 'symbol',
    width: 100,
    fixed: 'left'
  },
  {
    title: '最新价',
    key: 'last_price',
    width: 100,
    align: 'right'
  },
  {
    title: '涨跌',
    key: 'change',
    width: 80,
    align: 'right'
  },
  {
    title: '涨跌幅',
    key: 'change_percent',
    width: 80,
    align: 'right'
  },
  {
    title: '买一/卖一',
    key: 'bid_ask',
    width: 120,
    align: 'right'
  },
  {
    title: '成交量',
    key: 'volume',
    width: 100,
    align: 'right'
  },
  {
    title: '持仓量',
    key: 'open_interest',
    width: 100,
    align: 'right'
  },
  {
    title: '最高',
    key: 'high',
    width: 80,
    align: 'right'
  },
  {
    title: '最低',
    key: 'low',
    width: 80,
    align: 'right'
  },
  {
    title: '开盘',
    key: 'open',
    width: 80,
    align: 'right'
  },
  {
    title: '时间',
    key: 'timestamp',
    width: 80,
    align: 'center'
  }
]

// 计算属性
const systemStatusClass = computed(() => {
  if (systemStore.isSystemRunning) return 'running'
  if (systemStore.error) return 'error'
  return 'stopped'
})

const systemStatusText = computed(() => {
  if (systemStore.loading) return '检查中...'
  if (systemStore.isSystemRunning) return '运行中'
  if (systemStore.error) return '主系统未连接'
  return '主系统已停止'
})

const uptime = computed(() => systemStore.uptime)

const currentModeText = computed(() => {
  if (systemStore.error || systemStore.currentMode === 'UNKNOWN') {
    return 'Web管理模式'
  }
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

// 通信状态计算属性
const commStatusClass = computed(() => {
  const status = commStats.value.connection_status
  if (status === 'connected') return 'running'
  if (status === 'connecting') return 'warning'
  return 'stopped'
})

const commStatusText = computed(() => {
  const status = commStats.value.connection_status
  if (status === 'connected') return '已连接'
  if (status === 'connecting') return '连接中'
  if (status === 'error') return '连接错误'
  return '未连接'
})

const commSuccessRate = computed(() => {
  const { total_requests, successful_requests } = commStats.value
  if (total_requests === 0) return '0%'
  const rate = (successful_requests / total_requests) * 100
  return `${rate.toFixed(1)}%`
})

// 方法
const handleStartSystem = async () => {
  console.log('点击启动系统按钮')
  try {
    const success = await systemStore.startSystem()
    console.log('启动系统结果:', success)
    if (success) {
      message.success('系统启动成功')
    } else {
      message.error('系统启动失败')
    }
  } catch (error) {
    console.error('启动系统错误:', error)
    message.error('启动系统时发生错误')
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

// 合约相关方法
const fetchAvailableContracts = async () => {
  try {
    console.log('开始获取合约列表...')
    contractsLoading.value = true
    const response = await fetch('/api/v1/data/market/contracts')
    const result = await response.json()
    
    console.log('合约列表API响应:', result)
    
    if (result.success) {
      availableContracts.value = result.data.contracts || []
      console.log('成功加载合约列表，数量:', availableContracts.value.length)
    } else {
      console.error('获取合约列表失败:', result.message)
      message.error('获取合约列表失败')
    }
  } catch (error) {
    console.error('获取合约列表错误:', error)
    message.error('获取合约列表失败')
  } finally {
    contractsLoading.value = false
  }
}

const handleContractChange = (value: string) => {
  selectedContract.value = value
  customContract.value = '' // 清空自定义输入
}

const handleCustomContract = () => {
  if (customContract.value.trim()) {
    selectedContract.value = customContract.value.trim().toUpperCase()
  }
}

const subscribeContract = async () => {
  if (!selectedContract.value) {
    message.warning('请选择或输入合约代码')
    return
  }
  
  try {
    subscribeLoading.value = true
    
    // 检查合约是否已经在订阅列表中
    if (subscribedContracts.value.includes(selectedContract.value)) {
      message.info('该合约已在订阅列表中')
      return
    }
    
    // 添加到订阅列表
    subscribedContracts.value.push(selectedContract.value)
    
    // 立即获取该合约的行情数据
    await fetchMarketData()
    
    message.success(`成功订阅合约: ${selectedContract.value}`)
    
    // 清空选择
    selectedContract.value = ''
    customContract.value = ''
    
  } catch (error) {
    console.error('订阅合约错误:', error)
    message.error('订阅合约失败')
  } finally {
    subscribeLoading.value = false
  }
}

// 行情数据相关方法
const fetchMarketData = async () => {
  try {
    marketDataLoading.value = true
    
    // 使用当前订阅的合约列表
    const symbols = subscribedContracts.value.join(',')
    const response = await fetch(`/api/v1/data/market/ticks?symbols=${symbols}`)
    const result = await response.json()
    
    if (result.success) {
      marketData.value = result.data.ticks || []
    } else {
      message.error('获取行情数据失败')
    }
  } catch (error) {
    console.error('获取行情数据错误:', error)
    message.error('获取行情数据失败')
  } finally {
    marketDataLoading.value = false
  }
}

const getPriceClass = (change: number) => {
  if (change > 0) return 'price-up'
  if (change < 0) return 'price-down'
  return 'price-unchanged'
}

const startMarketTimer = () => {
  // 立即获取一次数据
  fetchMarketData()
  
  // 每2秒更新一次行情
  marketTimer.value = setInterval(() => {
    fetchMarketData()
  }, 2000)
}

const stopMarketTimer = () => {
  if (marketTimer.value) {
    clearInterval(marketTimer.value)
    marketTimer.value = null
  }
}

// 通信状态相关方法
const fetchCommStats = async () => {
  try {
    const response = await fetch('/api/communication/stats')
    const result = await response.json()
    
    if (result.success) {
      commStats.value = result.data
    }
  } catch (error) {
    console.error('获取通信统计信息失败:', error)
  }
}

const startCommTimer = () => {
  // 立即获取一次数据
  fetchCommStats()
  
  // 每10秒更新一次通信状态
  commTimer.value = setInterval(() => {
    fetchCommStats()
  }, 10000)
}

const stopCommTimer = () => {
  if (commTimer.value) {
    clearInterval(commTimer.value)
    commTimer.value = null
  }
}

// 可折叠区域控制方法
const toggleMarketSection = () => {
  marketSectionCollapsed.value = !marketSectionCollapsed.value
}

const toggleNavSection = () => {
  navSectionCollapsed.value = !navSectionCollapsed.value
}

// 数据获取方法
const fetchAccountInfo = async () => {
  try {
    const response = await fetch('/api/v1/data/account/info')
    const result = await response.json()
    
    if (result.success) {
      accountInfo.value = result.data
    }
  } catch (error) {
    console.error('获取账户信息失败:', error)
  }
}

const fetchRiskMetrics = async () => {
  try {
    const response = await fetch('/api/v1/data/risk/metrics')
    const result = await response.json()
    
    if (result.success) {
      riskMetrics.value = result.data
    }
  } catch (error) {
    console.error('获取风险指标失败:', error)
  }
}

const fetchTradingSummary = async () => {
  try {
    const response = await fetch('/api/trading/summary')
    const result = await response.json()
    
    if (result.success) {
      tradingSummary.value = result.data
    }
  } catch (error) {
    console.error('获取交易统计失败:', error)
  }
}

const fetchPositions = async () => {
  try {
    const response = await fetch('/api/v1/data/account/positions')
    const result = await response.json()
    
    if (result.success) {
      positions.value = result.data || []
    }
  } catch (error) {
    console.error('获取持仓信息失败:', error)
  }
}

// 工具方法
const getPnLClass = (pnl: number) => {
  if (pnl > 0) return 'pnl-positive'
  if (pnl < 0) return 'pnl-negative'
  return 'pnl-neutral'
}

const getRiskLevelColor = (level: string) => {
  const colorMap: Record<string, string> = {
    'LOW': 'green',
    'MEDIUM': 'orange',
    'HIGH': 'red',
    'CRITICAL': 'red'
  }
  return colorMap[level] || 'default'
}

const refreshServices = () => {
  systemStore.fetchServices()
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
  
  // 获取可用合约列表
  fetchAvailableContracts()
  
  // 启动行情定时器
  startMarketTimer()
  
  // 启动通信状态定时器
  startCommTimer()
  
  // 获取初始数据
  fetchAccountInfo()
  fetchRiskMetrics()
  fetchTradingSummary()
  fetchPositions()
  
  // 启动数据定时刷新
  const dataRefreshTimer = window.setInterval(() => {
    fetchAccountInfo()
    fetchRiskMetrics()
    fetchTradingSummary()
    fetchPositions()
  }, 10000)
  
  // 保存定时器引用以便清理
  ;(window as any).dataRefreshTimer = dataRefreshTimer
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  
  // 清理数据刷新定时器
  if ((window as any).dataRefreshTimer) {
    clearInterval((window as any).dataRefreshTimer)
  }
  
  // 停止行情定时器
  stopMarketTimer()
  
  // 停止通信状态定时器
  stopCommTimer()
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
      
      &.comm-status {
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

// 新的Dashboard布局样式
.status-bar {
  background: #fff;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 16px;
  
  .status-item {
    display: flex;
    align-items: center;
    padding: 12px;
    border-radius: 6px;
    background: #fafafa;
    transition: all 0.3s;
    
    &:hover {
      background: #f0f0f0;
    }
    
    .status-icon {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 12px;
      font-size: 18px;
      
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
      
      &.mode-status {
        background: #e6f7ff;
        color: #1890ff;
      }
      
      &.services-status {
        background: #f9f0ff;
        color: #722ed1;
      }
      
      &.uptime-status {
        background: #fff7e6;
        color: #fa8c16;
      }
    }
    
    .status-info {
      flex: 1;
      
      .status-label {
        font-size: 12px;
        color: #8c8c8c;
        margin-bottom: 2px;
      }
      
      .status-value {
        font-size: 16px;
        font-weight: 600;
        color: #262626;
      }
    }
  }
}

.control-section {
  margin-bottom: 16px;
  
  .control-card {
    height: 100%;
    
    .ant-card-head {
      border-bottom: 1px solid #f0f0f0;
    }
    
    .ant-card-body {
      padding: 16px;
    }
  }
}

.market-section {
  margin-bottom: 16px;
  
  .market-card {
    .ant-card-head {
      background: #fafafa;
    }
  }
}

.data-section {
  margin-bottom: 16px;
  
  .data-card {
    height: 100%;
    
    .overview-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid #f0f0f0;
      
      &:last-child {
        border-bottom: none;
      }
      
      .overview-label {
        font-size: 14px;
        color: #8c8c8c;
      }
      
      .overview-value {
        font-size: 16px;
        font-weight: 600;
        color: #262626;
        
        &.pnl-positive {
          color: #52c41a;
        }
        
        &.pnl-negative {
          color: #f5222d;
        }
        
        &.pnl-neutral {
          color: #8c8c8c;
        }
        
        &.risk-warning {
          color: #fa8c16;
        }
      }
    }
  }
}

.nav-section {
  .nav-card {
    .nav-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
      border: 1px solid #f0f0f0;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.3s;
      
      &:hover {
        border-color: #1890ff;
        background: #f6ffed;
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

// 行情面板样式
.market-panel {
  .ant-table {
    .ant-table-tbody > tr > td {
      padding: 8px 12px;
    }
  }
  
  .price {
    font-weight: 600;
    font-size: 14px;
    
    &.price-up {
      color: #f5222d;
    }
    
    &.price-down {
      color: #52c41a;
    }
    
    &.price-unchanged {
      color: #262626;
    }
  }
  
  .bid-ask {
    display: flex;
    flex-direction: column;
    gap: 2px;
    
    .bid {
      color: #52c41a;
      font-size: 12px;
    }
    
    .ask {
      color: #f5222d;
      font-size: 12px;
    }
  }
  
  .volume {
    color: #1890ff;
    font-weight: 500;
  }
  
  .timestamp {
    color: #8c8c8c;
    font-size: 12px;
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

