<script>
  export let title = '';
  export let subtitle = '';
  export let onEnter = () => {};
</script>

<button class="card" on:click={onEnter}>
  <div class="title">{title}</div>
  <div class="subtitle">{subtitle}</div>
  <div class="spacer"></div>
  <div class="enter">Open</div>
</button>

<style>
  .card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-start;
    padding: clamp(20px, 5vh, 56px) clamp(20px, 4vw, 52px);
    min-height: clamp(160px, 38vh, 420px);
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-lg);
    text-align: left;
    transition: border-color 0.15s ease, background 0.15s ease;
  }

  .card:hover {
    border-color: var(--border-2);
    background: var(--bg-2);
  }

  .title {
    font-size: clamp(22px, 3.5vw, 38px);
    font-weight: 600;
    line-height: 1.15;
    letter-spacing: -0.02em;
    color: var(--text-0);
  }

  .subtitle {
    margin-top: clamp(6px, 1vh, 14px);
    color: var(--text-2);
    font-size: clamp(11px, 1.4vw, 16px);
    line-height: 1.5;
  }

  .spacer {
    flex: 1;
  }

  .enter {
    color: var(--text-1);
    font-size: 15px;
    font-weight: 500;
  }

  @media (max-width: 600px) {
    .card {
      min-height: clamp(140px, 32vh, 240px);
    }
  }
</style>
