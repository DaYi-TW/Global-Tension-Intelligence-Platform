import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export const fetchDashboardOverview = (date = null) =>
  api.get('/dashboard/overview', { params: date ? { date } : {} }).then(r => r.data)

export const fetchGlobalTrend = (range = '30d') =>
  api.get('/tension/global/trend', { params: { range } }).then(r => r.data)

export const fetchRegions = (date = null) =>
  api.get('/tension/regions', { params: date ? { date } : {} }).then(r => r.data)

export const fetchCountries = (date = null, region = null, limit = 50) =>
  api.get('/tension/countries', {
    params: {
      ...(date ? { date } : {}),
      ...(region ? { region } : {}),
      limit,
    },
  }).then(r => r.data)

export const fetchMapHeat = (date = null, dimension = 'overall') =>
  api.get('/map/heat', {
    params: { dimension, ...(date ? { date } : {}) },
  }).then(r => r.data)

export const fetchMapHeatRange = (from, to, dimension = 'overall') =>
  api.get('/map/heat/range', {
    params: { from, to, dimension },
  }).then(r => r.data)

export const fetchEvents = (params = {}) =>
  api.get('/events', { params }).then(r => r.data)

export const fetchEventDetail = (eventId) =>
  api.get(`/events/${eventId}`).then(r => r.data)

export default api
