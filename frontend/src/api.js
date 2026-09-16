const BASE = import.meta.env.VITE_API_URL || '/api';
let csrfToken = '';
export function setCsrfToken(value) {
  csrfToken = value || '';
}
export async function request(path, options = {}) {
  let response;
  try {
    const headers = new Headers(options.headers);
    if (csrfToken && ['POST', 'PATCH', 'PUT', 'DELETE'].includes(options.method))
      headers.set('X-CSRF-Token', csrfToken);
    response = await fetch(`${BASE}${path}`, { ...options, headers, credentials: 'same-origin' });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Unable to connect. Start the feedback server, then try again.');
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/'))
      window.dispatchEvent(new Event('session-expired'));
    const detail = body.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((e) => e.msg).join('; ')
          : [detail?.message, ...(detail?.errors || []).map((e) => `Row ${e.row}: ${e.message}`)]
              .filter(Boolean)
              .join('\n');
    const error = new Error(message || `Request failed (${response.status}).`);
    error.detail = detail;
    throw error;
  }
  return body;
}
export function apiUrl(path, params = {}) {
  return `${BASE}${path}?${new URLSearchParams(params)}`;
}
export function uploadCsv(file, mode, dateOrder = 'auto') {
  const body = new FormData();
  body.append('file', file);
  return request(`/ingest/csv?${new URLSearchParams({ mode, date_order: dateOrder })}`, {
    method: 'POST',
    body,
  });
}
