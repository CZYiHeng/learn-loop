<script setup lang="ts">
// 根容器：路由出口，根据 platform 切 layout
import { computed } from "vue";
import { useRoute } from "vue-router";
import { usePlatform } from "@/composables/usePlatform";
import MobileLayout from "@/layouts/MobileLayout.vue";
import DesktopLayout from "@/layouts/DesktopLayout.vue";

const route = useRoute();
const { isMobile } = usePlatform();

// 路由 meta.platform: 'mobile' | 'desktop' | 'auto'
// 默认 auto：按设备宽度切换
const layout = computed(() => {
  const platform = (route.meta.platform as string) ?? "auto";
  if (platform === "mobile") return MobileLayout;
  if (platform === "desktop") return DesktopLayout;
  return isMobile.value ? MobileLayout : DesktopLayout;
});
</script>

<template>
  <component :is="layout">
    <router-view />
  </component>
</template>
