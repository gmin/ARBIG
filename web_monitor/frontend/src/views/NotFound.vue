<template>
  <div class="not-found-page">
    <a-result
      status="404"
      title="404"
      sub-title="抱歉，您访问的页面不存在。"
    >
      <template #extra>
        <a-button type="primary" @click="$router.push('/')">
          返回首页
        </a-button>
      </template>
    </a-result>
  </div>
</template>

<script setup lang="ts">
// 404页面
</script>

<style scoped lang="scss">
.not-found-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
