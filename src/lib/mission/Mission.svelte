<script>
  import { onMount } from 'svelte';
  import {
    fetchBtMessage,
    fetchBtState,
    fetchLaunchStatus,
    fetchProfileLog,
    launchProfile,
    stopProfile
  } from '$lib/ros.js';
  import { localFixedUi } from '$lib/uiMode.js';
  import BackBar from '$lib/common/BackBar.svelte';
  import GuestAid from './GuestAid.svelte';
  import BtState from './BtState.svelte';

  const missionModes = [
    { id: 'hri', label: 'HRI', profile: 'bt_hri' },
    { id: 'pickandplace', label: 'Pick and Place', shortLabel: 'Pick Place', profile: 'bt_pickandplace' },
    { id: 'restaurant', label: 'Restaurant', profile: 'bt_restaurant' },
    { id: 'gpsr', label: 'GPSR', profile: 'bt_gpsr' },
    { id: 'laundry', label: 'Laundry', profile: 'bt_laundry' },
    { id: 'final', label: 'Final', profile: 'bt_final' }
  ];

  let selectedMode = 'hri';
  let runningProfile = '';
  let busy = false;
  let backendOffline = false;
  let controlError = '';
  let logTitle = 'BT Log';
  let logMeta = '';
  let logText = '';
  let logLoading = false;
  let showLogDetails = false;
  let btStatePayload = null;
  let btMessagePayload = null;
  let btPollTimer = null;
  let mounted = false;

  async function openLogDetails() {
    const profile = runningProfile || selectedMission.profile;
    const mode = runningMode ?? selectedMission;

    logTitle = controlError ? 'BT Error Log' : 'BT Log';
    logMeta = mode.label;
    logText = '';
    logLoading = true;
    showLogDetails = true;

    try {
      const payload = await fetchProfileLog(profile, 50);
      const lines = payload.lines ?? [];
      const tail = lines.length
        ? lines.map((entry) => entry.line ?? String(entry)).join('\n')
        : '(no log lines)';

      logText = controlError
        ? `${controlError}\n\n--- current last 50 log lines ---\n${tail}`
        : `--- last 50 log lines ---\n${tail}`;
    } catch (error) {
      logText = `Could not load logs: ${error?.message ?? error}`;
    } finally {
      logLoading = false;
    }
  }

  async function refreshMissionStatus() {
    try {
      const payload = await fetchLaunchStatus();
      backendOffline = false;

      const liveMode = missionModes.find((mode) => payload?.[mode.profile]?.running);
      runningProfile = liveMode?.profile ?? '';

      if (liveMode && !busy) {
        selectedMode = liveMode.id;
      }
    } catch {
      backendOffline = true;
    }
  }

  async function refreshBtStatus() {
    if (!running) return;

    try {
      const [statePayload, messagePayload] = await Promise.all([
        fetchBtState(),
        fetchBtMessage()
      ]);
      btStatePayload = statePayload;
      btMessagePayload = messagePayload;
    } catch {
      btStatePayload = null;
      btMessagePayload = null;
    }
  }

  function startBtPolling() {
    if (btPollTimer) return;
    refreshBtStatus();
    btPollTimer = setInterval(refreshBtStatus, 400);
  }

  function stopBtPolling() {
    if (btPollTimer) {
      clearInterval(btPollTimer);
      btPollTimer = null;
    }
    btStatePayload = null;
    btMessagePayload = null;
  }

  async function enterFullscreen() {
    if (typeof document === 'undefined') return;
    if (document.fullscreenElement) return;
    try {
      await document.documentElement.requestFullscreen?.();
    } catch {
      // ignored — user gesture or permission may be missing
    }
  }

  async function exitFullscreen() {
    if (typeof document === 'undefined') return;
    if (!document.fullscreenElement) return;
    try {
      await document.exitFullscreen?.();
    } catch {
      // ignored
    }
  }

  async function toggle() {
    if (busy) return;

    busy = true;
    controlError = '';
    showLogDetails = false;

    const nextErrorTitle = runningProfile ? 'BT Stop Error' : 'BT Start Error';
    const nextErrorMeta = runningMode?.label ?? selectedMission.label;
    const wasRunning = Boolean(runningProfile);

    if (!wasRunning) {
      await enterFullscreen();
    }

    try {
      if (wasRunning) {
        await stopProfile(runningProfile);
      } else {
        await launchProfile(selectedMission.profile);
      }
    } catch (error) {
      logTitle = nextErrorTitle;
      logMeta = nextErrorMeta;
      controlError = error?.message ?? 'mission control failed';
    } finally {
      busy = false;
      await refreshMissionStatus();
      if (wasRunning) {
        await exitFullscreen();
      }
    }
  }

  onMount(() => {
    mounted = true;
    refreshMissionStatus();
    const timer = setInterval(refreshMissionStatus, 1500);
    return () => {
      mounted = false;
      clearInterval(timer);
      stopBtPolling();
    };
  });

  $: selectedMission = missionModes.find((mode) => mode.id === selectedMode) ?? missionModes[0];
  $: runningMode = missionModes.find((mode) => mode.profile === runningProfile);
  $: running = Boolean(runningProfile);
  $: controlLabel = busy ? (running ? 'Stopping' : 'Starting') : running ? 'Stop' : 'Start';
  $: if (mounted) {
    if (running) {
      startBtPolling();
    } else {
      stopBtPolling();
    }
  }
  $: btStateLabel = btStatePayload?.state ?? '—';
  $: btStateActive = Boolean(btStatePayload?.state);
