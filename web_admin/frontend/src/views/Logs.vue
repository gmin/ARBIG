<template>
  <div class="logs-page">
    <a-card title="系统日志">
      <LogViewer />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import LogViewer from '@/components/LogViewer.vue'
</script>

<style scoped lang="scss">
.logs-page {
  padding: 24px;
  height: calc(100vh - 64px);

  .ant-card {
    height: 100%;

    :deep(.ant-card-body) {
      height: calc(100% - 57px);
      padding: 0;
    }
  }
}
</style>
