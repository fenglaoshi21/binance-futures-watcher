import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import History from '../views/History.vue'
import Detail from '../views/Detail.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard, meta: { title: '实时看板' } },
  { path: '/history', name: 'History', component: History, meta: { title: '历史观测' } },
  { path: '/detail/:id', name: 'Detail', component: Detail, meta: { title: '观测详情' }, props: true },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = `${to.meta.title || '观测'} - 币安合约涨幅榜监控`
})

export default router
