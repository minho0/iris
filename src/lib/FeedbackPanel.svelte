<script>
  import { onMount } from 'svelte';

  // Dummy feedback streams — 나중에 실제 토픽으로 교체
  const heardSamples = [
    { t: '14:23:02', text: 'Hello robot, can you bring me a cup?', conf: 0.91 },
    { t: '14:23:10', text: 'The cup is on the table.', conf: 0.87 },
    { t: '14:23:18', text: 'Thank you.', conf: 0.94 }
  ];

  const detectionSamples = [
    { cls: 'person', conf: 0.94, box: [210, 180, 320, 540] },
    { cls: 'cup', conf: 0.81, box: [720, 360, 840, 500] },
    { cls: 'table', conf: 0.78, box: [520, 520, 1100, 720] }
  ];

  const sensorSamples = [
    { k: 'battery', v: '87%', status: 'ok' },
    { k: 'nav_goal_dist', v: '1.42 m', status: 'ok' },
    { k: 'mic_rms', v: '-24 dBFS', status: 'ok' },
    { k: 'cpu_load', v: '34%', status: 'ok' }
  ];

  let heardIdx = 0;
  let detIdx = 0;

  let timer1, timer2;

  onMount(() => {
    timer1 = setInterval(() => (heardIdx = (heardIdx + 1) % heardSamples.length), 3000);
    timer2 = setInterval(() => (detIdx = (detIdx + 1) % detectionSamples.length), 1500);
    return () => {
      clearInterval(timer1);
      clearInterval(timer2);
    };
  });

  $: heard = heardSamples[heardIdx];
  $: det = detectionSamples[detIdx];
</script>

<section class="feedback">
  <!-- ─── Camera / perception image ─────────────── -->
  <div class="image-card">
    <div class="card-head">
      <span class="mono topic">/person_detector/waving_image</span>
      <span class="label">Perception</span>
      <div class="meta mono">
        <span class="dot ok" />
        <span>15.2 Hz</span>
      </div>
    </div>
    <div class="frame">
      <div class="scene">
        <div class="grid" />
        <div class="horizon" />
        <div class="sweep" />
        <div
          class="bbox"
          style="left: {(det.box[0] / 1280) * 100}%; top: {(det.box[1] / 720) * 100}%;
                 width: {((det.box[2] - det.box[0]) / 1280) * 100}%;
                 height: {((det.box[3] - det.box[1]) / 720) * 100}%"
        >
          <span class="bbox-label mono">{det.cls} {Math.round(det.conf * 100)}%</span>
        </div>
        <div class="hud mono">
          <span>DUMMY FEED · 1280×720</span>
          <span>det: {det.cls}</span>
        </div>
      </div>
    </div>
  </div>

  <!-- ─── Heard / speech ────────────────────────── -->
  <div class="card heard">
    <div class="card-head">
      <span class="kicker">HEARD</span>
      <span class="mono conf">conf {Math.round(heard.conf * 100)}%</span>
    </div>
    <div class="heard-text">"{heard.text}"</div>
    <div class="heard-foot mono">
      <span class="dot ok" />
      <span>{heard.t}</span>
      <span class="source">/speech/asr_result</span>
    </div>
  </div>

  <!-- ─── Sensor / blackboard mini-stats ─────────── -->
  <div class="card stats">
    <div class="card-head">
      <span class="kicker">TELEMETRY</span>
    </div>
    <div class="stat-grid">
      {#each sensorSamples as s}
        <div class="stat">
          <div class="stat-k mono">{s.k}</div>
          <div class="stat-v mono">{s.v}</div>
        </div>
      {/each}
    </div>
  </div>
</section>

<style>
  .feedback {
    display: grid;
    grid-template-rows: minmax(0, 1.4fr) auto auto;
    gap: 18px;
    height: 100%;
    min-height: 0;
  }

  .card,
  .image-card {
    background: var(--bg-1);
    border: 0.5px solid var(--border-1);
    border-radius: var(--radius-lg);
    padding: 18px 20px;
  }

  .image-card {
    padding: 14px;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .card-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }

  .kicker {
    font-size: 11px;
    letter-spacing: 0.12em;
    color: var(--text-2);
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
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    color: var(--text-1);
    padding: 4px 10px;
    background: var(--bg-2);
    border-radius: var(--radius-sm);
  }

  /* ─── Image frame ─────────────────────────────── */
  .frame {
    flex: 1;
    position: relative;
    background: var(--bg-0);
    border-radius: var(--radius-md);
    overflow: hidden;
    min-height: 0;
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
    background-size: 48px 48px;
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
    width: 140px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(16, 185, 129, 0.1) 50%,
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
    transition: all 0.4s ease-out;
  }

  .bbox-label {
    position: absolute;
    top: -20px;
    left: 0;
    font-size: 11px;
    padding: 2px 7px;
    background: var(--ok);
    color: var(--bg-0);
    border-radius: 2px;
    white-space: nowrap;
  }

  .hud {
    position: absolute;
    top: 12px;
    left: 14px;
    right: 14px;
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: rgba(255, 255, 255, 0.55);
    letter-spacing: 0.1em;
  }

  /* ─── Heard card ──────────────────────────────── */
  .heard .conf {
    margin-left: auto;
    font-size: 11px;
    color: var(--text-2);
  }

  .heard-text {
    font-size: 22px;
    color: var(--text-0);
    font-weight: 400;
    line-height: 1.4;
    padding: 6px 0 14px;
  }

  .heard-foot {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 11px;
    color: var(--text-2);
  }

  .heard-foot .source {
    margin-left: auto;
    color: var(--text-3);
  }

  /* ─── Telemetry stats ─────────────────────────── */
  .stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
    gap: 14px;
  }

  .stat {
    background: var(--bg-0);
    padding: 10px 12px;
    border-radius: var(--radius-md);
  }

  .stat-k {
    font-size: 10px;
    color: var(--text-3);
    letter-spacing: 0.08em;
    margin-bottom: 4px;
  }

  .stat-v {
    font-size: 17px;
    color: var(--text-0);
    font-weight: 500;
  }
</style>
