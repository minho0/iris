<script>
  import EntryCard from './EntryCard.svelte';
  import { goto } from '$lib/router.js';
  import { localFixedUi } from '$lib/uiMode.js';
</script>

<section class="landing" class:local-fixed-ui={$localFixedUi}>
  <header class="hero">
    <img class="hero-logo" src="/logo.png" alt="INHA United" />
    <h1 class="hero-title" aria-label="IRIS">
      <span class="hero-title-text">IRIS</span>
    </h1>
    <span class="hero-divider" aria-hidden="true"></span>
    <p class="hero-tag">Inha Robot Interface System</p>
  </header>

  <div class="grid">
    <EntryCard
      title="Launcher"
      subtitle="Check nodes, sensors, and topics before starting subsystems."
      onEnter={() => goto('launcher')}
    />
    <EntryCard
      title="Mission"
      subtitle="Run the Behavior Tree and open the guest-facing screen."
      onEnter={() => goto('mission')}
    />
  </div>
</section>

<style>
  .landing {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: clamp(12px, 3vh, 32px);
    padding: clamp(16px, 4vh, 40px) clamp(20px, 4vw, 48px);
    min-height: 0;
  }

  .hero {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
  }

  .hero::before {
    content: '';
    position: absolute;
    inset: -40px -80px;
    background:
      radial-gradient(ellipse at 50% 60%, rgba(56, 189, 248, 0.14) 0%, transparent 60%),
      radial-gradient(ellipse at 30% 70%, rgba(125, 211, 252, 0.10) 0%, transparent 55%),
      radial-gradient(ellipse at 70% 70%, rgba(59, 130, 246, 0.08) 0%, transparent 55%);
    filter: blur(8px);
    pointer-events: none;
    z-index: 0;
  }

  .hero > * {
    position: relative;
    z-index: 1;
  }

  .hero-logo {
    width: clamp(80px, 12vh, 160px);
    height: auto;
    object-fit: contain;
  }

  .hero-title {
    margin: 6px 0 2px;
    font-size: clamp(36px, 8vw, 132px);
    font-weight: 800;
    letter-spacing: 0.14em;
    line-height: 1;
  }

  .hero-title-text {
    background: linear-gradient(
      135deg,
      #7dd3fc 0%,
      #38bdf8 40%,
      #0ea5e9 70%,
      #2563eb 100%
    );
    background-size: 200% 200%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: transparent;
    animation: hero-shimmer 8s ease-in-out infinite;
    text-shadow: 0 1px 0 rgba(56, 189, 248, 0.08);
  }

  @keyframes hero-shimmer {
    0%, 100% { background-position: 0% 50%; }
    50%      { background-position: 100% 50%; }
  }

  .hero-divider {
    width: 56px;
    height: 2px;
    border-radius: 999px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(56, 189, 248, 0.65) 50%,
      transparent 100%
    );
  }

  .hero-tag {
    margin: 0;
    color: var(--text-2);
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.32em;
    text-transform: uppercase;
  }

  .grid {
    width: 100%;
    max-width: 1400px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }

  .landing.local-fixed-ui {
    gap: 16px;
    padding: 18px 28px 20px;
  }

  .landing.local-fixed-ui .hero {
    gap: 4px;
    padding: 0;
  }

  .landing.local-fixed-ui .hero-logo {
    width: 104px;
  }

  .landing.local-fixed-ui .hero-title {
    margin: 0;
    font-size: clamp(46px, 6.4vw, 82px);
    letter-spacing: 0.12em;
  }

  .landing.local-fixed-ui .hero-divider {
    width: 36px;
  }

  .landing.local-fixed-ui .hero-tag {
    font-size: 10px;
    letter-spacing: 0.2em;
  }

  .landing.local-fixed-ui .grid {
    max-width: 1100px;
    gap: 14px;
  }

  .landing.local-fixed-ui :global(.card) {
    min-height: 240px;
    padding: 26px 24px;
  }

  .landing.local-fixed-ui :global(.title) {
    font-size: 26px;
  }

  .landing.local-fixed-ui :global(.subtitle) {
    margin-top: 8px;
    font-size: 13px;
  }

  .landing.local-fixed-ui :global(.enter) {
    font-size: 13px;
  }

  @media (max-width: 600px) {
    .landing {
      justify-content: flex-start;
    }

    .grid {
      grid-template-columns: 1fr;
      gap: 12px;
    }
  }
</style>