</script>

<div class="mission" class:local-fixed-ui={$localFixedUi} class:running>
  {#if !running}
    <BackBar title="Mission" to="landing" />
  {/if}

  <div class="body" class:running>
    <section class="card guest-card">
      {#if !running}
        <div class="card-head">
          <span class="card-title">Guest screen</span>
          <span class="card-meta mono">{running ? 'running' : 'ready'}</span>
        </div>
      {/if}
      <div class="card-body guest-body">
        <GuestAid
          embedded={true}
          {running}
          text="Mission running"
          {btStatePayload}
          {btMessagePayload}
        />
      </div>
    </section>

    {#if running}
      <section class="card bt-card">
        <div class="card-body bt-body">
          <BtState embedded={true} running={btStateActive} state={{ current: btStateLabel }} />
        </div>
      </section>
    {/if}

    {#if !running}
      <section class="card mode-card">
        <div class="card-head">
          <span class="card-title">Mode</span>
          <div class="mode-actions">
            <span class="card-meta mono">
              {#if controlError}
                error
              {:else if backendOffline}
                offline
              {:else if runningMode}
                running
              {:else}
                ready
              {/if}
            </span>
            <button type="button" class="log-chip mono" on:click={openLogDetails}>
              log
            </button>
          </div>
        </div>
        <div class="card-body mode-body">
          <div class="mode-options" title={controlError}>
            {#each missionModes as mode (mode.id)}
              <button
                type="button"
                class="mode-option"
                class:active={selectedMode === mode.id}
                disabled={running || busy}
                on:click={() => (selectedMode = mode.id)}
              >
                {mode.shortLabel ?? mode.label}
              </button>
            {/each}
          </div>
        </div>
      </section>
    {/if}

    <div class="control">
      <button type="button" class="control-btn" class:stop={running} disabled={busy} on:click={toggle}>
        {controlLabel}
      </button>
    </div>
  </div>

  {#if showLogDetails}
    <div class="error-backdrop" role="presentation" on:click={() => (showLogDetails = false)}>
      <section class="error-dialog" role="dialog" aria-modal="true" aria-label={logTitle} on:click|stopPropagation>
        <div class="error-head">
          <div class="error-copy">
            <span class="error-title">{logTitle}</span>
            <span class="error-meta mono">{logMeta}</span>
          </div>
          <button type="button" class="error-close" on:click={() => (showLogDetails = false)}>
            Close
          </button>
        </div>
        <pre class="error-log">{logLoading ? 'Loading logs...' : logText}</pre>
      </section>
    </div>
  {/if}
</div>

<style>
  .mission {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .mission :global(.bar) {
    padding: 6px 16px;
    min-height: 40px;
  }

  .mission :global(.bar .back) {
    width: 30px;
    height: 30px;
  }

  .mission.running {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: var(--bg-0);
  }

  .body {
    flex: 1;
    padding: clamp(4px, 0.8vh, 14px) clamp(6px, 0.9vw, 16px);
    display: grid;
    grid-template-columns: minmax(0, 1fr) clamp(140px, 16vw, 280px);
    grid-template-rows: minmax(0, 1fr) clamp(110px, 22vh, 280px);
    grid-template-areas:
      "guest guest"
      "mode control";
    gap: clamp(4px, 0.8vw, 12px);
    min-height: 0;
    overflow: hidden;
    max-width: none;
    width: 100%;
  }

  .body.running {
    padding: clamp(4px, 0.8vh, 14px);
    gap: clamp(4px, 0.8vw, 12px);
    grid-template-columns: minmax(0, 1fr) clamp(160px, 18vw, 320px);
    grid-template-rows: minmax(0, 1fr) clamp(120px, 22vh, 280px);
    grid-template-areas:
      "guest guest"
      "bt control";
  }

  .body.running .card-body {
    padding: 0;
  }

  .body.running :global(.bt.embedded .current) {
    font-size: clamp(56px, 11vh, 120px);
    line-height: 1;
  }

  .body.running :global(.aid.embedded .screen-top) {
    display: none;
  }

  .body.running .control-btn.stop {
    height: 100%;
    font-size: clamp(44px, 9vh, 88px);
  }

  .card {
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
  }

  .card-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-1);
    background: #ffffff;
  }

  .card-title {
    color: var(--text-1);
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .card-meta {
    min-width: 0;
    color: var(--text-3);
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mode-actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
    min-width: 0;
  }

  .log-chip {
    min-width: 36px;
    height: 20px;
    padding: 0 7px;
    color: var(--text-2);
    background: #ffffff;
    border: 1px solid var(--border-2);
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0;
  }

  .card-body {
    padding: 8px 10px;
  }

  .guest-card {
    grid-area: guest;
  }

  .bt-card {
    grid-area: bt;
  }

  .mode-card {
    grid-area: mode;
  }

  .guest-card,
  .bt-card,
  .mode-card {
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .guest-body,
  .bt-body {
    flex: 1;
    min-height: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
  }

  .mode-body {
    flex: 1;
    min-height: 0;
    display: flex;
    align-items: center;
  }

  .mode-options {
    width: 100%;
    min-width: 0;
    height: 100%;
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: clamp(4px, 0.6vw, 10px);
  }

  .mode-option {
    min-width: 0;
    height: 100%;
    padding: 0 clamp(4px, 0.6vw, 12px);
    color: var(--text-1);
    background: #ffffff;
    border: 1px solid var(--border-2);
    border-radius: var(--radius);
    font-size: clamp(18px, 2.4vw, 30px);
    font-weight: 700;
    letter-spacing: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    transition: border-color 0.12s ease, background 0.12s ease, color 0.12s ease;
  }

  .mode-option.active {
    color: var(--text-0);
    background: rgba(37, 99, 235, 0.08);
    border-color: rgba(37, 99, 235, 0.32);
  }

  .mode-option:disabled {
    color: var(--text-2);
    opacity: 1;
  }

  .mode-option:disabled:not(.active) {
    background: var(--bg-2);
  }

  .control {
    grid-area: control;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px;
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
  }

  .control-btn {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-0);
    background: linear-gradient(180deg, rgba(74, 222, 128, 0.16), rgba(74, 222, 128, 0.08));
    border: 1px solid rgba(74, 222, 128, 0.28);
    border-radius: var(--radius-lg);
    font-size: clamp(30px, 4.4vw, 56px);
    font-weight: 700;
    letter-spacing: 0;
    transition: border-color 0.12s ease, background 0.12s ease;
  }

  .control-btn.stop {
    width: 100%;
    height: 100%;
    align-self: stretch;
    color: var(--err);
    background: linear-gradient(180deg, rgba(248, 113, 113, 0.14), rgba(248, 113, 113, 0.08));
    border-color: rgba(248, 113, 113, 0.34);
    border-radius: var(--radius);
    font-size: 18px;
  }

  .control-btn:hover {
    filter: brightness(0.98);
  }

  .control-btn:disabled {
    opacity: 0.72;
  }

  .error-backdrop {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: rgba(15, 17, 21, 0.34);
  }

  .error-dialog {
    width: min(860px, calc(100vw - 48px));
    max-height: min(640px, calc(100vh - 48px));
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: #ffffff;
    border: 1px solid var(--border-2);
    border-radius: var(--radius);
    box-shadow: var(--shadow-md);
  }

  .error-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 12px 14px;
    border-bottom: 1px solid var(--border-1);
  }

  .error-copy {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .error-title {
    color: var(--err);
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0;
  }

  .error-meta {
    color: var(--text-3);
    font-size: 11px;
  }

  .error-close {
    flex: 0 0 auto;
    height: 34px;
    padding: 0 12px;
    color: var(--text-1);
    background: var(--bg-1);
    border: 1px solid var(--border-2);
    border-radius: var(--radius);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0;
  }

  .error-log {
    margin: 0;
    padding: 14px;
    overflow: auto;
    color: var(--text-0);
    background: #ffffff;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
    font-size: 12px;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-word;
    user-select: text;
  }

  .mission.local-fixed-ui {
    overflow: hidden;
  }

  .mission.local-fixed-ui .body {
    padding: clamp(3px, 0.7vh, 10px) clamp(4px, 0.8vw, 12px);
    gap: clamp(3px, 0.7vw, 10px);
    grid-template-columns: minmax(0, 1fr) clamp(126px, 15vw, 240px);
    grid-template-rows: minmax(0, 1fr) clamp(84px, 18vh, 220px);
    width: 100%;
    height: 100%;
  }

  .mission.local-fixed-ui.running .body {
    transform: none;
    width: 100%;
    height: 100%;
  }

  .mission.local-fixed-ui .card-head {
    padding: 4px 7px;
  }

  .mission.local-fixed-ui .card-body {
    padding: 4px 6px;
  }

  .mission.local-fixed-ui .mode-actions {
    gap: 6px;
  }

  .mission.local-fixed-ui .log-chip,
  .mission.local-fixed-ui .card-meta,
  .mission.local-fixed-ui .error-meta {
    font-size: 10px;
  }

  .mission.local-fixed-ui .mode-options {
    height: clamp(32px, 6.2vh, 62px);
    gap: clamp(3px, 0.5vw, 8px);
  }

  .mission.local-fixed-ui .mode-option {
    padding: 0 clamp(3px, 0.5vw, 8px);
    font-size: clamp(9px, 1.25vw, 18px);
  }

  .mission.local-fixed-ui .control {
    padding: clamp(3px, 0.7vh, 8px);
  }

  .mission.local-fixed-ui .control-btn {
    font-size: clamp(17px, 2.8vw, 40px);
  }

  .mission.local-fixed-ui .control-btn.stop {
    font-size: 12px;
  }

  .mission.local-fixed-ui .error-backdrop {
    padding: 16px;
  }

  .mission.local-fixed-ui .error-dialog {
    max-height: min(520px, calc(100vh - 32px));
  }

  .mission.local-fixed-ui .error-head {
    padding: 10px 12px;
  }

  .mission.local-fixed-ui .error-log {
    padding: 10px 12px;
    font-size: 11px;
  }
</style>
