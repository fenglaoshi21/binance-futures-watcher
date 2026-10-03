<template>
  <div>
    <div style="margin-bottom:16px">
      <router-link to="/history" class="btn">← 返回列表</router-link>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="record">
      <!-- 标题 -->
      <div class="card" style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <span class="card-title">观测详情 #{{ record.id }}</span>
          <div style="font-size:28px;font-weight:700">
            {{ record.symbol }}
            <span class="badge" :class="record.change_24h >= 0 ? 'badge-green' : 'badge-red'" style="margin-left:12px;font-size:16px">
              {{ record.change_24h >= 0 ? '+' : '' }}{{ record.change_24h }}%
            </span>
          </div>
        </div>
        <div style="text-align:right">
          <div class="text-muted" style="font-size:12px">观测时间</div>
          <div style="font-size:16px">{{ formatTime(record.observe_time) }}</div>
          <div class="text-muted" style="font-size:12px;margin-top:4px">
            状态: {{ statusLabel(record.task_status) }}
          </div>
        </div>
      </div>

      <!-- 核心指标 -->
      <div class="grid-4">
        <div class="card">
          <div class="metric-label">24h 涨跌幅</div>
          <div class="metric-value" :class="record.change_24h >= 0 ? 'text-green' : 'text-red'">
            {{ record.change_24h >= 0 ? '+' : '' }}{{ record.change_24h }}%
          </div>
        </div>
        <div class="card">
          <div class="metric-label">持仓量 OI</div>
          <div class="metric-value">{{ formatNumber(record.open_interest) }}</div>
        </div>
        <div class="card">
          <div class="metric-label">资金费率</div>
          <div class="metric-value" :class="record.funding_rate >= 0 ? 'text-green' : 'text-red'">
            {{ record.funding_rate }}%
          </div>
        </div>
        <div class="card">
          <div class="metric-label">24h 成交量</div>
          <div class="metric-value">{{ formatNumber(record.volume_24h) }}</div>
        </div>
      </div>

      <!-- 爆仓明细 -->
      <div class="grid-3">
        <div class="card">
          <div class="metric-label">多头爆仓 (24h)</div>
          <div class="metric-value text-red">{{ formatNumber(record.long_liq_24h) }}</div>
        </div>
        <div class="card">
          <div class="metric-label">空头爆仓 (24h)</div>
          <div class="metric-value text-green">{{ formatNumber(record.short_liq_24h) }}</div>
        </div>
        <div class="card">
          <div class="metric-label">总爆仓 (24h)</div>
          <div class="metric-value text-yellow">
            {{ formatNumber((record.long_liq_24h || 0) + (record.short_liq_24h || 0)) }}
          </div>
        </div>
      </div>

      <!-- AI 报告 -->
      <div class="card" v-if="record.llm_report">
        <div class="card-title">🤖 AI 分析报告</div>
        <pre class="report">{{ record.llm_report }}</pre>
      </div>

      <!-- 原始数据 -->
      <div class="card" v-if="record.raw_data">
        <div class="card-title">原始数据 (JSON)</div>
        <pre class="report" style="max-height:400px;overflow:auto">{{ JSON.stringify(record.raw_data, null, 2) }}</pre>
      </div>

      <!-- 错误信息 -->
      <div class="card" v-if="record.error_msg">
        <div class="card-title">错误信息</div>
        <pre class="report" style="color:var(--accent-red)">{{ record.error_msg }}</pre>
      </div>
    </div>

    <div v-else class="card">
      <div class="loading">未找到该记录</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getObservation, formatNumber, formatTime } from '../api/supabase'

const route = useRoute()
const record = ref(null)
const loading = ref(true)

function statusLabel(status) {
  const map = { pending: '待处理', processing: '处理中', completed: '已完成', fail: '失败' }
  return map[status] || status
}

async function loadData() {
  loading.value = true
  try {
    record.value = await getObservation(route.params.id)
  } catch (e) {
    console.error('加载失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
