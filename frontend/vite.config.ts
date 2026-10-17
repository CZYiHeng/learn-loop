import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    // 代理后端：/api/* → http://127.0.0.1:8000
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        // SSE 必须关掉 buffer，否则问答流式会一次性全出
        // （M6 Nginx 也要配 proxy_buffering off）
        configure: (proxy) => {
          proxy.on("proxyReq", (proxyReq) => {
            proxyReq.setHeader("Accept", "text/event-stream");
          });
        },
      },
      // /health 同样代理
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    target: "es2022",
    sourcemap: true,
  },
});
