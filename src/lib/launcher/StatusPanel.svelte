<script>
  import { onMount } from 'svelte';
  import {
    fetchLaunchStatus,
    fetchProfileLogSince,
    launchProfile,
    stopProfile
  } from '$lib/ros.js';

  const TOPIC_CHECK_PROFILE = 'topic_receive_check';
  const TOPIC_TARGETS = [
    '/scan0',
    '/scan1',
    '/scan_merged',
    '/camera/camera_head/color/image_raw',
    '/camera/camera_head/color/image_raw/compressed',
    '/camera/camera_head/depth/image_rect_raw',
    '/livox/lidar'
  ];

  export let nodes = [
    { name: 'base_driver', up: true },
    { name: 'lidar', up: true },
    { name: 'camera_rgb', up: true },
    { name: 'camera_depth', up: true },
    { name: 'nav2', up: false },
    { name: 'manipulation', up: false },
    { name: 'hri_vlm', up: true },
    { name: 'vla', up: false },
    { name: 'vision', up: true },
    { name: 'tts', up: true },
    { name: 'mic_array', up: true }
  ];

  export let peers = [
    { name: 'PC1', offset: 1.2 },
    { name: 'PC2', offset: 0.8 },
    { name: 'Router', offset: 0.3 }
  ];

  let topicsOpen = false;
  let topicsError = '';
  let topicBusy = '';
  let topicRunning = false;
  let topicRows = TOPIC_TARGETS.map((name) => ({
    topic: name,
    status: 'WAIT',
    hz: 0,
    age_s: null,
    delay_ms: null,
    max_delay_ms: null,
    type: '',
    error: '',
    count: 0
  }));
  let topicLastLogTs = null;

  function resetTopicRows() {
    topicRows = TOPIC_TARGETS.map((name) => ({
      topic: name,
      status: 'WAIT',
      hz: 0,
      age_s: null,
      delay_ms: null,
      max_delay_ms: null,
      type: '',
      error: '',
      count: 0
    }));
  }

  function statusClass(status) {
    if (status === 'OK') return 'ok';
    if (status === 'STALE' || status === 'WAIT') return 'warn';
    if (status === 'ERROR') return 'err';
    return 'idle';
  }

  function fmtNumber(value, digits = 1) {
    return Number.isFinite(value) ? value.toFixed(digits) : '-';
  }

  function fmtAge(value) {
    return Number.isFinite(value) ? `${value.toFixed(1)}s` : '-';
  }

  function fmtDelay(value) {
    return Number.isFinite(value) ? `${value.toFixed(1)}ms` : '-';
  }

  function parseTopicLog(line) {
    if (!line || line[0] !== '{') return null;
    try {
      const payload = JSON.parse(line);
      return payload?.event === 'topic' && payload.topic ? payload : null;
    } catch {
      return null;
    }
  }

  function applyTopicEntries(entries) {
    if (!entries?.length) return;

    const byName = new Map(topicRows.map((row) => [row.topic, row]));
    let changed = false;

    for (const entry of entries) {
      if (entry.ts != null) {
        topicLastLogTs = Math.max(topicLastLogTs ?? entry.ts, entry.ts);
      }

      const parsed = parseTopicLog(entry.line);
      if (!parsed || !byName.has(parsed.topic)) continue;

      byName.set(parsed.topic, {
        topic: parsed.topic,
        status: parsed.status ?? 'WAIT',
        hz: Number(parsed.hz ?? 0),
        age_s: parsed.age_s == null ? null : Number(parsed.age_s),
        delay_ms: parsed.delay_ms == null ? null : Number(parsed.delay_ms),
        max_delay_ms: parsed.max_delay_ms == null ? null : Number(parsed.max_delay_ms),
        type: parsed.type ?? '',
        error: parsed.error ?? '',
        count: Number(parsed.count ?? 0)
      });
      changed = true;
    }

    if (changed) {
      topicRows = TOPIC_TARGETS.map((name) => byName.get(name));
    }
  }

  async function refreshTopicStatus() {
    try {
      const payload = await fetchLaunchStatus();
      topicRunning = Boolean(payload?.[TOPIC_CHECK_PROFILE]?.running);
    } catch (error) {
      topicRunning = false;
      topicsError = 'Backend unavailable';
    }
  }

  async function refreshTopicLogs() {
    try {
      const payload = await fetchProfileLogSince(TOPIC_CHECK_PROFILE, topicLastLogTs);
      applyTopicEntries(payload.lines ?? []);
      if (payload.running != null) topicRunning = Boolean(payload.running);
      if (!payload.running && payload.exit_code !== null && payload.exit_code !== 0 && payload.exit_code !== -2) {
        topicsError = `Topic Check stopped: exit ${payload.exit_code}`;
      }
    } catch (error) {
      if (topicRunning) topicsError = error?.message ?? 'Topic log unavailable';
    }
  }

  async function startTopicCheck() {
    topicBusy = 'start';
    topicsError = '';
    topicLastLogTs = null;
    resetTopicRows();
    try {
      await launchProfile(TOPIC_CHECK_PROFILE);
      topicRunning = true;
      await refreshTopicLogs();
    } catch (error) {
      topicsError = error?.message ?? 'Topic Check start failed';
    } finally {
      topicBusy = '';
      refreshTopicStatus();
    }
  }

  async function stopTopicCheck() {
    topicBusy = 'stop';
    topicsError = '';
    try {
      await stopProfile(TOPIC_CHECK_PROFILE);
      topicRunning = false;
    } catch (error) {
      topicsError = error?.message ?? 'Topic Check stop failed';
    } finally {
      topicBusy = '';
      refreshTopicStatus();
    }
  }

  onMount(() => {
    refreshTopicStatus();
    refreshTopicLogs();
    const statusTimer = setInterval(refreshTopicStatus, 1500);
    const logTimer = setInterval(refreshTopicLogs, 1000);
    return () => {
      clearInterval(statusTimer);
      clearInterval(logTimer);
    };
  });

  $: nodesUp = nodes.filter((n) => n.up).length;
  $: topicsOk = topicRows.filter((t) => t.status === 'OK').length;
  $: maxOffset = Math.max(...peers.map((p) => p.offset));
  $: tsLabel = `ok · max ${maxOffset.toFixed(1)}ms`;
  $: topicSummaryLabel = topicRunning ? `${topicsOk} / ${topicRows.length}` : 'idle';
