<script>
  import { onMount } from 'svelte';

  // Dummy BT step sequence — 나중에 실제 BT 노드와 연동
  const steps = [
    'Wait',
    'Find person',
    'Approach',
    'Greet',
    'Listen',
    'Guide',
    'Return'
  ];

  let idx = 0;
  let timer;

  onMount(() => {
    timer = setInterval(() => {
      idx = (idx + 1) % steps.length;
    }, 6000);
    return () => clearInterval(timer);
  });
</script>

<div class="bt">
  <div class="track">
    {#each steps as step, i}
      <div class="node" class:active={i === idx} class:done={i < idx} />
      {#if i < steps.length - 1}
        <div class="link" class:done={i < idx} />
      {/if}
    {/each}
  </div>

  <div class="label">
    <span class="mono step">STEP {String(idx + 1).padStart(2, '0')} / {String(steps.length).padStart(2, '0')}</span>
    <span class="name">{steps[idx]}</span>
  </div>
</div>

<style>
  .bt {
    display: flex;
    align-items: center;
    gap: 32px;
    padding: 18px 32px;
    background: var(--bg-1);
    border: 0.5px solid var(--border-1);
    border-radius: var(--radius-lg);
  }

  .track {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 0;
  }

  .node {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--border-2);
    flex-shrink: 0;
    transition: all 0.4s ease;
  }

  .node.done {
    background: var(--ok);
    opacity: 0.45;
  }

  .node.active {
    background: var(--ok);
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.15), 0 0 16px var(--ok);
    transform: scale(1.4);
  }

  .link {
    flex: 1;
    height: 1px;
    background: var(--border-2);
    transition: background 0.4s ease;
  }

  .link.done {
    background: var(--ok);
    opacity: 0.45;
  }

  .label {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
    min-width: 200px;
  }

  .step {
    font-size: 10px;
    letter-spacing: 0.15em;
    color: var(--text-3);
  }

  .name {
    font-size: 18px;
    font-weight: 500;
    color: var(--text-0);
    letter-spacing: -0.01em;
  }
</style>
