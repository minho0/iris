<script>
  import { goto } from '$lib/router.js';

  export let title = '';
  export let to = 'landing';
</script>

<div class="bar">
  <button class="back" on:click={() => goto(to)} aria-label="back">
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M15 18l-6-6 6-6"></path>
    </svg>
  </button>
  <div class="title">{title}</div>
  <div class="right">
    <slot />
  </div>
</div>

<style>
  .bar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 24px;
    border-bottom: 1px solid var(--border-1);
  }

  .back {
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    color: var(--text-1);
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius);
  }

  .back:hover {
    color: var(--text-0);
    border-color: var(--border-2);
  }

  .title {
    flex: 1;
    font-size: 17px;
    font-weight: 500;
    color: var(--text-0);
  }

  .right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  @media (max-width: 760px) {
    .bar {
      flex-wrap: wrap;
      gap: 10px;
      padding: 12px 14px;
    }

    .title {
      min-width: 0;
      font-size: 16px;
    }

    .right {
      width: 100%;
      justify-content: flex-end;
      flex-wrap: wrap;
    }
  }
</style>
