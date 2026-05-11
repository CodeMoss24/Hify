import api from '@/api'

export const getHealth = () => {
  return api.get('/v1/health')
}
