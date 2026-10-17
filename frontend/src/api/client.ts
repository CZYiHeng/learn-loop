// API 客户端 — token 注入、401 跳转、超时、统一错误体
// 计划第五节约定错误体: { error: { code, message, details, request_id } }

const API_BASE = "/api/v1";
const TOKEN_HEADER = "X-Auth-Token";
const DEFAULT_TIMEOUT = 30000;

// 取 token — 从 localStorage 或环境注入
function getToken(): string {
  return localStorage.getItem("studyhub_token") || "";
}

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public details: Record<string, unknown> = {},
    public requestId: string = "unknown",
    public status: number = 500
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends RequestInit {
  timeout?: number;
  // SSE 流式接口不能用 fetch 包装，需要返回原始 Response
  raw?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeout = DEFAULT_TIMEOUT, raw = false, headers = {}, ...rest } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        [TOKEN_HEADER]: getToken(),
        ...(headers as Record<string, string>),
      },
      signal: controller.signal,
    });

    if (raw) {
      return res as unknown as T;
    }

    if (!res.ok) {
      let body: { error?: { code?: string; message?: string; details?: object; request_id?: string } } = {};
      try { body = await res.json(); } catch { /* ignore */ }
      const err = body.error || {};
      throw new ApiError(
        err.code || "http_error",
        err.message || `HTTP ${res.status}`,
        (err.details as Record<string, unknown>) || {},
        err.request_id || "unknown",
        res.status
      );
    }

    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body: JSON.stringify(body || {}) }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body: JSON.stringify(body || {}) }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE" }),
  // SSE 流式：返回 Response，调用方自己解析
  stream: (path: string, body?: unknown, options?: RequestOptions) =>
    request<Response>(path, {
      ...options,
      method: "POST",
      body: JSON.stringify(body || {}),
      raw: true,
      // SSE 不要超时（流可能持续很久）
      timeout: 600000,
    }),
};

// 全局未授权处理：跳登录（一期没登录页，先 alert）
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

// 包一层自动处理 401
export async function apiCall<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      onUnauthorized?.();
    }
    throw e;
  }
}
