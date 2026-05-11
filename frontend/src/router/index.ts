import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/pages/HomePage.vue'

const routes = [
  { path: '/', name: 'home', component: HomePage },
  {
    path: '/analysis/:studyId',
    name: 'analysis',
    component: () => import('@/pages/AnalysisPage.vue'),
    props: true,
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
