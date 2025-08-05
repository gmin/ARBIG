/**
 * API客户端
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { message } from 'ant-design-vue'
import type { APIResponse, ErrorResponse } from '@/types/api'

class APIClient {
  private instance: AxiosInstance | null = null

  constructor() {
    this.initializeInstance()
  }

  private initializeInstance() {
    try {
      // 检查axios是否可用
      if (typeof axios === 'undefined') {
        console.error('Axios is not available')
        return
      }

      this.instance = axios.create({
        baseURL: '/api/v1',
        timeout: 10000,
        headers: {
          'Content-Type': 'application/json',
        },
      })

      this.setupInterceptors()
    } catch (error) {
      console.error('Failed to create axios instance:', error)
      // 尝试创建一个简单的实例
      try {
        this.instance = axios.create({
          baseURL: '/api/v1',
          timeout: 10000,
        })
      } catch (fallbackError) {
        console.error('Failed to create fallback axios instance:', fallbackError)
        this.instance = null
      }
    }
  }

  private setupInterceptors() {
    if (!this.instance) {
      console.error('Cannot setup interceptors: instance is null')
      return
    }

    // 请求拦截器
    this.instance.interceptors.request.use(
      (config) => {
        // 可以在这里添加认证token
        // config.headers.Authorization = `Bearer ${token}`
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response: AxiosResponse<APIResponse>) => {
        const { data } = response
        
        // 检查业务状态
        if (!data.success) {
          const errorData = data as unknown as ErrorResponse
          message.error(errorData.error?.message || '请求失败')
          return Promise.reject(new Error(errorData.error?.message || '请求失败'))
        }
        
        // 如果成功，返回整个response
        return response
      },
      (error) => {
        // 处理HTTP错误
        if (error.response) {
          const status = error.response.status
          switch (status) {
            case 401:
              message.error('未授权，请重新登录')
              break
            case 403:
              message.error('权限不足')
              break
            case 404:
              message.error('请求的资源不存在')
              break
            case 500:
              message.error('服务器内部错误')
              break
            default:
              message.error(`请求失败: ${error.response.data?.message || error.message}`)
          }
        } else if (error.request) {
          message.error('网络连接失败，请检查网络')
        } else {
          message.error(`请求配置错误: ${error.message}`)
        }
        
        return Promise.reject(error)
      }
    )
  }

  // GET请求
  async get<T = any>(url: string, params?: any): Promise<APIResponse<T>> {
    if (!this.instance) {
      throw new Error('API客户端未正确初始化')
    }
    const response = await this.instance.get<APIResponse<T>>(url, { params })
    return response.data
  }

  // POST请求
  async post<T = any>(url: string, data?: any): Promise<APIResponse<T>> {
    if (!this.instance) {
      throw new Error('API客户端未正确初始化')
    }
    const response = await this.instance.post<APIResponse<T>>(url, data)
    return response.data
  }

  // PUT请求
  async put<T = any>(url: string, data?: any): Promise<APIResponse<T>> {
    if (!this.instance) {
      throw new Error('API客户端未正确初始化')
    }
    const response = await this.instance.put<APIResponse<T>>(url, data)
    return response.data
  }

  // DELETE请求
  async delete<T = any>(url: string): Promise<APIResponse<T>> {
    if (!this.instance) {
      throw new Error('API客户端未正确初始化')
    }
    const response = await this.instance.delete<APIResponse<T>>(url)
    return response.data
  }
}

// 创建API客户端实例
let apiClient: APIClient

// 创建fallback函数
const createFallbackMethods = () => ({
  async get(url: string, params?: any) {
    const queryString = params ? '?' + new URLSearchParams(params).toString() : ''
    const response = await fetch(`/api/v1${url}${queryString}`)
    return await response.json()
  },
  async post(url: string, data?: any) {
    const response = await fetch(`/api/v1${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return await response.json()
  },
  async put(url: string, data?: any) {
    const response = await fetch(`/api/v1${url}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return await response.json()
  },
  async delete(url: string) {
    const response = await fetch(`/api/v1${url}`, { method: 'DELETE' })
    return await response.json()
  }
})

try {
  apiClient = new APIClient()
} catch (error) {
  console.error('Failed to create API client, using fallback:', error)
  // 创建一个fallback客户端
  const fallbackMethods = createFallbackMethods()
  apiClient = fallbackMethods as APIClient
}

export { apiClient }

// 导出便捷方法 - 使用更安全的方式
const fallbackMethods = createFallbackMethods()

// 安全的方法导出，确保总是有可用的方法
export const get = apiClient?.get?.bind(apiClient) || fallbackMethods.get
export const post = apiClient?.post?.bind(apiClient) || fallbackMethods.post
export const put = apiClient?.put?.bind(apiClient) || fallbackMethods.put
export const del = apiClient?.delete?.bind(apiClient) || fallbackMethods.delete
