<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-form">
        <div class="login-header">
          <RocketOutlined class="login-icon" />
          <h1>ARBIG量化交易系统</h1>
          <p>Web指挥中轴</p>
        </div>
        
        <a-form
          :model="loginForm"
          @finish="handleLogin"
          layout="vertical"
        >
          <a-form-item
            label="用户名"
            name="username"
            :rules="[{ required: true, message: '请输入用户名' }]"
          >
            <a-input v-model:value="loginForm.username" size="large" />
          </a-form-item>
          
          <a-form-item
            label="密码"
            name="password"
            :rules="[{ required: true, message: '请输入密码' }]"
          >
            <a-input-password v-model:value="loginForm.password" size="large" />
          </a-form-item>
          
          <a-form-item>
            <a-button type="primary" html-type="submit" size="large" block>
              登录
            </a-button>
          </a-form-item>
        </a-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { RocketOutlined } from '@ant-design/icons-vue'

const router = useRouter()

const loginForm = reactive({
  username: '',
  password: ''
})

const handleLogin = () => {
  // 简单的登录逻辑，实际项目中需要调用API
  router.push('/')
}
</script>

<style scoped lang="scss">
.login-page {
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-container {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
  
  .login-icon {
    font-size: 48px;
    color: #1890ff;
    margin-bottom: 16px;
  }
  
  h1 {
    margin: 0 0 8px 0;
    font-size: 24px;
    color: #262626;
  }
  
  p {
    margin: 0;
    color: #8c8c8c;
  }
}
</style>
