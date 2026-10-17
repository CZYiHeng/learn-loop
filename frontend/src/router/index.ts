// 路由配置 — 10 个 view 占位
// meta.platform: 'mobile' | 'desktop' | 'auto'(默认)
// meta.title: 页面标题
import { createRouter, createWebHistory } from "vue-router";

const routes = [
  {
    path: "/",
    name: "home",
    component: () => import("@/views/HomeView.vue"),
    meta: { title: "首页" },
  },
  {
    path: "/today",
    name: "today",
    component: () => import("@/views/TodayView.vue"),
    meta: { title: "今日看板", tab: "today" },
  },
  {
    path: "/plans",
    name: "plans",
    component: () => import("@/views/PlansView.vue"),
    meta: { title: "计划列表", tab: "plans" },
  },
  {
    path: "/plans/:id",
    name: "plan-detail",
    component: () => import("@/views/PlanDetailView.vue"),
    meta: { title: "计划详情" },
  },
  {
    path: "/plans/new",
    name: "plan-create",
    component: () => import("@/views/PlanCreateView.vue"),
    meta: { title: "新建计划" },
  },
  {
    path: "/calendar",
    name: "calendar",
    component: () => import("@/views/CalendarView.vue"),
    meta: { title: "日历", tab: "calendar" },
  },
  {
    path: "/stats",
    name: "stats",
    component: () => import("@/views/StatsView.vue"),
    meta: { title: "统计", tab: "stats" },
  },
  {
    path: "/review",
    name: "review",
    component: () => import("@/views/ReviewView.vue"),
    meta: { title: "复习", tab: "review" },
  },
  {
    path: "/resources",
    name: "resources",
    component: () => import("@/views/ResourcesView.vue"),
    meta: { title: "资料库" },
  },
  {
    path: "/settings",
    name: "settings",
    component: () => import("@/views/SettingsView.vue"),
    meta: { title: "设置" },
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach((to, _from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} · StudyHub`;
  }
  next();
});
