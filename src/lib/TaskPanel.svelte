<script>
  import { topic } from '$lib/ros.js';

  // ROS 2에서 /robot_state 토픽 (std_msgs/String, JSON 포맷)
  //   { task: "Receptionist", phase: "Searching waving person",
  //     step: 3, total: 7, elapsed: 42, status: "running" }
  const { value: state } = topic('/robot_state', 'std_msgs/msg/String');

  // JSON 파싱 + 기본값
  $: data = (() => {
    try {
      return JSON.parse($state?.data ?? '{}');
    } catch {
      return {};
    }
  })();

  $: task = data.task ?? 'Idle';
  $: phase = data.phase ?? 'Waiting for command';
  $: step = data.step ?? 0;
  $: total = data.total ?? 0;
  $: elapsed = data.elapsed ?? 0;
  $: status = data.status ?? 'idle'; // running | idle | error | done
  $: progress = total > 0 ? (step / total) * 100 : 0;

  $: statusColor =
    status === 'running'
      ? 'ok'
      : status === 'error'
        ? 'err'
        : status === 'done'
          ? 'ok'
          : 'idle';

  function fmtTime(s) {
    const m = Math.floor(s / 60);
    const ss = String(Math.floor(s % 60)).padStart(2, '0');
    return `${m}:${ss}`;
  }
</script>

<section class="task">
  <div class="head">
    <span class="kicker">CURRENT TASK</span>
    <div class="badge">
      <span class="dot {statusColor}" />
      <span class="mono">{status.toUpperCase()}</span>
    </div>
  </div>

  <div class="title">{task}</div>
  <div class="phase">{phase}</div>

  <div class="progress">
    <div class="bar">
      <div class="fill" style="width: {progress}%" />
    </div>
    <div class="progress-meta mono">
      <span>{step} / {total}</span>
      <span>{fmtTime(elapsed)} elapsed</span>
    </div>
  </div>

  <div class="recent">
    <div class="recent-head">RECENT ACTIONS</div>
    <ul class="log mono">
      <li><span class="t">14:22:41</span> Navigating to living_room</li>
      <li><span class="t">14:22:58</span> Arrived at waypoint_3</li>
      <li class="active"><span class="t">14:23:02</span> Scanning for waving gesture</li>
    </ul>
  </div>
</section>

<style>
  .task {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg-1);
    border: 0.5px solid var(--border-1);
    border-radius: var(--radius-lg);
    padding: 28px;
  }

  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
  }

  .kicker {
    font-size: 11px;
    letter-spacing: 0.12em;
    color: var(--text-2);
  }

  .badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 10px;
    background: var(--bg-2);
    border-radius: var(--radius-sm);
    font-size: 11px;
    color: var(--text-1);
  }

  .title {
    font-size: 36px;
    font-weight: 500;
    color: var(--text-0);
    letter-spacing: -0.01em;
    margin-bottom: 6px;
  }

  .phase {
    font-size: 16px;
    color: var(--text-1);
    margin-bottom: 28px;
  }

  .progress {
    margin-bottom: 32px;
  }

  .bar {
    height: 3px;
    background: var(--border-1);
    border-radius: 2px;
    overflow: hidden;
  }

  .fill {
    height: 100%;
    background: var(--ok);
    border-radius: 2px;
    transition: width 0.3s ease-out;
  }

  .progress-meta {
    display: flex;
    justify-content: space-between;
    margin-top: 10px;
    font-size: 11px;
    color: var(--text-2);
  }

  .recent {
    margin-top: auto;
    padding-top: 20px;
    border-top: 0.5px solid var(--border-1);
  }

  .recent-head {
    font-size: 10px;
    letter-spacing: 0.12em;
    color: var(--text-3);
    margin-bottom: 12px;
  }

  .log {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 12px;
    color: var(--text-2);
  }

  .log li {
    display: flex;
    gap: 12px;
  }

  .log li .t {
    color: var(--text-3);
  }

  .log li.active {
    color: var(--text-0);
  }

  .log li.active .t {
    color: var(--ok);
  }
</style>
