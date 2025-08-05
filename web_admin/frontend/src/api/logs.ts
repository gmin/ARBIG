import { apiClient } from './client'

export interface LogEntry {
  timestamp: string
  level: string
  module: string
  message: string
  line_number: number
}

export interface LogsResponse {
  logs: LogEntry[]
  total_lines: number
  file_path: string
  file_size: number
  last_modified: string
}

export interface LogFilesResponse {
  log_files: Record<string, string[]>
}

export const logsAPI = {
  // 获取日志文件列表
  getLogFiles: async (): Promise<LogFilesResponse> => {
    const response = await apiClient.get('/logs/files')
    return response.data
  },

  // 获取日志内容
  getLogContent: async (params: {
    service?: string
    filename?: string
    lines?: number
    level?: string
    search?: string
    start_time?: string
    end_time?: string
  }): Promise<LogsResponse> => {
    const queryParams = new URLSearchParams()

    if (params.service) queryParams.append('service', params.service)
    if (params.filename) queryParams.append('filename', params.filename)
    if (params.lines) queryParams.append('lines', params.lines.toString())
    if (params.level) queryParams.append('level', params.level)
    if (params.search) queryParams.append('search', params.search)
    if (params.start_time) queryParams.append('start_time', params.start_time)
    if (params.end_time) queryParams.append('end_time', params.end_time)

    const response = await apiClient.get(`/logs/content?${queryParams.toString()}`)
    return response.data
  },

  // 下载日志文件
  downloadLogFile: (service: string, filename: string): string => {
    return `/api/v1/logs/download/${service}/${filename}`
  }
}
