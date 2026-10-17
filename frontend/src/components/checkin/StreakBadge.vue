<script setup lang="ts">
// StreakBadge — 连续天数徽章
// ★ 决策 6：今天没活动不归零（service 层 + 单测覆盖）
import { computed } from "vue";
import type { Streak } from "@/api/types";

const props = defineProps<{
  streak: Streak | null;
}>();

const streakDays = computed(() => props.streak?.streak ?? 0);
const todayActive = computed(() => props.streak?.today_active ?? false);
</script>

<template>
  <div class="streak-badge" :class="{ idle: !todayActive && streakDays > 0 }">
    <div class="streak-number">{{ streakDays }}</div>
    <div class="streak-label">
      <template v-if="streakDays === 0">还没开始</template>
      <template v-else>{{ todayActive ? '连续' : '已断' }} {{ streakDays }} 天</template>
    </div>
  </div>
</template>

<style scoped>
.streak-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #534AB7, #7F77DD);
  color: #fff;
  border-radius: var(--radius-md);
  min-width: 90px;
}
.streak-badge.idle {
  background: linear-gradient(135deg, #888, #aaa);
}
.streak-number {
  font-size: 28px;
  font-weight: 600;
  line-height: 1;
}
.streak-label {
  font-size: 11px;
  margin-top: 4px;
  opacity: 0.85;
}
</style>
