<script>
  import { exitApplication } from '$lib/ros.js';

  export let variant = 'compact';

  let exiting = false;

  async function handleExit() {
    if (exiting) return;
    exiting = true;

    try {
      await exitApplication();
    } catch (error) {
      console.error('Exit request failed', error);
    }

    setTimeout(() => {
      window.close();
      setTimeout(() => {
        if (!document.hidden) {
          window.location.replace('about:blank');
        }
      }, 180);
    }, 120);

    setTimeout(() => {
      exiting = false;
    }, 2000);
  }
</script>

<button class="exit {variant}" disabled={exiting} on:click={handleExit}>
  {exiting ? 'Exiting...' : 'Exit'}
</button>

<style>
  .exit {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--text-0);
    border: 1px solid rgba(248, 113, 113, 0.28);
    background: rgba(248, 113, 113, 0.1);
    transition: border-color 0.12s ease, background 0.12s ease;
  }

  .exit:hover {
    border-color: rgba(248, 113, 113, 0.42);
    background: rgba(248, 113, 113, 0.16);
  }

  .exit:disabled {
    opacity: 0.72;
  }

  .exit.compact {
    min-width: 84px;
    height: 34px;
    padding: 0 14px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
  }

  .exit.panel {
    width: 100%;
    min-height: 62px;
    padding: 0 18px;
    border-radius: 16px;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.03em;
  }

  @media (max-width: 1100px) {
    .exit.panel {
      min-height: 56px;
      font-size: 20px;
    }
  }

  @media (max-width: 760px) {
    .exit.compact {
      min-width: 72px;
      height: 30px;
      padding: 0 12px;
      font-size: 12px;
    }
  }
</style>
