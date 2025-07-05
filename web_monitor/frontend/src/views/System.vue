<template>
  <div class="system-page">
    <a-card title="系统控制" class="control-card">
      <a-row :gutter="[16, 16]">
        <a-col :xs="24" :md="12">
          <div class="control-section">
            <h3>系统操作</h3>
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
            </a-space>
          </div>
        </a-col>
        
        <a-col :xs="24" :md="12">
          <div class="status-section">
            <h3>系统状态</h3>
            <a-descriptions :column="1" bordered>
              <a-descriptions-item label="运行状态">
                <a-tag :color="systemStore.isSystemRunning ? 'green' : 'red'">
                  {{ systemStore.isSystemRunning ? '运行中' : '已停止' }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="运行模式">
                {{ currentModeText }}
              </a-descriptions-item>
              <a-descriptions-item label="运行时长">
                {{ systemStore.uptime }}
              </a-descriptions-item>
              <a-descriptions-item label="系统版本">
                v1.0.0
              </a-descriptions-item>
            </a-descriptions>
          </div>
        </a-col>
      </a-row>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { message } from 'ant-design-vue'
import { PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons-vue'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()

const currentModeText = computed(() => {
  const modeMap: Record<string, string> = {
    'FULL_TRADING': '完整交易模式',
    'MONITOR_ONLY': '仅监控模式',
    'MARKET_DATA_ONLY': '仅行情模式'
  }
  return modeMap[systemStore.currentMode] || systemStore.currentMode
})

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
</script>

<style scoped lang="scss">
.system-page {
  padding: 24px;
}

.control-card {
  .control-section, .status-section {
    h3 {
      margin-bottom: 16px;
      color: #262626;
    }
  }
  
  .ant-btn {
    height: 48px;
    font-size: 16px;
  }
}
</style>
