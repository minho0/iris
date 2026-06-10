<script>
  import { stopEveryNode } from '$lib/ros.js';

  export let variant = 'compact';

  let stopping = false;
  let failed = false;
  let resetTimer = null;

  async function handleStopEveryNode() {
    if (stopping) return;
    stopping = true;
    failed = false;

    if (resetTimer) {
      clearTimeout(resetTimer);
      resetTimer = null;
    }

    try {
      await stopEveryNode();
      window.dispatchEvent(new CustomEvent('iris:profiles-refresh'));
    } catch (error) {
      failed = true;
      console.error('Stop every node request failed', error);
    } finally {
      stopping = false;
      resetTimer = setTimeout(() => {
        failed = false;
        resetTimer = null;
      }, 2000);
    }
  }
</script>

<button
  class="stop-every {variant}"
  class:failed
  disabled={stopping}
  on:click={handleStopEveryNode}
>
  {stopping ? 'Stopping...' : failed ? 'Stop Failed' : 'Stop Every Node'}
</button>

<style>
  .stop-every {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--text-0);
    border: 1px solid rgba(248, 113, 113, 0.28);
    background: rgba(248, 113, 113, 0.1);
    transition: border-color 0.12s ease, background 0.12s ease;
    white-space: nowrap;
  }

  .stop-every:hover {
    border-color: rgba(248, 113, 113, 0.42);
    background: rgba(248, 113, 113, 0.16);
  }

  .stop-every.failed {
    border-color: rgba(248, 113, 113, 0.56);
    background: rgba(248, 113, 113, 0.2);
  }

  .stop-every:disabled {
    opacity: 0.72;
  }

  .stop-every.compact {
    min-width: 144px;
    height: 34px;
    padding: 0 14px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
  }

  .stop-every.panel {
    width: 100%;
    min-height: 62px;
    padding: 0 18px;
    border-radius: 16px;
    font-size: 22px;
    font-weight: 700;
  }

  @media (max-width: 1100px) {
    .stop-every.panel {
      min-height: 56px;
      font-size: 20px;
    }
  }

  @media (max-width: 760px) {
    .stop-every.compact {
      min-width: 132px;
      height: 30px;
      padding: 0 12px;
      font-size: 12px;
    }
  }
</style>
