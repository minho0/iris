<script>
  import { onMount } from 'svelte';
  import { topic, videoStreamUrl } from '$lib/ros.js';

  export let active = false;

  const { value: robotState } = topic('/robot_state', 'std_msgs/msg/String');
  const { value: speech } = topic('/speech/asr_result', 'std_msgs/msg/String');

  const fallbackLines = [
    '로봇이 주변을 확인하고 있습니다.',
    '손님을 인식하면 이 화면에 크게 보여줍니다.',
    '음성이 들어오면 현재 문장만 표시합니다.'
  ];

  let fallbackIdx = 0;
  let imageReady = false;
  let imageFailed = false;

  $: streamUrl = videoStreamUrl('/person_detector/waving_image', 80);

  onMount(() => {
    const timer = setInterval(() => {
      fallbackIdx = (fallbackIdx + 1) % fallbackLines.length;
    }, 5200);
    return () => clearInterval(timer);
  });

  function parseJson(raw) {
    try {
      return JSON.parse(raw ?? '{}');
    } catch {
      return {};
    }
  }

  function textFrom(raw) {
    if (!raw) return '';

    const parsed = parseJson(raw);
    if (parsed.text) return parsed.text;
    if (parsed.message) return parsed.message;
    if (parsed.transcript) return parsed.transcript;

    return raw;
  }

  $: state = parseJson($robotState?.data);
  $: heard = textFrom($speech?.data);
  $: headline = state.task ?? (active ? '안내를 시작했습니다' : '로봇이 준비 중입니다');
  $: currentLine = heard || state.message || state.phase || fallbackLines[fallbackIdx];
  $: subLine = state.phase && state.phase !== currentLine ? state.phase : '사진 또는 음성이 들어오면 이 화면이 바로 바뀝니다.';
  $: showImage = active && imageReady && !imageFailed;

  function handleLoad() {
    imageReady = true;
    imageFailed = false;
  }

  function handleError() {
    imageFailed = true;
    imageReady = false;
  }
</script>

<section class="stage" class:image={showImage}>
  <div class="visual">
    <img
      src={streamUrl}
      alt="로봇 카메라 화면"
      class:visible={showImage}
      on:load={handleLoad}
      on:error={handleError}
    />

    {#if !showImage}
      <div class="empty">
        <div class="empty-mark">
          <svg viewBox="0 0 48 48" width="46" height="46" fill="none">
            <path d="M10 30c0-8.2 6-14.6 14-14.6S38 21.8 38 30" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"></path>
            <path d="M16 30h16" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"></path>
            <circle cx="18" cy="13" r="3.2" fill="currentColor"></circle>
            <circle cx="30" cy="13" r="3.2" fill="currentColor"></circle>
          </svg>
        </div>
        <div class="empty-title">{headline}</div>
        <div class="empty-text">{currentLine}</div>
      </div>
    {/if}
  </div>

  {#if showImage}
    <div class="caption">
      <div class="caption-label">{heard ? '방금 들은 말' : '현재 상태'}</div>
      <div class="caption-text">{currentLine}</div>
      <div class="caption-sub">{subLine}</div>
    </div>
  {/if}
</section>

<style>
  .stage {
    position: relative;
    height: 100%;
    min-height: 0;
    overflow: hidden;
    background: #050607;
    border: 1px solid var(--border-1);
    border-radius: var(--radius-lg);
  }

  .visual {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background:
      linear-gradient(180deg, rgba(56, 189, 248, 0.08), transparent 36%),
      linear-gradient(145deg, #0b0d10, #050607 58%, #11140f);
  }

  img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
    opacity: 0;
    transition: opacity 180ms ease;
  }

  img.visible {
    opacity: 1;
  }

  .empty {
    width: min(860px, 76%);
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    color: var(--text-0);
  }

  .empty-mark {
    width: 82px;
    height: 82px;
    display: grid;
    place-items: center;
    margin-bottom: 30px;
    color: var(--text-1);
    background: rgba(247, 245, 239, 0.06);
    border: 1px solid var(--border-1);
    border-radius: 50%;
  }

  .empty-title {
    font-size: 52px;
    font-weight: 750;
    line-height: 1.15;
  }

  .empty-text {
    margin-top: 18px;
    color: var(--text-1);
    font-size: 31px;
    line-height: 1.35;
    word-break: keep-all;
  }

  .caption {
    position: absolute;
    left: 34px;
    right: 34px;
    bottom: 30px;
    padding: 22px 26px 24px;
    background: rgba(7, 8, 10, 0.82);
    border: 1px solid rgba(247, 245, 239, 0.16);
    border-radius: var(--radius-lg);
    backdrop-filter: blur(14px);
  }

  .caption-label {
    margin-bottom: 8px;
    color: var(--info);
    font-size: 16px;
    font-weight: 700;
  }

  .caption-text {
    color: var(--text-0);
    font-size: 36px;
    font-weight: 750;
    line-height: 1.25;
    word-break: keep-all;
  }

  .caption-sub {
    margin-top: 10px;
    color: var(--text-2);
    font-size: 18px;
    line-height: 1.35;
    word-break: keep-all;
  }

  .stage.image .caption {
    background: linear-gradient(180deg, rgba(7, 8, 10, 0.68), rgba(7, 8, 10, 0.9));
  }
</style>
