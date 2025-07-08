<template>
  <div class="services-page">
    <a-card title="服务管理">
      <a-table 
        :columns="columns" 
        :data-source="systemStore.services"
        :loading="systemStore.loading"
        row-key="name"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>
          
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button 
                v-if="record.status === 'stopped'"
                type="primary" 
                size="small"
                @click="handleStartService(record.name)"
              >
                启动
              </a-button>
              <a-button 
                v-else-if="record.status === 'running'"
                size="small"
                @click="handleStopService(record.name)"
              >
                停止
              </a-button>
              <a-button 
                size="small"
                @click="handleRestartService(record.name)"
                :disabled="record.status !== 'running'"
              >
                重启
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { message } from 'ant-design-vue'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()

const columns = [
  {
    title: '服务名称',
    dataIndex: 'display_name',
    key: 'display_name',
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
  },
  {
    title: '运行时长',
    dataIndex: 'uptime',
    key: 'uptime',
  },
  {
    title: '是否必需',
    dataIndex: 'required',
    key: 'required',
    customRender: ({ text }: { text: boolean }) => text ? '是' : '否'
  },
  {
    title: '操作',
    key: 'actions',
  },
]

const getStatusColor = (status: string) => {
  const colorMap: Record<string, string> = {
    'running': 'green',
    'stopped': 'default',
    'error': 'red',
    'starting': 'blue',
    'stopping': 'orange'
  }
  return colorMap[status] || 'default'
}

const getStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    'running': '运行中',
    'stopped': '已停止',
    'error': '错误',
    'starting': '启动中',
    'stopping': '停止中'
  }
  return textMap[status] || status
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

const handleRestartService = async (serviceName: string) => {
  const success = await systemStore.restartService(serviceName)
  if (success) {
    message.success(`${serviceName}重启成功`)
  }
}
</script>

<style scoped lang="scss">
.services-page {
  padding: 24px;
}
</style>
