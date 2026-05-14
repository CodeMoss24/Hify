import { get } from '@/api'

export const getHealth = () => {
  return get('/v1/health')
}
