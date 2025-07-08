<template>
  <div id="app">
    <a-config-provider :locale="zhCN">
      <router-view />
    </a-config-provider>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()

onMounted(async () => {
  // 初始化系统状态
  try {
    await systemStore.init()
    console.log('✓ 系统状态初始化完成')
  } catch (error) {
    console.error('✗ 系统状态初始化失败:', error)
  }
})
</script>

<style>
#app {
  height: 100vh;
  overflow: hidden;
}
</style>
