<template>
  <div class="market-page">
    <!-- 主力合约配置 -->
    <a-card title="主力合约配置" class="mb-4">
      <div class="main-contract-section">
        <a-row :gutter="16" align="middle">
          <a-col :span="6">
            <a-input
              v-model:value="mainContract"
              placeholder="输入主力合约，如: au2509"
              size="large"
              :disabled="loading"
            >
              <template #prefix>
                <StarOutlined style="color: #faad14" />
              </template>
            </a-input>
          </a-col>
          <a-col :span="4">
            <a-button
              type="primary"
              size="large"
              :loading="loading"
              @click="saveMainContract"
            >
              保存主力合约
            </a-button>
          </a-col>
          <a-col :span="14">
            <div class="contract-info">
              <a-tag v-if="currentMainContract" color="gold" class="mr-2">
                <StarOutlined class="mr-1" />
                当前主力合约: {{ currentMainContract }}
              </a-tag>
              <a-tag v-if="contractExpiry" :color="isContractExpired ? 'red' : 'green'">
                {{ isContractExpired ? '已过期' : '有效' }}: {{ contractExpiry }}
              </a-tag>
            </div>
          </a-col>
        </a-row>
      </div>
    </a-card>

    <!-- 实时行情 -->
    <a-card title="实时行情">
      <div v-if="!currentMainContract" class="no-contract">
        <a-empty description="请先设置主力合约">
          <template #image>
            <StarOutlined style="font-size: 48px; color: #faad14;" />
          </template>
        </a-empty>
      </div>
      <div v-else class="market-data">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-statistic
              title="最新价"
              :value="marketData.lastPrice || '--'"
              suffix="元"
              :value-style="{ color: getPriceColor(marketData.change) }"
            />
          </a-col>
          <a-col :span="8">
            <a-statistic
              title="涨跌幅"
              :value="marketData.changePercent || '--'"
              suffix="%"
              :value-style="{ color: getPriceColor(marketData.change) }"
            />
          </a-col>
          <a-col :span="8">
            <a-statistic
              title="成交量"
              :value="marketData.volume || '--'"
              suffix="手"
            />
          </a-col>
        </a-row>

        <a-divider />

        <a-row :gutter="16">
          <a-col :span="6">
            <a-statistic title="开盘价" :value="marketData.openPrice || '--'" suffix="元" />
          </a-col>
          <a-col :span="6">
            <a-statistic title="最高价" :value="marketData.highPrice || '--'" suffix="元" />
          </a-col>
          <a-col :span="6">
            <a-statistic title="最低价" :value="marketData.lowPrice || '--'" suffix="元" />
          </a-col>
          <a-col :span="6">
            <a-statistic title="昨收价" :value="marketData.preClosePrice || '--'" suffix="元" />
          </a-col>
        </a-row>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { StarOutlined } from '@ant-design/icons-vue'

// 响应式数据
const mainContract = ref('')
const currentMainContract = ref('')
const loading = ref(false)
const marketData = ref({
  lastPrice: 0,
  change: 0,
  changePercent: 0,
  volume: 0,
  openPrice: 0,
  highPrice: 0,
  lowPrice: 0,
  preClosePrice: 0
})

// 计算合约到期日期
const contractExpiry = computed(() => {
  if (!currentMainContract.value) return ''

  // 从合约代码提取年月，如 au2509 -> 2025年09月
  const match = currentMainContract.value.match(/(\w+)(\d{4})/)
  if (!match) return ''

  const [, symbol, yearMonth] = match
  const year = '20' + yearMonth.substring(0, 2)
  const month = yearMonth.substring(2, 4)

  return `${year}年${month}月`
})

// 检查合约是否过期
const isContractExpired = computed(() => {
  if (!currentMainContract.value) return false

  const match = currentMainContract.value.match(/(\w+)(\d{4})/)
  if (!match) return false

  const [, symbol, yearMonth] = match
  const year = parseInt('20' + yearMonth.substring(0, 2))
  const month = parseInt(yearMonth.substring(2, 4))

  const now = new Date()
  const contractDate = new Date(year, month - 1) // month is 0-indexed

  return contractDate < now
})

// 获取价格颜色
const getPriceColor = (change: number) => {
  if (change > 0) return '#f5222d' // 红色上涨
  if (change < 0) return '#52c41a' // 绿色下跌
  return '#666666' // 灰色平盘
}

// 加载当前主力合约
const loadMainContract = async () => {
  try {
    const response = await fetch('/api/v1/system/config')
    const data = await response.json()

    if (data.success) {
      currentMainContract.value = data.data.main_contract || ''
      mainContract.value = currentMainContract.value

      // 如果合约为空或已过期，提示用户输入
      if (!currentMainContract.value || isContractExpired.value) {
        message.warning('请设置有效的主力合约')
      }
    }
  } catch (error) {
    console.error('加载主力合约失败:', error)
  }
}

// 保存主力合约
const saveMainContract = async () => {
  if (!mainContract.value.trim()) {
    message.error('请输入主力合约代码')
    return
  }

  loading.value = true
  try {
    const response = await fetch('/api/v1/data/market/subscribe', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        symbol: mainContract.value.trim().toUpperCase(),
        subscriber_id: 'web_admin',
        save_to_config: true
      })
    })

    const data = await response.json()

    if (data.success) {
      currentMainContract.value = mainContract.value.trim().toUpperCase()
      message.success('主力合约保存成功')

      // 开始获取行情数据
      loadMarketData()
    } else {
      message.error(`保存失败: ${data.message}`)
    }
  } catch (error) {
    message.error('保存主力合约失败')
    console.error('保存主力合约失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载行情数据
const loadMarketData = async () => {
  if (!currentMainContract.value) return

  try {
    const response = await fetch(`/api/v1/data/market/price/${currentMainContract.value}`)
    const data = await response.json()

    if (data.success && data.data) {
      marketData.value = {
        lastPrice: data.data.last_price || 0,
        change: data.data.change || 0,
        changePercent: data.data.change_percent || 0,
        volume: data.data.volume || 0,
        openPrice: data.data.open_price || 0,
        highPrice: data.data.high_price || 0,
        lowPrice: data.data.low_price || 0,
        preClosePrice: data.data.pre_close_price || 0
      }
    }
  } catch (error) {
    console.error('加载行情数据失败:', error)
  }
}

// 页面加载时执行
onMounted(() => {
  loadMainContract()

  // 定时刷新行情数据
  setInterval(() => {
    if (currentMainContract.value) {
      loadMarketData()
    }
  }, 5000) // 每5秒刷新一次
})
</script>

<style scoped lang="scss">
.market-page {
  padding: 24px;
}

.mb-4 {
  margin-bottom: 24px;
}

.mr-1 {
  margin-right: 4px;
}

.mr-2 {
  margin-right: 8px;
}

.main-contract-section {
  .contract-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.no-contract {
  text-align: center;
  padding: 40px 0;
}

.market-data {
  .ant-statistic {
    text-align: center;
  }
}
</style>
