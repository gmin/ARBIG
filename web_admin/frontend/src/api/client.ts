/**
 * API客户端
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { message } from 'ant-design-vue'
import type { APIResponse, ErrorResponse } from '@/types/api'

class APIClient {
  private instance: AxiosInstance

  constructor() {
    this.instance = axios.create({
      baseURL: '/api/v1',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
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
    const response = await this.instance.get<APIResponse<T>>(url, { params })
    return response.data
  }

  // POST请求
  async post<T = any>(url: string, data?: any): Promise<APIResponse<T>> {
    const response = await this.instance.post<APIResponse<T>>(url, data)
    return response.data
  }

  // PUT请求
  async put<T = any>(url: string, data?: any): Promise<APIResponse<T>> {
    const response = await this.instance.put<APIResponse<T>>(url, data)
    return response.data
  }

  // DELETE请求
  async delete<T = any>(url: string): Promise<APIResponse<T>> {
    const response = await this.instance.delete<APIResponse<T>>(url)
    return response.data
  }
}

// 创建API客户端实例
export const apiClient = new APIClient()

// 导出便捷方法
export const { get, post, put, delete: del } = apiClient
