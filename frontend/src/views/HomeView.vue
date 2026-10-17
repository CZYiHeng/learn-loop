<script setup lang="ts">
// 首页 — 检查 plan：
//   无 → 直接显示 AI 生成入口（修订 electric-pulse 第二节）
//   有 → 跳 /today
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { plansApi } from "@/api/plans";
import PlanCreateView from "@/views/PlanCreateView.vue";

const router = useRouter();
const loading = ref(true);
const hasPlan = ref(false);
const error = ref("");

onMounted(async () => {
  try {
    const result = await plansApi.list();
    hasPlan.value = result.items.length > 0;
    if (hasPlan.value) {
      router.push("/today");
    }
  } catch (e: any) {
    // 后端不通也跳 /plans/new，让用户能看到入口
    error.value = e?.message || "";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="home">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>启动中…</p>
    </div>
    <!-- 有 plan → 自动跳转，这里不会渲染 -->
    <!-- 无 plan → 直接渲染 PlanCreateView 作为 AI 生成入口 -->
    <PlanCreateView v-else-if="!loading && !hasPlan" />
  </div>
</template>

<style scoped>
.home {
  min-height: 100vh;
}
.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 16px;
  min-height: 100vh;
  color: #888;
}
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #eee;
  border-top-color: #534AB7;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
