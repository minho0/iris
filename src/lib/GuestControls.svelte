<script>
  import { launchProfile, stopProfile } from '$lib/ros.js';

  export let started = false;
  export let nodeRunning = false;

  let nodeBusy = false;

  async function toggleNode() {
    nodeBusy = true;
    try {
      if (nodeRunning) {
        try {
          await stopProfile('competition');
        } catch (e) {
          console.warn(e);
        }
      } else {
        try {
          await launchProfile('competition');
        } catch (e) {
          console.warn(e);
        }
      }
      nodeRunning = !nodeRunning;
    } finally {
      nodeBusy = false;
    }
  }

  function toggleScreen() {
    started = !started;
  }
</script>

<section class="controls">
  <button class="primary" class:running={started} on:click={toggleScreen}>
    <span class="icon">
      {#if started}
        <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="1.5"></rect>
        </svg>
      {:else}
        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
          <path d="M8 5v14l11-7z"></path>
        </svg>
      {/if}
    </span>
    <span>{started ? '화면 정지' : '손님 화면 시작'}</span>
  </button>

  <button class="secondary" class:running={nodeRunning} on:click={toggleNode}>
    <span class="dot" class:ok={nodeRunning} class:idle={!nodeRunning}></span>
    <span>{nodeBusy ? '처리 중' : nodeRunning ? '노드 실행 중' : '노드 실행'}</span>
  </button>
</section>

<style>
  .controls {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
  }

  button {
    min-height: 58px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 0 18px;
    border-radius: var(--radius-md);
    font-size: 17px;
    font-weight: 750;
  }

  .primary {
    color: #061008;
    background: var(--ok);
  }

  .primary.running {
    color: #1c1000;
    background: var(--warn);
  }

  .secondary {
    color: var(--text-1);
    background: var(--bg-1);
    border: 1px solid var(--border-1);
  }

  .secondary.running {
    color: var(--ok);
    border-color: rgba(34, 197, 94, 0.34);
    background: var(--ok-soft);
  }

  .icon {
    width: 28px;
    height: 28px;
    display: grid;
    place-items: center;
  }
</style>
