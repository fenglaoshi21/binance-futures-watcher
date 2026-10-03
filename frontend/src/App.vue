<template>
  <div id="app">
    <nav class="nav">
      <div class="nav-brand">📊 合约涨幅榜监控</div>
      <router-link to="/">实时看板</router-link>
      <router-link to="/history">历史观测</router-link>
      <span style="margin-left:auto" class="text-muted" v-if="lastUpdate">
        更新于 {{ lastUpdate }}
      </span>
    </nav>
    <main class="container">
      <router-view />
    </main>
    <footer style="text-align:center;padding:20px;color:var(--text-secondary);font-size:12px">
      ⚠️ 本系统仅为行情数据统计与复盘分析工具，不构成任何投资建议。加密合约高杠杆风险极高。
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const lastUpdate = ref('')

onMounted(() => {
  lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
})
</script>
