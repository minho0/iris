<script>
  import '../app.css';
  import Header from '$lib/Header.svelte';
  import Landing from '$lib/landing/Landing.svelte';
  import Launcher from '$lib/launcher/Launcher.svelte';
  import Mission from '$lib/mission/Mission.svelte';
  import { route } from '$lib/router.js';
  import { localFixedUi } from '$lib/uiMode.js';

  $: if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('responsive-ui', !$localFixedUi);
    document.body.classList.toggle('responsive-ui', !$localFixedUi);
  }
</script>

<div class="root" class:responsive-ui={!$localFixedUi} class:local-fixed-ui={$localFixedUi}>
  <Header />

  <main class="view">
    {#if $route === 'landing'}
      <Landing />
    {:else if $route === 'launcher'}
      <Launcher />
    {:else if $route === 'mission'}
      <Mission />
    {/if}
  </main>
</div>

<style>
  .root {
    width: 100vw;
    min-height: 100vh;
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
    background: var(--bg-0);
    overflow: hidden;
  }

  .view {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .root.responsive-ui {
    overflow-x: hidden;
    overflow-y: auto;
  }
</style>
