let getAccessToken: (() => string | null) | null = null
let getRefreshToken: (() => string | null) | null = null
let onRefresh: (() => Promise<boolean>) | null = null
let onLogout: (() => void) | null = null

export function initApiClient(
  accessTokenFn: () => string | null,
  refreshTokenFn: () => string | null,
  refreshFn: () => Promise<boolean>,
  logoutFn: () => void,
) {
  getAccessToken = accessTokenFn
  getRefreshToken = refreshTokenFn
  onRefresh = refreshFn
  onLogout = logoutFn
}

export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }
  const token = getAccessToken?.()
  if (token) headers['Authorization'] = `Bearer ${token}`

  let resp = await fetch(url, { ...options, headers })

  if (resp.status === 401 && onRefresh) {
    const refreshed = await onRefresh()
    if (refreshed) {
      const newToken = getAccessToken?.()
      if (newToken) headers['Authorization'] = `Bearer ${newToken}`
      resp = await fetch(url, { ...options, headers })
    } else {
      onLogout?.()
    }
  }

  return resp
}