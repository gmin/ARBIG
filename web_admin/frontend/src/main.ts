import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// Ant Design Vue
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

// 全局样式
import './styles/global.scss'

// 创建应用
const app = createApp(App)

// 使用插件
app.use(createPinia())
app.use(router)
app.use(Antd)

// 挂载应用
app.mount('#app')

console.log('🚀 ARBIG Web指挥中轴已启动')
