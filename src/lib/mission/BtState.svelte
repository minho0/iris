<script>
  export let running = false;
  export let state = { current: '—' };
  export let embedded = false;
</script>

<section class="bt" class:embedded>
  <div class="current" class:blink={running}>
    {state.current ?? '—'}
  </div>
</section>

<style>
  .bt {
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 10px 18px;
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-lg);
  }

  .bt.embedded {
    border: none;
    border-radius: 0;
  }

  .current {
    color: var(--text-0);
    font-size: clamp(24px, 2.8vw, 44px);
    font-weight: 700;
    letter-spacing: 0;
    line-height: 1.05;
    text-align: center;
    word-break: keep-all;
  }

  .blink {
    animation: blink 1.1s steps(1, end) infinite;
  }

  @keyframes blink {
    0%,
    48% {
      opacity: 1;
    }
    50%,
    100% {
      opacity: 0.24;
    }
  }
</style>
