<script>
  import { config, startNextInstruction } from '$lib/ros.js';
  const apiUrl = config.apiUrl;
  export let running = false;
  export let text = 'Mission running';
  export let embedded = false;
  export let btStatePayload = null;
  export let btMessagePayload = null;

  let nextInstructionBusy = false;
  let nextInstructionError = '';

  $: active = btMessagePayload?.active ?? false;
  $: mode = active ? (btMessagePayload?.mode ?? 0) : 0;
  $: messageText = active ? String(btMessagePayload?.message ?? '').trim() : '';
  $: imagePath = active ? String(btMessagePayload?.image_path ?? '').trim() : '';
  $: isNextInstructionMode = mode === 2;
  $: nextInstructionLabel = messageText || 'Start Next Instruction';
  $: isListening = String(btStatePayload?.state ?? '').trim().toLowerCase() === 'listening';

  $: taskLines = mode === 1 && messageText
    ? messageText.split('\n').map(l => l.trim()).filter(Boolean)
    : [];

  $: showLogo = !isListening && !messageText && !imagePath && !isNextInstructionMode;

  async function handleStartNextInstruction() {
    if (nextInstructionBusy) return;

    nextInstructionBusy = true;
    nextInstructionError = '';

    try {
      await startNextInstruction();
    } catch (error) {
      nextInstructionError = error?.message ?? 'Service call failed';
    } finally {
      nextInstructionBusy = false;
    }
  }
</script>

<section class="aid" class:embedded>
  <div class="screen">
    <div class="screen-top">
      <div class="eyebrow">Guest Screen</div>
      <div class="status mono" class:active={running}>{running ? 'ON' : 'READY'}</div>
    </div>

    <div class="content">
      {#if isNextInstructionMode}
        <div class="next-panel">
          {#if imagePath}
            <img class="face" src="{apiUrl}/bt/message/image?t={Date.now()}" alt="face" />
          {/if}
          <button
            type="button"
            class="next-button"
            disabled={nextInstructionBusy}
            on:click={handleStartNextInstruction}
          >
            {nextInstructionBusy ? 'Sending' : nextInstructionLabel}
          </button>
          {#if nextInstructionError}
            <div class="next-error">{nextInstructionError}</div>
          {/if}
        </div>

      {:else if isListening}
        <img class="listen" src="/listen.png" alt="Listening" />

      {:else if showLogo}
        <img class="logo" src="/logo.png" alt="INHA United" />

      {:else if mode === 1}
        <!-- GPSR task list mode -->
        <div class="task-panel">
          {#if imagePath}
            <img class="face" src="{apiUrl}/bt/message/image?t={Date.now()}" alt="face" />
          {/if}
          <div class="task-list">
            {#each taskLines as line, i}
              <div class="task-item">
                <span class="task-num">{i + 1}</span>
                <span class="task-text">{line}</span>
              </div>
            {/each}
          </div>
        </div>

      {:else}
        <!-- Text mode (mode 0) -->
        <div class="text-panel">
          {#if imagePath}
            <img class="face" src="{apiUrl}/bt/message/image?t={Date.now()}" alt="face" />
          {/if}
          <div class="message">{messageText}</div>
        </div>
      {/if}
    </div>
  </div>
</section>

<style>
  .aid {
    flex: 1;
    min-height: 0;
  }

  .aid.embedded {
    height: 100%;
  }

  .screen {
    height: 100%;
    display: flex;
    flex-direction: column;
    padding: 24px 28px;
    background:
      radial-gradient(circle at top left, rgba(74, 222, 128, 0.08), transparent 34%),
      linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent 42%),
      var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-lg);
  }

  .aid.embedded .screen {
    border: none;
    border-radius: 0;
  }

  .screen-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .eyebrow {
    color: var(--text-2);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .status {
    color: var(--text-2);
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.08em;
  }

  .status.active {
    color: var(--ok);
  }

  .content {
    flex: 1;
    display: grid;
    place-items: center;
    min-height: 0;
  }

  /* ── Text mode ── */
  .text-panel {
  width: 100%;
  height: 100%;
  overflow: hidden;
  } 

  .message {
  max-width: 90%;
  max-height: 100%;
  font-size: clamp(32px, 7vmin, 120px);
  line-height: 1.08;
  text-align: center;

  word-break: keep-all;
  overflow-wrap: anywhere;
  overflow: hidden;
  }

  .next-panel {
    width: min(86%, 760px);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 18px;
  }

  .next-button {
    width: 100%;
    min-height: clamp(96px, 18vh, 180px);
    padding: 20px 28px;
    color: #ffffff;
    background: var(--ok);
    border: 1px solid rgba(255, 255, 255, 0.24);
    border-radius: var(--radius);
    font-size: clamp(30px, 6vmin, 72px);
    font-weight: 800;
    line-height: 1.08;
    text-align: center;
    overflow-wrap: anywhere;
    box-shadow: 0 18px 46px rgba(21, 128, 61, 0.24);
  }

  .next-button:disabled {
    opacity: 0.68;
  }

  .next-error {
    max-width: 100%;
    color: var(--err);
    font-size: clamp(14px, 2vmin, 20px);
    font-weight: 700;
    text-align: center;
    overflow-wrap: anywhere;
  }

  /* ── GPSR task list mode ── */
  .task-panel {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    max-width: 640px;
  }

  .task-list {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .task-item {
    display: flex;
    align-items: baseline;
    gap: 14px;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.6);
    border: 1px solid var(--border-1);
    border-radius: var(--radius);
  }

  .task-num {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    display: grid;
    place-items: center;
    color: #ffffff;
    background: var(--ok);
    border-radius: 50%;
    font-size: 16px;
    font-weight: 700;
  }

  .task-text {
    color: var(--text-0);
    font-size: clamp(20px, 3vw, 36px);
    font-weight: 600;
    line-height: 1.3;
  }

  /* ── Face image (shared) ── */
  .face {
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
    object-fit: contain;
    border-radius: 0;
    border: none;
  }

  .listen {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .logo {
    max-width: clamp(200px, 65%, 520px);
    max-height: clamp(200px, 80%, 520px);
    width: auto;
    height: auto;
    object-fit: contain;
    opacity: 0.85;
  }

  @media (max-width: 900px) {
    .screen {
      padding: 18px 18px 20px;
    }

    .message {
      font-size: clamp(52px, 14vw, 96px);
    }

    .task-text {
      font-size: clamp(16px, 4vw, 28px);
    }
  }
</style>