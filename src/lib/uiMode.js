import { readable } from 'svelte/store';

function resolveLocalFixedUi() {
  if (typeof window === 'undefined') return false;

  const host = window.location.hostname;
  return host === 'localhost' || host === '127.0.0.1' || host === '::1';
}

export const localFixedUi = readable(resolveLocalFixedUi());
