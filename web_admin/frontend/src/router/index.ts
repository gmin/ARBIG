/**
 * 路由配置
 */

import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: {
          title: '系统概览',
          icon: 'DashboardOutlined'
        }
      },
      {
        path: '/system',
        name: 'System',
        component: () => import('@/views/System.vue'),
        meta: {
          title: '系统控制',
          icon: 'SettingOutlined'
        }
      },
      {
        path: '/services',
        name: 'Services',
        component: () => import('@/views/Services.vue'),
        meta: {
          title: '服务管理',
          icon: 'AppstoreOutlined'
        }
      },
      {
        path: '/strategies',
        name: 'Strategies',
        component: () => import('@/views/Strategies.vue'),
        meta: {
          title: '策略管理',
          icon: 'RocketOutlined'
        }
      },
      {
        path: '/market',
        name: 'Market',
        component: () => import('@/views/Market.vue'),
        meta: {
          title: '行情数据',
          icon: 'LineChartOutlined'
        }
      },
      {
        path: '/account',
        name: 'Account',
        component: () => import('@/views/Account.vue'),
        meta: {
          title: '账户资金',
          icon: 'WalletOutlined'
        }
      },
      {
        path: '/positions',
        name: 'Positions',
        component: () => import('@/views/Positions.vue'),
        meta: {
          title: '持仓管理',
          icon: 'PieChartOutlined'
        }
      },
      {
        path: '/risk',
        name: 'Risk',
        component: () => import('@/views/Risk.vue'),
        meta: {
          title: '风险控制',
          icon: 'SafetyOutlined'
        }
      },
      {
        path: '/logs',
        name: 'Logs',
        component: () => import('@/views/Logs.vue'),
        meta: {
          title: '系统日志',
          icon: 'FileTextOutlined'
        }
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: {
      title: '登录',
      hideInMenu: true
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: {
      title: '页面不存在',
      hideInMenu: true
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta?.title) {
    document.title = `${to.meta.title} - ARBIG量化交易系统`
  }
  
  // 这里可以添加认证逻辑
  // if (to.name !== 'Login' && !isAuthenticated()) {
  //   next({ name: 'Login' })
  // } else {
  //   next()
  // }
  
  next()
})

export default router
