<script>
  export let active = false;
  export let label = 'Perception Stream';
  export let topicName = '/person_detector/waving_image';

  // Dummy detection boxes that float around
  const boxes = [
    { x: 22, y: 34, w: 20, h: 38, label: 'person', conf: 0.94 },
    { x: 58, y: 46, w: 14, h: 22, label: 'cup', conf: 0.81 }
  ];
</script>

<div class="stream" class:active>
  <div class="head">
    <div class="label-row">
      <span class="mono topic">{topicName}</span>
      <span class="label">{label}</span>
    </div>
    <div class="meta mono">
      <span class="dot" class:ok={active} class:idle={!active} />
      <span>{active ? '15.2 Hz' : '0 Hz'}</span>
    </div>
  </div>

  <div class="frame">
    {#if active}
      <!-- Dummy synthetic camera scene -->
      <div class="scene">
        <div class="grid" />
        <div class="horizon" />
        <div class="sweep" />
        {#each boxes as b}
          <div
            class="bbox"
            style="left: {b.x}%; top: {b.y}%; width: {b.w}%; height: {b.h}%"
          >
            <span class="bbox-label mono">{b.label} {Math.round(b.conf * 100)}%</span>
          </div>
        {/each}
        <div class="hud mono">
          <span>DUMMY FEED</span>
          <span>1280×720</span>
        </div>
      </div>
    {:else}
      <div class="placeholder mono">NO SIGNAL — press START</div>
    {/if}
  </div>
</div>

<style>
  .stream {
    display: flex;
    flex-direction: column;
    background: var(--bg-1);
    border: 0.5px solid var(--border-1);
    border-radius: var(--radius-lg);
    padding: 14px;
    height: 100%;
    min-height: 0;
  }

  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .label-row {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .topic {
    font-size: 10px;
    color: var(--text-3);
    letter-spacing: 0.06em;
  }

  .label {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-0);
  }

  .meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    color: var(--text-1);
    padding: 4px 8px;
    background: var(--bg-2);
    border-radius: var(--radius-sm);
  }

  .frame {
    flex: 1;
    position: relative;
    background: var(--bg-0);
    border-radius: var(--radius-md);
    overflow: hidden;
    min-height: 0;
  }

  .placeholder {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-3);
    font-size: 12px;
    letter-spacing: 0.2em;
  }

  .scene {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse at 50% 100%, rgba(59, 130, 246, 0.08), transparent 60%),
      linear-gradient(180deg, #0f1720 0%, #0a0a0a 60%, #000 100%);
    overflow: hidden;
  }

  .grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
    background-size: 40px 40px;
  }

  .horizon {
    position: absolute;
    left: 0;
    right: 0;
    top: 60%;
    height: 1px;
    background: rgba(59, 130, 246, 0.4);
    box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
  }

  .sweep {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 120px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(16, 185, 129, 0.08) 50%,
      transparent 100%
    );
    animation: sweep 3.5s linear infinite;
  }

  @keyframes sweep {
    0% { left: -20%; }
    100% { left: 100%; }
  }

  .bbox {
    position: absolute;
    border: 1.5px solid var(--ok);
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4);
    border-radius: 2px;
  }

  .bbox-label {
    position: absolute;
    top: -18px;
    left: 0;
    font-size: 10px;
    padding: 1px 6px;
    background: var(--ok);
    color: var(--bg-0);
    border-radius: 2px;
    white-space: nowrap;
  }

  .hud {
    position: absolute;
    top: 10px;
    left: 12px;
    right: 12px;
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: rgba(255, 255, 255, 0.5);
    letter-spacing: 0.1em;
  }
</style>
