import { writable } from 'svelte/store';

// 'landing' | 'launcher' | 'mission'
const validRoutes = new Set(['landing', 'launcher', 'mission']);

function resolveInitialRoute() {
  if (typeof window === 'undefined') return 'landing';

  const name = new URLSearchParams(window.location.search).get('screen');
  return validRoutes.has(name) ? name : 'landing';
}

export const route = writable(resolveInitialRoute());

export function goto(name) {
  if (validRoutes.has(name)) {
    route.set(name);
  }
}
