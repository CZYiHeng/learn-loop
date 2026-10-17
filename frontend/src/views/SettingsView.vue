<script setup lang="ts">
// 设置 — M0 占位，但能验证 /health 联通
import { ref, onMounted } from "vue";
import { api } from "@/api/client";

interface Health {
  status: string;
  app: string;
  env: string;
  version: string;
  db: { driver: string; table_count: number; ok: boolean };
}

const health = ref<Health | null>(null);
const error = ref<string>("");

onMounted(async () => {
  try {
    // 直接走 /health，不在 /api/v1 下，绕过 token
    const res = await fetch("/health");
    health.value = await res.json() as Health;
  } catch (e) {
    error.value = String(e);
  }
});
</script>

<template>
  <div class="view-placeholder">
    <h1>设置</h1>
    <div v-if="error" style="color: #c00;">后端连通失败：{{ error }}</div>
    <div v-else-if="health">
      <p>后端状态：{{ health.status }} · {{ health.app }} v{{ health.version }}</p>
      <p>环境：{{ health.env }}</p>
      <p>数据库：{{ health.db.driver }} · {{ health.db.table_count }} 张表 · {{ health.db.ok ? "✅" : "❌" }}</p>
    </div>
    <div v-else>正在连接后端…</div>
  </div>
</template>
