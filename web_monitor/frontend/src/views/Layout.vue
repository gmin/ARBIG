<template>
  <a-layout class="layout">
    <!-- 顶部导航 -->
    <a-layout-header class="header">
      <div class="header-left">
        <div class="logo">
          <RocketOutlined class="logo-icon" />
          <span class="logo-text">ARBIG量化交易系统</span>
        </div>
      </div>
      
      <div class="header-center">
        <div class="system-status">
          <span class="status-indicator" :class="systemStatusClass"></span>
          <span class="status-text">{{ systemStatusText }}</span>
          <a-divider type="vertical" />
          <span class="mode-text">{{ currentMode }}</span>
        </div>
      </div>
      
      <div class="header-right">
        <a-space>
          <!-- 系统时间 -->
          <div class="system-time">
            {{ currentTime }}
          </div>
          
          <!-- 紧急停止按钮 -->
          <a-button 
            type="primary" 
            danger 
            size="small"
            @click="showEmergencyModal = true"
          >
            <StopOutlined />
            紧急停止
          </a-button>
          
          <!-- 用户菜单 -->
          <a-dropdown>
            <a-button type="text" class="user-button">
              <UserOutlined />
              管理员
              <DownOutlined />
            </a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item key="profile">
                  <UserOutlined />
                  个人设置
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item key="logout">
                  <LogoutOutlined />
                  退出登录
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </a-space>
      </div>
    </a-layout-header>

    <a-layout>
      <!-- 侧边导航 -->
      <a-layout-sider 
        v-model:collapsed="collapsed" 
        :trigger="null" 
        collapsible
        width="240"
        class="sider"
      >
        <div class="sider-trigger" @click="collapsed = !collapsed">
          <MenuUnfoldOutlined v-if="collapsed" />
          <MenuFoldOutlined v-else />
        </div>
        
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="inline"
          theme="light"
          :inline-collapsed="collapsed"
          @click="handleMenuClick"
        >
          <a-menu-item 
            v-for="route in menuRoutes" 
            :key="route.name"
          >
            <component :is="route.meta?.icon || 'AppstoreOutlined'" />
            <span>{{ route.meta?.title }}</span>
          </a-menu-item>
        </a-menu>
      </a-layout-sider>

      <!-- 主内容区 -->
      <a-layout-content class="content">
        <div class="content-wrapper">
          <router-view />
        </div>
      </a-layout-content>
    </a-layout>

    <!-- 紧急停止确认弹窗 -->
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
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  RocketOutlined,
  UserOutlined,
  DownOutlined,
  LogoutOutlined,
  StopOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined
} from '@ant-design/icons-vue'
import { useSystemStore } from '@/stores/system'
import dayjs from 'dayjs'

const router = useRouter()
const route = useRoute()
const systemStore = useSystemStore()

// 响应式数据
const collapsed = ref(false)
const selectedKeys = ref<string[]>([])
const currentTime = ref('')
const showEmergencyModal = ref(false)
const emergencyReason = ref('')
const emergencyLoading = ref(false)

// 菜单路由
const menuRoutes = computed(() => {
  return router.getRoutes()
    .filter(route => route.meta && !route.meta.hideInMenu && route.name !== 'Layout')
    .sort((a, b) => (a.meta?.order || 0) - (b.meta?.order || 0))
})

// 系统状态
const systemStatusClass = computed(() => {
  if (systemStore.isSystemRunning) return 'running'
  if (systemStore.error) return 'error'
  return 'stopped'
})

const systemStatusText = computed(() => {
  if (systemStore.loading) return '检查中...'
  if (systemStore.isSystemRunning) return '系统运行中'
  if (systemStore.error) return '系统异常'
  return '系统已停止'
})

const currentMode = computed(() => {
  const modeMap: Record<string, string> = {
    'FULL_TRADING': '完整交易模式',
    'MONITOR_ONLY': '仅监控模式',
    'MARKET_DATA_ONLY': '仅行情模式'
  }
  return modeMap[systemStore.currentMode] || systemStore.currentMode
})

// 方法
const updateTime = () => {
  currentTime.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
}

const handleMenuClick = ({ key }: { key: string }) => {
  router.push({ name: key })
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
  } catch (error) {
    message.error('紧急停止执行失败')
  } finally {
    emergencyLoading.value = false
  }
}

// 定时器
let timeTimer: number | null = null
let statusTimer: number | null = null

onMounted(() => {
  // 更新选中的菜单项
  selectedKeys.value = [route.name as string]
  
  // 启动时间更新定时器
  updateTime()
  timeTimer = window.setInterval(updateTime, 1000)
  
  // 启动状态更新定时器
  statusTimer = window.setInterval(() => {
    systemStore.fetchSystemStatus()
  }, 5000)
})

onUnmounted(() => {
  if (timeTimer) {
    clearInterval(timeTimer)
  }
  if (statusTimer) {
    clearInterval(statusTimer)
  }
})

// 监听路由变化
router.afterEach((to) => {
  selectedKeys.value = [to.name as string]
})
</script>

<style scoped lang="scss">
.layout {
  height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #001529;
  color: white;

  .header-left {
    .logo {
      display: flex;
      align-items: center;
      
      .logo-icon {
        font-size: 24px;
        color: #1890ff;
        margin-right: 12px;
      }
      
      .logo-text {
        font-size: 18px;
        font-weight: 600;
        color: white;
      }
    }
  }

  .header-center {
    .system-status {
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
      
      .status-text {
        color: white;
        margin-right: 16px;
      }
      
      .mode-text {
        color: #1890ff;
        font-weight: 500;
      }
    }
  }

  .header-right {
    .system-time {
      color: #8c8c8c;
      font-family: 'SF Mono', Monaco, monospace;
      margin-right: 16px;
    }
    
    .user-button {
      color: white;
      
      &:hover {
        color: #1890ff;
      }
    }
  }
}

.sider {
  background: white;
  border-right: 1px solid #f0f0f0;

  .sider-trigger {
    padding: 16px;
    cursor: pointer;
    transition: color 0.3s;
    text-align: center;
    border-bottom: 1px solid #f0f0f0;
    
    &:hover {
      color: #1890ff;
    }
  }
}

.content {
  background: #f5f5f5;
  
  .content-wrapper {
    height: 100%;
    overflow-y: auto;
  }
}
</style>
