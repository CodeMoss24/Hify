import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

api.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 200) {
      return res.data
    }
    ElMessage.error(res.message || '请求失败')
    return Promise.reject(res)
  },
  (error) => {
    ElMessage.error(error.message || '网络异常')
    return Promise.reject(error)
  }
)

export const get = <T = any>(url: string, params?: any, config?: any): Promise<T> => {
  return api.get(url, { params, ...config })
}

export const post = <T = any>(url: string, data?: any, config?: any): Promise<T> => {
  return api.post(url, data, config)
}

export const put = <T = any>(url: string, data?: any, config?: any): Promise<T> => {
  return api.put(url, data, config)
}

export const del = <T = any>(url: string, params?: any, config?: any): Promise<T> => {
  return api.delete(url, { params, ...config })
}

export default api
