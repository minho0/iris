<script>
  import { topic } from '$lib/ros.js';
  import TopicRow from './TopicRow.svelte';

  const topics = [
    { name: '/scan', type: 'sensor_msgs/msg/LaserScan', min: 5 },
    { name: '/odom', type: 'nav_msgs/msg/Odometry', min: 10 },
    { name: '/cmd_vel', type: 'geometry_msgs/msg/Twist', min: 0 },
    { name: '/tf', type: 'tf2_msgs/msg/TFMessage', min: 20 },
    { name: '/joint_states', type: 'sensor_msgs/msg/JointState', min: 20 },
    { name: '/battery_state', type: 'sensor_msgs/msg/BatteryState', min: 0 }
  ];

  const subs = topics.map((t) => ({ ...t, ...topic(t.name, t.type) }));
</script>

<div class="monitor">
  <div class="kicker">TOPICS</div>
  <div class="list">
    {#each subs as s (s.name)}
      <TopicRow name={s.name} hzStore={s.hz} min={s.min} />
    {/each}
  </div>
</div>

<style>
  .monitor {
    background: var(--bg-1);
    border: 0.5px solid var(--border-1);
    border-radius: var(--radius-lg);
    padding: 16px 18px;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .kicker {
    font-size: 11px;
    letter-spacing: 0.12em;
    color: var(--text-2);
    margin-bottom: 12px;
  }

  .list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
  }
</style>
