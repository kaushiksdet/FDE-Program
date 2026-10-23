// Hash-based routing: #/add, #/search, #/high-risk, #/status, #/status/<encounterId>.

export type Screen = 'add' | 'search' | 'high-risk' | 'status'

export interface Route {
  screen: Screen
  encounterId?: number
}

const SCREENS: Screen[] = ['add', 'search', 'high-risk', 'status']

export function parseRoute(hash: string): Route {
  const [screen, id] = hash.replace(/^#\/?/, '').split('/')
  if (!SCREENS.includes(screen as Screen)) return { screen: 'search' }
  const encounterId = Number(id)
  return {
    screen: screen as Screen,
    encounterId: id && Number.isInteger(encounterId) && encounterId > 0 ? encounterId : undefined,
  }
}

export function screenHref(screen: Screen): string {
  return `#/${screen}`
}

export function statusHref(encounterId: number): string {
  return `#/status/${encounterId}`
}
