<script>
  import { launchProfile, stopProfile } from '$lib/ros.js';

  export let started = false;
  export let nodeRunning = false;

  let nodeBusy = false;

  async function toggleNode() {
    nodeBusy = true;
    try {
      if (nodeRunning) {
        try { await stopProfile('competition'); } catch (e) { console.warn(e); }
      } else {
        try { await launchProfile('competition'); } catch (e) { console.warn(e); }
      }
      nodeRunning = !nodeRunning;
    } finally {
      nodeBusy = false;
    }
  }

  function toggleStart() {
    started = !started;
  }
</script>

<section class="panel">
  <div class="kicker">CONTROL</div>

  <button class="start" class:running={started} on:click={toggleStart}>
    <div class="start-ring">
      <div class="start-inner">
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          {#if started}
            <rect x="6" y="6" width="12" height="12" rx="1.5" fill="currentColor" stroke="none" />
          {:else}
            <path d="M8 5v14l11-7z" fill="currentColor" stroke="none" />
          {/if}
        </svg>
      </div>
    </div>
    <div class="start-label mono">{started ? 'STOP' : 'START'}</div>
    <div class="start-hint">
      {started ? 'Behavior tree running' : 'Tap to begin the run'}
    </div>
  </button>

  <button
    class="node"
    class:running={nodeRunning}
    class:busy={nodeBusy}
    on:click={toggleNode}
  >
    <div class="node-top">
      <span class="node-label">Launch Nodes</span>
      <span
        class="dot"
        class:ok={nodeRunning}
        class:idle={!nodeRunning}
      />
    </div>
    <div class="node-desc mono">competition.launch.py</div>
    <div class="node-hint">Bring up full perception + planning stack</div>
    <div class="node-action">
      <span class="action-label">
        {nodeBusy ? '...' : nodeRunning ? 'Stop Nodes' : 'Launch Nodes'}
      </span>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        {#if nodeRunning}
          <rect x="6" y="6" width="12" height="12" rx="1" fill="currentColor" stroke="none" />
        {:else}
          <path d="M8 5v14l11-7z" fill="currentColor" stroke="none" />
        {/if}
      </svg>
    </div>
  </button>
</section>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
    height: 100%;
  }

  .kicker {
    font-size: 11px;
    letter-spacing: 0.12em;
    color: var(--text-2);
  }

  /* ─── Start button ─────────────────────────────── */
  .start {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    padding: 28px 20px 24px;
    background: var(--bg-1);
    border: 0.5px solid var(--border-1);
    border-radius: var(--radius-lg);
    color: inherit;
    transition: all 0.2s;
  }

  .start:hover {
    border-color: var(--border-3);
  }

  .start.running {
    border-color: var(--warn);
    background: rgba(245, 158, 11, 0.04);
  }

  .start-ring {
    width: 140px;
    height: 140px;
    border-radius: 50%;
    border: 2px solid var(--ok);
    padding: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    box-shadow: 0 0 40px rgba(16, 185, 129, 0.18);
  }

  .start.running .start-ring {
    border-color: var(--warn);
    box-shadow: 0 0 40px rgba(245, 158, 11, 0.25);
  }

  .start-inner {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: var(--ok);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--bg-0);
    transition: background 0.2s;
  }

  .start.running .start-inner {
    background: var(--warn);
  }

  .start:active .start-inner {
    transform: scale(0.94);
  }

  .start-label {
    font-size: 22px;
    font-weight: 500;
    letter-spacing: 0.2em;
    color: var(--text-0);
  }

  .start-hint {
    font-size: 11px;
    color: var(--text-3);
    letter-spacing: 0.05em;
  }

  /* ─── Node launch button ───────────────────────── */
  .node {
    text-align: left;
    background: var(--bg-1);
    border: 0.5px solid var(--border-1);
    border-radius: var(--radius-lg);
    padding: 20px 22px;
    color: inherit;
    transition: border-color 0.15s;
  }

  .node:hover {
    border-color: var(--border-3);
  }

  .node.running {
    border-color: var(--border-2);
    background: var(--bg-2);
  }

  .node-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .node-label {
    font-size: 18px;
    font-weight: 500;
    color: var(--text-0);
  }

  .node-desc {
    font-size: 12px;
    color: var(--text-2);
    margin-bottom: 4px;
  }

  .node-hint {
    font-size: 12px;
    color: var(--text-3);
  }

  .node-action {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 14px;
    padding-top: 14px;
    border-top: 0.5px solid var(--border-1);
    color: var(--text-1);
  }

  .node.running .node-action {
    color: var(--warn);
  }

  .action-label {
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
</style>
