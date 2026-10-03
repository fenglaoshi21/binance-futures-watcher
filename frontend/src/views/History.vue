<template>
  <div>
    <div class="card" style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <span class="card-title">历史观测记录</span>
        <div style="font-size:20px;font-weight:700">共 {{ records.length }} 条</div>
      </div>
      <button class="btn" @click="loadData">刷新</button>
    </div>

    <div class="card" style="padding:0;overflow-x:auto">
      <table v-if="records.length > 0">
        <thead>
          <tr>
            <th>ID</th>
            <th>观测时间</th>
            <th>标的</th>
            <th>24h涨幅</th>
            <th>OI</th>
            <th>资金费率</th>
            <th>24h爆仓</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.id">
            <td class="text-muted">#{{ r.id }}</td>
            <td>{{ formatTime(r.observe_time) }}</td>
            <td style="font-weight:700">{{ r.symbol || '—' }}</td>
            <td :class="r.change_24h >= 0 ? 'text-green' : 'text-red'">
              {{ r.change_24h >= 0 ? '+' : '' }}{{ r.change_24h }}%
            </td>
            <td>{{ formatNumber(r.open_interest) }}</td>
            <td :class="r.funding_rate >= 0 ? 'text-green' : 'text-red'">
              {{ r.funding_rate }}%
            </td>
            <td class="text-yellow">{{ formatNumber((r.long_liq_24h || 0) + (r.short_liq_24h || 0)) }}</td>
            <td>
              <span :class="'badge badge-' + statusClass(r.task_status)">
                {{ statusLabel(r.task_status) }}
              </span>
            </td>
            <td>
              <router-link :to="'/detail/' + r.id" class="btn" style="padding:4px 10px;font-size:12px">
                详情
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="loading">暂无历史记录</div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listObservations, formatNumber, formatTime } from '../api/supabase'

const records = ref([])
const loading = ref(true)

function statusLabel(status) {
  const map = { pending: '待处理', processing: '处理中', completed: '已完成', fail: '失败' }
  return map[status] || status
}

function statusClass(status) {
  const map = { pending: 'blue', processing: 'blue', completed: 'green', fail: 'red' }
  return map[status] || 'blue'
}

async function loadData() {
  loading.value = true
  try {
    records.value = await listObservations(100)
  } catch (e) {
    console.error('加载失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
