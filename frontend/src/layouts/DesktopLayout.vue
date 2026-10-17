<script setup lang="ts">
// DesktopLayout — 顶部导航 + 侧边栏
import { useRouter } from "vue-router";
import { useRoute } from "vue-router";
import { computed } from "vue";

const router = useRouter();
const route = useRoute();

const navs = [
  { name: "today", label: "今日看板", path: "/today" },
  { name: "plans", label: "计划", path: "/plans" },
  { name: "calendar", label: "日历", path: "/calendar" },
  { name: "review", label: "复习", path: "/review" },
  { name: "stats", label: "统计", path: "/stats" },
  { name: "resources", label: "资料库", path: "/resources" },
  { name: "settings", label: "设置", path: "/settings" },
];

const activeTab = computed(() => (route.meta.tab as string) ?? "");
</script>

<template>
  <div class="desktop-layout">
    <header class="header">
      <div class="brand">✨ StudyHub</div>
      <nav class="topnav">
        <button
          v-for="nav in navs"
          :key="nav.name"
          :class="{ active: activeTab === nav.name || route.path === nav.path }"
          @click="router.push(nav.path)"
          type="button"
        >
          {{ nav.label }}
        </button>
      </nav>
    </header>
    <main class="content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.desktop-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #fafafa;
}
.header {
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #eee;
}
.brand {
  font-weight: 600;
  font-size: 18px;
  color: #534AB7;
}
.topnav {
  display: flex;
  gap: 8px;
}
.topnav button {
  background: none;
  border: none;
  padding: 8px 14px;
  cursor: pointer;
  color: #555;
  border-radius: 6px;
  font-size: 14px;
  transition: background 0.15s;
}
.topnav button:hover {
  background: #f0f0f5;
}
.topnav button.active {
  background: #534AB7;
  color: #fff;
}
.content {
  flex: 1;
  padding: 24px;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  overflow-y: auto;
}
</style>
