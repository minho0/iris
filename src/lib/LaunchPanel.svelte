<script>
  import { launchProfile, stopProfile } from '$lib/ros.js';

  // 현재 실행 상태 — 실제로는 서버 poll 해서 받아오는 게 맞음
  let running = { competition: false, debug: false };
  let busy = { competition: false, debug: false };

  async function toggle(profile) {
    busy[profile] = true;
    try {
      if (running[profile]) {
        await stopProfile(profile);
        running[profile] = false;
      } else {
        await launchProfile(profile);
        running[profile] = true;
      }
    } catch (e) {
      console.error(e);
    } finally {
      busy[profile] = false;
    }
  }

  const profiles = [
    {
      id: 'competition',
      title: 'Competition',
      desc: 'all_nodes.launch.py',
      hint: 'Full stack for the run',
      accent: 'var(--ok)'
    },
    {
      id: 'debug',
      title: 'Debug',
      desc: 'debug.launch.py',
      hint: 'Verbose + RViz2 bridge',
      accent: 'var(--warn)'
    }
  ];
</script>

<section class="launch">
  <div class="kicker">LAUNCH PROFILES</div>

  <div class="profiles">
    {#each profiles as p}
      <button
        class="card"
        class:running={running[p.id]}
        class:busy={busy[p.id]}
        on:click={() => toggle(p.id)}
      >
        <div class="card-top">
          <span class="card-label">{p.title}</span>
          <span
            class="dot"
            class:ok={running[p.id]}
            class:idle={!running[p.id]}
            style="background: {running[p.id] ? p.accent : 'var(--text-3)'}"
          />
        </div>
        <div class="card-desc mono">{p.desc}</div>
        <div class="card-hint">{p.hint}</div>

        <div class="action">
          <span class="action-label">
            {busy[p.id] ? '...' : running[p.id] ? 'Stop' : 'Launch'}
          </span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            {#if running[p.id]}
              <rect x="6" y="6" width="12" height="12" rx="1" fill="currentColor" stroke="none" />
            {:else}
              <path d="M8 5v14l11-7z" fill="currentColor" stroke="none" />
            {/if}
          </svg>
        </div>
      </button>
    {/each}
  </div>

  <button class="estop">
    <div class="estop-ring">
      <div class="estop-inner">
        <div class="estop-label">STOP</div>
      </div>
    </div>
    <div class="estop-hint">Tap to halt all motion</div>
  </button>
</section>

<style>
  .launch {
    display: flex;
    flex-direction: column;
    gap: 16px;
    height: 100%;
  }

  .kicker {
    font-size: 11px;
    letter-spacing: 0.12em;
    color: var(--text-2);
  }

  .profiles {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .card {
    position: relative;
    text-align: left;
    background: var(--bg-1);
    border: 0.5px solid var(--border-1);
    border-radius: var(--radius-lg);
    padding: 20px 22px;
    color: inherit;
    transition: border-color 0.15s;
  }

  .card:hover {
    border-color: var(--border-3);
  }

  .card.running {
    border-color: var(--border-2);
    background: var(--bg-2);
  }

  .card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .card-label {
    font-size: 18px;
    font-weight: 500;
    color: var(--text-0);
  }

  .card-desc {
    font-size: 12px;
    color: var(--text-2);
    margin-bottom: 4px;
  }

  .card-hint {
    font-size: 12px;
    color: var(--text-3);
  }

  .action {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 14px;
    padding-top: 14px;
    border-top: 0.5px solid var(--border-1);
    color: var(--text-1);
  }

  .action-label {
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .card.running .action {
    color: var(--warn);
  }

  /* Emergency stop — bottom anchored, big touch target */
  .estop {
    margin-top: auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 18px 0 6px;
  }

  .estop-ring {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    border: 2px solid var(--err);
    padding: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
  }

  .estop-inner {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: var(--err);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 32px rgba(239, 68, 68, 0.25);
  }

  .estop-label {
    font-family: var(--font-mono);
    font-size: 18px;
    font-weight: 500;
    letter-spacing: 0.15em;
    color: white;
  }

  .estop:active .estop-inner {
    transform: scale(0.92);
  }

  .estop-hint {
    font-size: 11px;
    color: var(--text-3);
    letter-spacing: 0.05em;
  }
</style>
