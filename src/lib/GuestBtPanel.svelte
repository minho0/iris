<script>
  import { onMount } from 'svelte';

  export let active = false;

  const steps = [
    '대기',
    '손님 찾기',
    '다가가기',
    '인사',
    '듣기',
    '안내',
    '복귀'
  ];

  let idx = 0;

  onMount(() => {
    const timer = setInterval(() => {
      if (active) idx = (idx + 1) % steps.length;
    }, 5200);
    return () => clearInterval(timer);
  });

  $: current = active ? steps[idx] : '대기';
  $: next = active ? steps[(idx + 1) % steps.length] : '시작 전';
</script>

<section class="bt">
  <div class="head">
    <span class="label">진행 단계</span>
    <span class="state" class:active>{active ? '진행 중' : '대기'}</span>
  </div>

  <div class="current">{current}</div>

  <div class="track" aria-label="BT 진행 상태">
    {#each steps as step, i}
      <div class="node" class:active={active && i === idx} class:done={active && i < idx} title={step}></div>
    {/each}
  </div>

  <div class="next">
    <span>다음</span>
    <strong>{next}</strong>
  </div>
</section>

<style>
  .bt {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 22px;
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-lg);
  }

  .head,
  .next {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .label,
  .next span {
    color: var(--text-2);
    font-size: 14px;
  }

  .state {
    padding: 5px 10px;
    color: var(--text-2);
    background: var(--bg-2);
    border-radius: var(--radius-sm);
    font-size: 13px;
  }

  .state.active {
    color: var(--ok);
    background: var(--ok-soft);
  }

  .current {
    color: var(--text-0);
    font-size: 32px;
    font-weight: 800;
    line-height: 1.15;
    word-break: keep-all;
  }

  .track {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 8px;
  }

  .node {
    height: 7px;
    background: var(--bg-3);
    border-radius: 99px;
  }

  .node.done {
    background: rgba(34, 197, 94, 0.42);
  }

  .node.active {
    background: var(--ok);
    box-shadow: 0 0 16px rgba(34, 197, 94, 0.55);
  }

  .next strong {
    color: var(--text-1);
    font-size: 15px;
    font-weight: 700;
  }
</style>
