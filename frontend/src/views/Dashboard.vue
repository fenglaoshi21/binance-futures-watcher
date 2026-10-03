<template>
  <div>
    <!-- 顶部状态条 -->
    <div class="card" style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <span class="card-title">当前观测状态</span>
        <div style="font-size:20px;font-weight:700">
          <span v-if="latest" class="text-green">{{ latest.symbol }}</span>
          <span v-else class="text-muted">加载中...</span>
          <span v-if="latest" class="badge badge-green" style="margin-left:12px">
            +{{ latest.change_24h }}%
          </span>
        </div>
      </div>
      <div style="text-align:right">
        <div class="text-muted" style="font-size:12px">观测时间</div>
        <div style="font-size:16px">{{ formatTime(latest?.observe_time) }}</div>
      </div>
    </div>

    <!-- 核心指标 -->
    <div class="grid-4" v-if="latest">
      <div class="card">
        <div class="metric-label">24h 涨跌幅</div>
        <div class="metric-value" :class="latest.change_24h >= 0 ? 'text-green' : 'text-red'">
          {{ latest.change_24h >= 0 ? '+' : '' }}{{ latest.change_24h }}%
        </div>
      </div>
      <div class="card">
        <div class="metric-label">持仓量 OI</div>
        <div class="metric-value">{{ formatNumber(latest.open_interest) }}</div>
      </div>
      <div class="card">
        <div class="metric-label">资金费率</div>
        <div class="metric-value" :class="latest.funding_rate >= 0 ? 'text-green' : 'text-red'">
          {{ latest.funding_rate }}%
        </div>
      </div>
      <div class="card">
        <div class="metric-label">24h 总爆仓</div>
        <div class="metric-value text-yellow">
          {{ formatNumber((latest.long_liq_24h || 0) + (latest.short_liq_24h || 0)) }}
        </div>
      </div>
    </div>

    <!-- 爆仓结构 -->
    <div class="grid-2" v-if="latest">
      <div class="card">
        <div class="card-title">爆仓结构 (24h)</div>
        <div style="display:flex;gap:20px">
          <div style="flex:1">
            <div class="text-muted" style="font-size:12px">多头爆仓</div>
            <div class="text-red" style="font-size:20px;font-weight:700">
              {{ formatNumber(latest.long_liq_24h) }}
            </div>
          </div>
          <div style="flex:1">
            <div class="text-muted" style="font-size:12px">空头爆仓</div>
            <div class="text-green" style="font-size:20px;font-weight:700">
              {{ formatNumber(latest.short_liq_24h) }}
            </div>
          </div>
        </div>
        <!-- 爆仓比例条 -->
        <div style="margin-top:12px;height:8px;background:var(--bg-primary);border-radius:4px;overflow:hidden;display:flex">
          <div :style="{width: longPct + '%', background: 'var(--accent-red)'}"></div>
          <div :style="{width: shortPct + '%', background: 'var(--accent-green)'}"></div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">成交量 (24h)</div>
        <div class="metric-value">{{ formatNumber(latest.volume_24h) }}</div>
        <div class="text-muted" style="font-size:12px;margin-top:4px">
          USDT 计价
        </div>
      </div>
    </div>

    <!-- LLM 分析报告 -->
    <div class="card" v-if="latest?.llm_report">
      <div class="card-title">🤖 AI 分析报告</div>
      <pre class="report">{{ latest.llm_report }}</pre>
    </div>

    <!-- 原始数据 -->
    <div class="card" v-if="latest?.raw_data">
      <div class="card-title">原始数据 (JSON)</div>
      <pre class="report" style="max-height:300px;overflow:auto">{{ JSON.stringify(latest.raw_data, null, 2) }}</pre>
    </div>

    <!-- 无数据提示 -->
    <div class="card" v-if="!latest && !loading">
      <div class="loading">
        暂无观测数据。请确保后端 Pipeline 已运行并写入 Supabase。
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getLatestObservation, formatNumber, formatTime } from '../api/supabase'

const latest = ref(null)
const loading = ref(true)

const longPct = computed(() => {
  if (!latest.value) return 50
  const long = Number(latest.value.long_liq_24h) || 0
  const short = Number(latest.value.short_liq_24h) || 0
  const total = long + short
  return total > 0 ? (long / total) * 100 : 50
})

const shortPct = computed(() => 100 - longPct.value)

async function loadData() {
  loading.value = true
  try {
    latest.value = await getLatestObservation()
  } catch (e) {
    console.error('加载失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
  // 每5分钟自动刷新
  setInterval(loadData, 5 * 60 * 1000)
})
</script>
