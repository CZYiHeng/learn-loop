<script setup lang="ts">
// 首页 — 无 plan 时显示输入框 + 场景下拉（M3 入口流程）
// M0 占位：先显示"启动中"状态，等 M1 后才有逻辑
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const loading = ref(true);

onMounted(async () => {
  // M1 后：检查是否有 plan
  //   无 plan → 显示输入框
  //   有 plan → router.push("/today")
  // M0：暂时直接跳 /today 占位
  setTimeout(() => {
    loading.value = false;
    router.push("/today");
  }, 300);
});
</script>

<template>
  <div class="home">
    <p v-if="loading">启动中…</p>
    <p v-else>跳转中…</p>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  color: #888;
}
</style>
