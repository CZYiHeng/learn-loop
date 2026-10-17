// 平台检测 — 根据屏幕宽度切换布局
import { ref, onMounted, onUnmounted } from "vue";

const MOBILE_BREAKPOINT = 768;

export function usePlatform() {
  const isMobile = ref(false);

  const update = () => {
    isMobile.value = window.innerWidth < MOBILE_BREAKPOINT;
  };

  onMounted(() => {
    update();
    window.addEventListener("resize", update);
  });

  onUnmounted(() => {
    window.removeEventListener("resize", update);
  });

  return { isMobile };
}
