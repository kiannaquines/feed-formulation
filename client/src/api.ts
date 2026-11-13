const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export type ApiResult = {
  status: number;
  ok: boolean;
  data: unknown;
};

export async function apiRequest(
  method: string,
  path: string,
  token?: string,
  body?: unknown,
): Promise<ApiResult> {
  const response = await fetch(`${apiBase}${path}`, {
    method,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  const content = await response.text();
  if (response.status === 401 && token) window.dispatchEvent(new Event('feedprime-session-expired'));
  let data: unknown = content;
  if (content) {
    try {
      data = JSON.parse(content);
    } catch {
      // Keep non-JSON error bodies visible in the response panel.
    }
  }
  return { status: response.status, ok: response.ok, data };
}

export function resultMessage(result: ApiResult): string {
  if (result.data && typeof result.data === 'object' && 'detail' in result.data) {
    const detail = result.data.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const messages = detail.map((item) => item && typeof item === 'object' && 'msg' in item ? String(item.msg) : '').filter(Boolean);
      if (messages.length) return messages.join('; ');
    }
  }
  return `Request failed with HTTP ${result.status}`;
}
