<script>
  import { videoStreamUrl, topic } from '$lib/ros.js';

  export let topicName;
  export let label;
  export let accent = 'var(--ok)';
  export let metadataTopic = null; // 선택: 감지 메타데이터 토픽 (Hz 측정용)

  $: url = videoStreamUrl(topicName);

  // Hz 계산용으로 실제 토픽 구독 (이미지 말고 메타데이터 토픽)
  const hzSource = metadataTopic
    ? topic(metadataTopic, 'std_msgs/msg/String')
    : { hz: { subscribe: (fn) => (fn(0), () => {}) } };
  const { hz } = hzSource;

  // 스트림이 끊어지면 재연결 시도
  let imgEl;
  let connected = true;

  function handleError() {
    connected = false;
    setTimeout(() => {
      if (imgEl) {
        imgEl.src = `${url}&_=${Date.now()}`;
        connected = true;
      }
    }, 1500);
  }
</script>

<div class="stream">
  <div class="head">
    <div class="label-row">
      <span class="mono topic">{topicName}</span>
      <span class="label">{label}</span>
    </div>
    <div class="meta mono">
      <span class="dot" style="background: {connected ? accent : 'var(--text-3)'}; animation: {connected ? 'pulse-dot 2s infinite' : 'none'}" />
      <span>{$hz} Hz</span>
    </div>
  </div>

  <div class="frame">
    <img bind:this={imgEl} src={url} alt={label} on:error={handleError} />
    {#if !connected}
      <div class="overlay mono">RECONNECTING...</div>
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

  .meta .dot {
    position: relative;
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .frame {
    flex: 1;
    position: relative;
    background: var(--bg-0);
    border-radius: var(--radius-md);
    overflow: hidden;
    min-height: 0;
  }

  .frame img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
  }

  .overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-0);
    color: var(--warn);
    font-size: 11px;
    letter-spacing: 0.15em;
  }
</style>
