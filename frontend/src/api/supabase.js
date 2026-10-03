/**
 * Supabase 前端 API 封装
 * 使用 anon key（只读权限），不暴露 service_role key
 */
import { createClient } from '@supabase/supabase-js'

// 从环境变量或硬编码（前端用 anon key 是安全的）
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || ''
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

export const supabase = SUPABASE_URL
  ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
  : null

/**
 * 获取最新一条已完成的观测记录
 */
export async function getLatestObservation() {
  if (!supabase) return null
  const { data, error } = await supabase
    .from('market_observation')
    .select('*')
    .eq('task_status', 'completed')
    .order('observe_time', { ascending: false })
    .limit(1)
  if (error) throw error
  return data[0] || null
}

/**
 * 获取观测记录列表（分页）
 */
export async function listObservations(limit = 50, offset = 0) {
  if (!supabase) return []
  const { data, error } = await supabase
    .from('market_observation')
    .select('id, observe_time, symbol, change_24h, volume_24h, open_interest, funding_rate, long_liq_24h, short_liq_24h, task_status')
    .order('observe_time', { ascending: false })
    .range(offset, offset + limit - 1)
  if (error) throw error
  return data
}

/**
 * 获取单条观测记录详情
 */
export async function getObservation(id) {
  if (!supabase) return null
  const { data, error } = await supabase
    .from('market_observation')
    .select('*')
    .eq('id', id)
    .single()
  if (error) throw error
  return data
}

/**
 * 格式化数字
 */
export function formatNumber(num, decimals = 2) {
  if (num === null || num === undefined) return 'N/A'
  const n = Number(num)
  if (isNaN(n)) return 'N/A'
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(decimals) + '亿'
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(decimals) + '万'
  return n.toFixed(decimals)
}

/**
 * 格式化时间
 */
export function formatTime(isoString) {
  if (!isoString) return 'N/A'
  const d = new Date(isoString)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