</script>

<div class="panel">
  <div class="main">
    <div class="head">
      <span class="label">Nodes</span>
      <span class="sum mono">{nodesUp} / {nodes.length}</span>
    </div>
    <div class="grid">
      {#each nodes as n}
        <div class="node">
          <span class="dot {n.up ? 'ok' : 'idle'}"></span>
          <span class="name">{n.name}</span>
        </div>
      {/each}
    </div>
  </div>

  <div class="footer">
    <div class="ts">
      <span class="label">Time sync</span>
      <span class="val">{tsLabel}</span>
      <span class="peers mono">{peers.map((p) => `${p.name} ${p.offset.toFixed(1)}ms`).join(' · ')}</span>
    </div>

    <div class="topics-wrap">
      <button class="topics-btn" class:open={topicsOpen} on:click={() => (topicsOpen = !topicsOpen)}>
        <span class="label">Topics</span>
        <span class="val mono">{topicSummaryLabel}</span>
        <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M3 5l3 3 3-3" />
        </svg>
      </button>

      {#if topicsOpen}
        <div class="topics-pop">
          <div class="topics-state">
            <span class="dot {topicRunning ? 'ok' : 'idle'}"></span>
            <span>{topicRunning ? 'subscribing' : 'stopped'}</span>
            <div class="topic-actions">
              <button class="topic-action start" disabled={topicRunning || topicBusy} on:click={startTopicCheck}>
                {topicBusy === 'start' ? 'Starting' : 'Start'}
              </button>
              <button class="topic-action stop" disabled={!topicRunning || topicBusy} on:click={stopTopicCheck}>
                {topicBusy === 'stop' ? 'Stopping' : 'Stop'}
              </button>
            </div>
          </div>

          {#if topicsError}
            <div class="topics-note">{topicsError}</div>
          {/if}

          <div class="topic-table">
            <div class="topic-head">
              <span>Topic</span>
              <span>Hz</span>
              <span>Delay</span>
              <span>Last</span>
              <span>Status</span>
            </div>
            {#each topicRows as t}
              <div class="topic-row">
                <div class="topic-copy">
                  <span class="t-name">{t.topic}</span>
                  <span class="t-meta mono">{t.type || 'waiting type'}</span>
                </div>
                <span class="mono t-num">{fmtNumber(t.hz)}</span>
                <span class="mono t-num">{fmtDelay(t.delay_ms)}</span>
                <span class="mono t-num">{fmtAge(t.age_s)}</span>
                <span class="t-status mono">
                  <span class="dot {statusClass(t.status)}"></span>
                  {t.status}
                </span>
              </div>
              {#if t.error}
                <div class="topic-error">{t.error}</div>
              {/if}
            {/each}
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-lg);
  }

  .main {
    padding: 16px 20px 14px;
  }

  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .label {
    color: var(--text-2);
    font-size: 12px;
    font-weight: 500;
  }

  .sum {
    color: var(--text-0);
    font-size: 14px;
    font-weight: 600;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px 20px;
  }

  .node {
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 0;
  }

  .node .name {
    color: var(--text-1);
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 10px 20px;
    border-top: 1px solid var(--border-1);
    position: relative;
  }

  .ts {
    display: flex;
    align-items: baseline;
    gap: 10px;
    min-width: 0;
    overflow: hidden;
  }

  .ts .val {
    color: var(--text-1);
    font-size: 13px;
  }

  .peers {
    color: var(--text-3);
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .topics-wrap {
    position: relative;
    flex-shrink: 0;
  }

  .topics-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    height: 28px;
    padding: 0 12px;
    color: var(--text-1);
    background: transparent;
    border: 1px solid var(--border-1);
    border-radius: var(--radius);
    font-size: 13px;
  }

  .topics-btn:hover {
    border-color: var(--border-2);
  }

  .topics-btn.open {
    color: var(--text-0);
    border-color: var(--border-3);
    background: var(--bg-2);
  }

  .topics-btn svg {
    transition: transform 0.15s ease;
  }

  .topics-btn.open svg {
    transform: rotate(180deg);
  }

  .topics-pop {
    position: absolute;
    right: 0;
    bottom: calc(100% + 8px);
    width: 720px;
    padding: 10px 14px;
    background: var(--bg-2);
    border: 1px solid var(--border-2);
    border-radius: var(--radius);
    display: flex;
    flex-direction: column;
    gap: 4px;
    z-index: 10;
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.4);
  }

  .topics-state {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-1);
    font-size: 12px;
    margin-bottom: 6px;
  }

  .topic-actions {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .topic-action {
    height: 24px;
    padding: 0 10px;
    border-radius: var(--radius);
    border: 1px solid var(--border-2);
    color: var(--text-1);
    background: var(--bg-1);
    font-size: 12px;
  }

  .topic-action:hover:not(:disabled) {
    border-color: var(--border-3);
    color: var(--text-0);
  }

  .topic-action.start:not(:disabled) {
    border-color: rgba(22, 163, 74, 0.6);
  }

  .topic-action.stop:not(:disabled) {
    border-color: rgba(220, 38, 38, 0.6);
  }

  .topics-note {
    color: var(--text-3);
    font-size: 12px;
    margin-bottom: 6px;
  }

  .topic-table {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--border-1);
    border-radius: var(--radius);
    overflow: hidden;
  }

  .topic-head,
  .topic-row {
    display: grid;
    grid-template-columns: minmax(250px, 1fr) 70px 90px 70px 88px;
    align-items: center;
    gap: 10px;
  }

  .topic-head {
    min-height: 28px;
    padding: 0 10px;
    color: var(--text-3);
    background: var(--bg-1);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .topic-row {
    min-height: 46px;
    padding: 6px 10px;
    font-size: 12px;
    border-top: 1px solid var(--border-1);
  }

  .topic-copy {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .t-name {
    color: var(--text-1);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .t-meta {
    color: var(--text-2);
    font-size: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .t-num {
    color: var(--text-1);
    text-align: right;
  }

  .t-status {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 7px;
    color: var(--text-2);
    font-size: 11px;
  }

  .topic-error {
    padding: 0 10px 8px 10px;
    color: var(--err);
    font-size: 11px;
    border-top: 1px solid var(--border-1);
    background: var(--bg-2);
  }
</style>
