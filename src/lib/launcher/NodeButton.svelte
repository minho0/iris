<script>
  export let name = '';
  export let desc = '';
  export let status = 'down'; // 'down' | 'starting' | 'up'
  export let live = null;     // { label, tone } where tone in 'ok' | 'warn' | 'err'
  export let onToggle = () => {};
  export let onLogs = null;
  export let logsOpen = false;

  $: dotClass = status === 'up' ? 'ok' : status === 'starting' ? 'warn' : 'idle';
  $: action = status === 'up' ? 'Stop' : status === 'starting' ? '…' : 'Start';
  $: actionDisabled = status === 'starting';
  $: showLogs = typeof onLogs === 'function';
</script>

<div class="row {status}">
  <span class="dot {dotClass}"></span>

  <div class="info">
    <div class="name">{name}</div>
    {#if desc}<div class="desc">{desc}</div>{/if}
    {#if live}<div class="live mono {live.tone ?? ''}">{live.label}</div>{/if}
  </div>

  <div class="actions">
    {#if showLogs}
      <button
        class="logs"
        class:active={logsOpen}
        on:click={onLogs}
        type="button"
      >
        {logsOpen ? 'Hide logs' : 'Logs'}
      </button>
    {/if}

    <button
      class="action {status === 'up' ? 'stop' : ''}"
      on:click={onToggle}
      disabled={actionDisabled}
      type="button"
    >
      {action}
    </button>
  </div>
</div>

<style>
  .row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius);
  }

  .row.up {
    border-color: rgba(22, 163, 74, 0.28);
  }

  .info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .name {
    color: var(--text-0);
    font-size: 13px;
    font-weight: 500;
    letter-spacing: -0.005em;
  }

  .desc {
    color: var(--text-2);
    font-size: 11px;
    line-height: 1.3;
  }

  .live {
    margin-top: 2px;
    color: var(--text-2);
    font-size: 11px;
  }

  .live.ok { color: var(--ok); }
  .live.warn { color: var(--warn); }
  .live.err { color: var(--err); }

  .action {
    flex-shrink: 0;
    height: 24px;
    padding: 0 10px;
    color: var(--text-1);
    background: var(--bg-1);
    border: 1px solid var(--border-2);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;
  }

  .action:hover:not(:disabled) {
    color: var(--text-0);
    background: var(--bg-2);
    border-color: var(--border-3);
  }

  .action.stop {
    color: var(--err);
    border-color: rgba(220, 38, 38, 0.28);
    background: #ffffff;
  }

  .action.stop:hover:not(:disabled) {
    background: rgba(220, 38, 38, 0.06);
  }

  .action:disabled {
    opacity: 0.5;
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .logs {
    flex-shrink: 0;
    height: 24px;
    padding: 0 10px;
    color: var(--text-2);
    background: transparent;
    border: 1px solid var(--border-1);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;
  }

  .logs:hover {
    color: var(--text-0);
    background: #ffffff;
    border-color: var(--border-3);
  }

  .logs.active {
    color: var(--text-0);
    background: #ffffff;
    border-color: var(--border-3);
  }

  @media (max-width: 760px) {
    .row {
      align-items: flex-start;
      flex-direction: column;
      gap: 8px;
    }

    .actions {
      width: 100%;
      justify-content: flex-end;
    }
  }
</style>
