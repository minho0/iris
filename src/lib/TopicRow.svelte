<script>
  export let name;
  export let hzStore;
  export let min;

  $: hz = $hzStore;

  $: health =
    min === 0 ? (hz > 0 ? 'ok' : 'idle') : hz >= min ? 'ok' : hz > 0 ? 'warn' : 'err';
</script>

<div class="row">
  <span class="dot {health}" />
  <span class="name mono">{name}</span>
  <span class="rate mono">{hz} Hz</span>
</div>

<style>
  .row {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 0.5px solid var(--border-1);
    font-size: 12px;
  }

  .row:last-child {
    border-bottom: none;
  }

  .name {
    color: var(--text-1);
  }

  .rate {
    color: var(--text-2);
    font-size: 11px;
  }
</style>
