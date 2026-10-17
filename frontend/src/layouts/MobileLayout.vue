<script setup lang="ts">
// MobileLayout — 底部 5 tab（决策第 10 节）
// 移动端：底部 5 tab；FAB 右下角；触摸目标 44px+
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const tabs = [
  { name: "today", label: "今日", path: "/today", icon: "✓" },
  { name: "plans", label: "计划", path: "/plans", icon: "📋" },
  { name: "calendar", label: "日历", path: "/calendar", icon: "📅" },
  { name: "review", label: "复习", path: "/review", icon: "🔄" },
  { name: "stats", label: "统计", path: "/stats", icon: "📊" },
];

const activeTab = computed(() => (route.meta.tab as string) ?? "");
</script>

<template>
  <div class="mobile-layout">
    <main class="mobile-content">
      <slot />
    </main>
    <nav class="mobile-tabbar">
      <button
        v-for="tab in tabs"
        :key="tab.name"
        class="tab"
        :class="{ active: activeTab === tab.name }"
        @click="router.push(tab.path)"
        type="button"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.mobile-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-bg, #f5f5f5);
}
.mobile-content {
  flex: 1;
  padding-bottom: env(safe-area-inset-bottom, 0);
  overflow-y: auto;
}
.mobile-tabbar {
  position: sticky;
  bottom: 0;
  display: flex;
  background: #fff;
  border-top: 1px solid #eee;
  padding-bottom: env(safe-area-inset-bottom, 0);
  z-index: 100;
}
.tab {
  flex: 1;
  background: none;
  border: none;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-height: 56px;
  cursor: pointer;
  color: #888;
  transition: color 0.15s;
}
.tab.active {
  color: #534AB7;
}
.tab-icon {
  font-size: 20px;
}
.tab-label {
  font-size: 11px;
}
</style>
