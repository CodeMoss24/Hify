export interface ApiResponse<T = any> {
  code: number
  message: string
  data?: T
}

export interface PageResult<T = any> extends ApiResponse<T> {
  list: T[]
  total: number
  page: number
  page_size: number
}

export interface PageParams {
  page?: number
  page_size?: number
}
