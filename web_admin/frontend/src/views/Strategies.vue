<template>
  <div class="strategies-page">
    <!-- 策略管理头部 -->
    <div class="page-header">
      <h2>策略管理</h2>
      <a-space>
        <a-button type="primary" @click="showCreateModal = true">
          <PlusOutlined />
          新建策略
        </a-button>
        <a-button @click="refreshStrategies">
          <ReloadOutlined />
          刷新
        </a-button>
      </a-space>
    </div>

    <!-- 策略列表 -->
    <a-card title="策略列表" class="strategy-list">
      <a-table
        :columns="columns"
        :data-source="strategies"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
      >
        <!-- 策略名称列 -->
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <div class="strategy-name">
              <span class="name">{{ record.name }}</span>
              <a-tag :color="getStatusColor(record.status)" size="small">
                {{ getStatusText(record.status) }}
              </a-tag>
            </div>
          </template>

          <!-- 状态列 -->
          <template v-else-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>

          <!-- 操作列 -->
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button 
                v-if="record.status === 'stopped'"
                type="primary" 
                size="small"
                @click="startStrategy(record)"
                :loading="record.loading"
              >
                启动
              </a-button>
              <a-button 
                v-else-if="record.status === 'running'"
                type="default" 
                size="small"
                @click="stopStrategy(record)"
                :loading="record.loading"
              >
                停止
              </a-button>
              <a-button 
                size="small"
                @click="editStrategy(record)"
              >
                编辑
              </a-button>
              <a-button 
                size="small"
                @click="viewStrategy(record)"
              >
                查看
              </a-button>
              <a-dropdown>
                <a-button size="small">
                  更多
                  <DownOutlined />
                </a-button>
                <template #overlay>
                  <a-menu>
                    <a-menu-item @click="backtestStrategy(record)">
                      <HistoryOutlined />
                      回测
                    </a-menu-item>
                    <a-menu-item @click="viewLogs(record)">
                      <FileTextOutlined />
                      日志
                    </a-menu-item>
                    <a-menu-item @click="exportStrategy(record)">
                      <ExportOutlined />
                      导出
                    </a-menu-item>
                    <a-menu-divider />
                    <a-menu-item danger @click="deleteStrategy(record)">
                      <DeleteOutlined />
                      删除
                    </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新建策略弹窗 -->
    <a-modal
      v-model:open="showCreateModal"
      title="新建策略"
      width="600px"
      @ok="createStrategy"
      @cancel="showCreateModal = false"
    >
      <a-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        layout="vertical"
      >
        <a-form-item label="策略名称" name="name">
          <a-input v-model:value="createForm.name" placeholder="请输入策略名称" />
        </a-form-item>
        <a-form-item label="策略类型" name="type">
          <a-select v-model:value="createForm.type" placeholder="请选择策略类型">
            <a-select-option value="arbitrage">套利策略</a-select-option>
            <a-select-option value="trend">趋势策略</a-select-option>
            <a-select-option value="mean_reversion">均值回归</a-select-option>
            <a-select-option value="custom">自定义策略</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="交易品种" name="symbols">
          <a-select
            v-model:value="createForm.symbols"
            mode="multiple"
            placeholder="请选择交易品种"
          >
            <a-select-option value="au2507">黄金2507</a-select-option>
            <a-select-option value="ag2507">白银2507</a-select-option>
            <a-select-option value="cu2507">铜2507</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="策略描述" name="description">
          <a-textarea
            v-model:value="createForm.description"
            placeholder="请输入策略描述"
            :rows="3"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 策略详情弹窗 -->
    <a-modal
      v-model:open="showDetailModal"
      title="策略详情"
      width="800px"
      :footer="null"
    >
      <div v-if="selectedStrategy" class="strategy-detail">
        <a-descriptions :column="2" bordered>
          <a-descriptions-item label="策略名称">
            {{ selectedStrategy.name }}
          </a-descriptions-item>
          <a-descriptions-item label="策略类型">
            {{ getTypeText(selectedStrategy.type) }}
          </a-descriptions-item>
          <a-descriptions-item label="运行状态">
            <a-tag :color="getStatusColor(selectedStrategy.status)">
              {{ getStatusText(selectedStrategy.status) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="创建时间">
            {{ selectedStrategy.createTime }}
          </a-descriptions-item>
          <a-descriptions-item label="交易品种" :span="2">
            {{ selectedStrategy.symbols?.join(', ') }}
          </a-descriptions-item>
          <a-descriptions-item label="策略描述" :span="2">
            {{ selectedStrategy.description }}
          </a-descriptions-item>
        </a-descriptions>

        <!-- 策略参数 -->
        <div class="strategy-params" style="margin-top: 16px;">
          <h4>策略参数</h4>
          <a-table
            :columns="paramColumns"
            :data-source="selectedStrategy.params || []"
            :pagination="false"
            size="small"
          />
        </div>

        <!-- 策略统计 -->
        <div class="strategy-stats" style="margin-top: 16px;">
          <h4>策略统计</h4>
          <a-row :gutter="16">
            <a-col :span="6">
              <a-statistic title="总收益" :value="selectedStrategy.totalReturn" suffix="%" />
            </a-col>
            <a-col :span="6">
              <a-statistic title="夏普比率" :value="selectedStrategy.sharpeRatio" />
            </a-col>
            <a-col :span="6">
              <a-statistic title="最大回撤" :value="selectedStrategy.maxDrawdown" suffix="%" />
            </a-col>
            <a-col :span="6">
              <a-statistic title="胜率" :value="selectedStrategy.winRate" suffix="%" />
            </a-col>
          </a-row>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  ReloadOutlined,
  DownOutlined,
  HistoryOutlined,
  FileTextOutlined,
  ExportOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue'

// 响应式数据
const loading = ref(false)
const strategies = ref([])
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const selectedStrategy = ref(null)

// 分页配置
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total: number) => `共 ${total} 条记录`
})

