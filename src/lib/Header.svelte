<script>
  import { onMount } from 'svelte';
  import { connectionState, clock } from '$lib/ros.js';
  import ExitButton from '$lib/common/ExitButton.svelte';

  let vpW = 0;
  let vpH = 0;
  let dpr = 1;

  function fmt(d) {
    return d.toLocaleTimeString('en-GB', { hour12: false, hour: '2-digit', minute: '2-digit' });
  }

  onMount(() => {
    const update = () => {
      vpW = window.innerWidth;
      vpH = window.innerHeight;
      dpr = window.devicePixelRatio || 1;
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  });

  $: statusClass =
    $connectionState === 'connected' ? 'ok' : $connectionState === 'connecting' ? 'warn' : 'err';
</script>

<header class="header">
  <div class="brand">
    <img class="brand-logo" src="/logo.png" alt="INHA United" />
    <span>INHA UNITED</span>
  </div>

  <div class="right">
    <span class="dot {statusClass}"></span>
    <span class="vp mono">{vpW}×{vpH} @ {dpr}x</span>
    <span class="time mono">{fmt($clock)}</span>
    <ExitButton />
  </div>
</header>

<style>
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 28px;
    min-height: 54px;
    border-bottom: 1px solid var(--border-1);
    background: var(--bg-0);
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--text-1);
  }

  .brand-logo {
    height: 32px;
    width: auto;
    object-fit: contain;
  }

  .right {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .time {
    color: var(--text-1);
    font-size: 14px;
  }

  .vp {
    color: var(--text-3);
    font-size: 12px;
    padding: 2px 8px;
    border: 1px solid var(--border-1);
    border-radius: 999px;
  }

  @media (max-width: 760px) {
    .header {
      padding: 10px 14px;
      gap: 10px;
      flex-wrap: wrap;
    }

    .brand {
      gap: 8px;
      font-size: 12px;
    }

    .brand-logo {
      height: 26px;
    }

    .right {
      width: 100%;
      justify-content: flex-end;
      gap: 10px;
    }

    .time {
      font-size: 12px;
    }
  }
</style>
