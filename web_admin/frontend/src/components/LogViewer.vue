<template>
  <div class="log-viewer">
    <div class="log-controls">
      <a-row :gutter="16" align="middle">
        <a-col :span="4">
          <a-select
            v-model:value="selectedService"
            placeholder="选择服务"
            @change="loadLogs"
          >
            <a-select-option value="main">主系统</a-select-option>
            <a-select-option value="web_admin">Web管理</a-select-option>
          </a-select>
        </a-col>
        
        <a-col :span="3">
          <a-select
            v-model:value="selectedLevel"
            placeholder="日志级别"
            allow-clear
            @change="loadLogs"
          >
            <a-select-option value="DEBUG">DEBUG</a-select-option>
            <a-select-option value="INFO">INFO</a-select-option>
            <a-select-option value="WARNING">WARNING</a-select-option>
            <a-select-option value="ERROR">ERROR</a-select-option>
          </a-select>
        </a-col>
        
        <a-col :span="4">
          <a-input
            v-model:value="searchKeyword"
            placeholder="搜索关键词"
            @press-enter="loadLogs"
          >
            <template #suffix>
              <SearchOutlined @click="loadLogs" />
            </template>
          </a-input>
        </a-col>
        
        <a-col :span="3">
          <a-input-number
            v-model:value="maxLines"
            :min="10"
            :max="1000"
            placeholder="行数"
            @change="loadLogs"
          />
        </a-col>
        
        <a-col :span="6">
          <a-space>
            <a-button @click="loadLogs" :loading="loading">
              <ReloadOutlined />
              刷新
            </a-button>
            <a-button @click="clearLogs">
              <ClearOutlined />
              清空
            </a-button>
            <a-switch
              v-model:checked="autoRefresh"
              checked-children="自动刷新"
              un-checked-children="手动刷新"
              @change="toggleAutoRefresh"
            />
          </a-space>
        </a-col>
      </a-row>
    </div>

    <div class="log-content">
      <a-spin :spinning="loading">
        <div class="log-info" v-if="logInfo">
          <a-descriptions size="small" :column="4">
            <a-descriptions-item label="文件路径">{{ logInfo.file_path }}</a-descriptions-item>
            <a-descriptions-item label="总行数">{{ logInfo.total_lines }}</a-descriptions-item>
            <a-descriptions-item label="文件大小">{{ formatFileSize(logInfo.file_size) }}</a-descriptions-item>
            <a-descriptions-item label="最后修改">{{ formatTime(logInfo.last_modified) }}</a-descriptions-item>
          </a-descriptions>
        </div>
        
        <div class="log-entries" ref="logContainer">
          <div
            v-for="(entry, index) in logEntries"
            :key="index"
            :class="[
              'log-entry',
              `log-${entry.level.toLowerCase()}`,
              entry.level.toLowerCase() === 'info' ? 'log-info' : '',
              entry.level.toLowerCase() === 'warning' ? 'log-warning' : '',
              entry.level.toLowerCase() === 'error' ? 'log-error' : ''
            ]"
          >
            <span class="log-timestamp">{{ entry.timestamp }}</span>
            <span class="log-level" :class="`level-${entry.level.toLowerCase()}`">
              [{{ entry.level }}]
            </span>
            <span class="log-module">{{ entry.module }}</span>
            <span class="log-message">{{ entry.message }}</span>
          </div>
          
          <div v-if="logEntries.length === 0 && !loading" class="no-logs">
            <a-empty description="暂无日志数据" />
          </div>
        </div>
      </a-spin>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, ReloadOutlined, ClearOutlined } from '@ant-design/icons-vue'
import { logsAPI, type LogEntry, type LogsResponse } from '../api/logs'

// Props
interface Props {
  defaultService?: string
}

const props = withDefaults(defineProps<Props>(), {
  defaultService: 'main'
})

// 响应式数据
const selectedService = ref(props.defaultService)
const selectedLevel = ref<string>()
const searchKeyword = ref('')
const maxLines = ref(100)
const autoRefresh = ref(false)
const loading = ref(false)
const logEntries = ref<LogEntry[]>([])
const logInfo = ref<LogsResponse>()
const logContainer = ref<HTMLElement>()

let refreshTimer: NodeJS.Timeout | null = null

// 加载日志
const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      service: selectedService.value,
      lines: maxLines.value,
      level: selectedLevel.value,
      search: searchKeyword.value || undefined
    }
    
    const response = await logsAPI.getLogContent(params)
    logEntries.value = response.logs
    logInfo.value = response
    
    // 滚动到底部
    await nextTick()
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  } catch (error) {
    message.error('加载日志失败')
    console.error('Load logs error:', error)
  } finally {
    loading.value = false
  }
}

// 清空日志
const clearLogs = () => {
  logEntries.value = []
  logInfo.value = undefined
}

// 切换自动刷新
const toggleAutoRefresh = (checked: boolean) => {
  if (checked) {
    refreshTimer = setInterval(loadLogs, 5000) // 每5秒刷新
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 格式化时间
const formatTime = (timeStr: string): string => {
  return new Date(timeStr).toLocaleString()
}

// 组件挂载
onMounted(() => {
  loadLogs()
})

// 组件卸载
onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.log-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.log-controls {
  padding: 16px;
  background: #fafafa;
  border-bottom: 1px solid #d9d9d9;
}

.log-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.log-info {
  padding: 12px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #d9d9d9;
}

.log-entries {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  background: #1a1a1a;
  color: #e8e8e8;
}

.log-entry {
  padding: 3px 0;
  border-bottom: 1px solid #404040;
}

.log-entry.log-info {
  color: #000000 !important;
  background: rgba(255, 255, 255, 0.9);
  padding: 3px 6px;
  border-radius: 2px;
}

.log-entry.log-info .log-timestamp,
.log-entry.log-info .log-module,
.log-entry.log-info .log-message {
  color: #000000 !important;
}

.log-entry.log-warning {
  color: #000000 !important;
  background: rgba(255, 204, 0, 0.8);
  padding: 3px 6px;
  border-radius: 2px;
}

.log-entry.log-warning .log-timestamp,
.log-entry.log-warning .log-module,
.log-entry.log-warning .log-message {
  color: #000000 !important;
}

.log-entry.log-error {
  color: #ffffff !important;
  background: rgba(255, 107, 107, 0.9);
  padding: 3px 6px;
  border-radius: 2px;
}

.log-entry.log-error .log-timestamp,
.log-entry.log-error .log-module,
.log-entry.log-error .log-message {
  color: #ffffff !important;
}

.log-timestamp {
  color: #87ceeb;
  margin-right: 10px;
  font-weight: 500;
}

.log-level {
  margin-right: 10px;
  font-weight: bold;
  min-width: 70px;
  display: inline-block;
  padding: 1px 4px;
  border-radius: 3px;
}

.level-debug {
  color: #b0b0b0;
  background: rgba(176, 176, 176, 0.1);
}
.level-info {
  color: #000000;
  background: rgba(255, 255, 255, 0.8);
}
.level-warning {
  color: #ffcc00;
  background: rgba(255, 204, 0, 0.1);
}
.level-error {
  color: #ff6b6b;
  background: rgba(255, 107, 107, 0.1);
}

.log-module {
  color: #66d9ef;
  margin-right: 10px;
  font-weight: 500;
}

.log-message {
  color: #f8f8f2;
}

.no-logs {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}
</style>