// 新建策略表单
const createForm = reactive({
  name: '',
  type: '',
  symbols: [],
  description: ''
})

const createRules = {
  name: [{ required: true, message: '请输入策略名称' }],
  type: [{ required: true, message: '请选择策略类型' }],
  symbols: [{ required: true, message: '请选择交易品种' }]
}

// 表格列定义
const columns = [
  {
    title: '策略名称',
    key: 'name',
    dataIndex: 'name',
    width: 200
  },
  {
    title: '类型',
    key: 'type',
    dataIndex: 'type',
    width: 120,
    customRender: ({ text }: { text: string }) => getTypeText(text)
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 100
  },
  {
    title: '交易品种',
    key: 'symbols',
    dataIndex: 'symbols',
    customRender: ({ text }: { text: string[] }) => text?.join(', ')
  },
  {
    title: '总收益',
    key: 'totalReturn',
    dataIndex: 'totalReturn',
    width: 100,
    customRender: ({ text }: { text: number }) => `${text?.toFixed(2)}%`
  },
  {
    title: '创建时间',
    key: 'createTime',
    dataIndex: 'createTime',
    width: 180
  },
  {
    title: '操作',
    key: 'action',
    width: 200,
    fixed: 'right'
  }
]

// 参数表格列定义
const paramColumns = [
  {
    title: '参数名',
    key: 'name',
    dataIndex: 'name'
  },
  {
    title: '参数值',
    key: 'value',
    dataIndex: 'value'
  },
  {
    title: '描述',
    key: 'description',
    dataIndex: 'description'
  }
]

// 方法
const getStatusColor = (status: string) => {
  const colors = {
    running: 'green',
    stopped: 'red',
    paused: 'orange',
    error: 'red'
  }
  return colors[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts = {
    running: '运行中',
    stopped: '已停止',
    paused: '已暂停',
    error: '错误'
  }
  return texts[status] || status
}

const getTypeText = (type: string) => {
  const texts = {
    arbitrage: '套利策略',
    trend: '趋势策略',
    mean_reversion: '均值回归',
    custom: '自定义策略'
  }
  return texts[type] || type
}

const refreshStrategies = async () => {
  loading.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    strategies.value = [
      {
        id: '1',
        name: '黄金套利策略',
        type: 'arbitrage',
        status: 'running',
        symbols: ['au2507', 'au2508'],
        totalReturn: 15.6,
        createTime: '2024-01-15 10:30:00',
        description: '基于黄金期货价差的套利策略'
      },
      {
        id: '2',
        name: '趋势跟踪策略',
        type: 'trend',
        status: 'stopped',
        symbols: ['cu2507'],
        totalReturn: 8.2,
        createTime: '2024-01-10 14:20:00',
        description: '基于移动平均线的趋势跟踪策略'
      }
    ]
    message.success('策略列表刷新成功')
  } catch (error) {
    message.error('刷新策略列表失败')
  } finally {
    loading.value = false
  }
}

const startStrategy = async (strategy: any) => {
  strategy.loading = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    strategy.status = 'running'
    message.success(`策略 ${strategy.name} 启动成功`)
  } catch (error) {
    message.error('启动策略失败')
  } finally {
    strategy.loading = false
  }
}

const stopStrategy = async (strategy: any) => {
  strategy.loading = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    strategy.status = 'stopped'
    message.success(`策略 ${strategy.name} 停止成功`)
  } catch (error) {
    message.error('停止策略失败')
  } finally {
    strategy.loading = false
  }
}

const editStrategy = (strategy: any) => {
  message.info('编辑策略功能开发中...')
}

const viewStrategy = (strategy: any) => {
  selectedStrategy.value = strategy
  showDetailModal.value = true
}

const backtestStrategy = (strategy: any) => {
  message.info('回测功能开发中...')
}

const viewLogs = (strategy: any) => {
  message.info('查看日志功能开发中...')
}

const exportStrategy = (strategy: any) => {
  message.info('导出策略功能开发中...')
}

const deleteStrategy = (strategy: any) => {
  message.info('删除策略功能开发中...')
}

const createStrategy = async () => {
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    showCreateModal.value = false
    message.success('策略创建成功')
    refreshStrategies()
  } catch (error) {
    message.error('创建策略失败')
  }
}

// 生命周期
onMounted(() => {
  refreshStrategies()
})
</script>

<style scoped lang="scss">
.strategies-page {
  padding: 24px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }
  }

  .strategy-list {
    .strategy-name {
      display: flex;
      align-items: center;
      gap: 8px;

      .name {
        font-weight: 500;
      }
    }
  }

  .strategy-detail {
    .strategy-params,
    .strategy-stats {
      h4 {
        margin-bottom: 12px;
        font-weight: 600;
      }
    }
  }
}
</style>
