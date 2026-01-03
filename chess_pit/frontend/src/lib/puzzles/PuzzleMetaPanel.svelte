<script>
  export let title = "";
  export let difficultyLabel = "";
  export let sideAnnouncement = "";
  export let statusTone = "muted";
  export let statusText = "";
  export let celebrating = false;
</script>

<section class="puzzle-meta" aria-live="polite">
  <div class="puzzle-meta__title" data-celebrating={celebrating}>
    <span class="puzzle-meta__glyph" aria-hidden="true">♞</span>
    <span class="puzzle-meta__name">{title}</span>
    <span class="puzzle-meta__glyph" aria-hidden="true">♘</span>
  </div>
  <div class="puzzle-meta__details">
    <span class="chip chip--difficulty">{difficultyLabel}</span>
    {#if sideAnnouncement}
      <span class="chip chip--side">{sideAnnouncement}</span>
    {/if}
    {#if statusText}
      <span class={`chip chip--${statusTone}`}>{statusText}</span>
    {/if}
  </div>
</section>

<style>
  .puzzle-meta {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    padding: 0.9rem 1.2rem;
    border-radius: 16px;
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(148, 163, 184, 0.22);
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.3);
    font-family: "IBM Plex Mono", "Fira Code", "Menlo", monospace;
  }

  .puzzle-meta__title {
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 0.75rem;
    font-size: 1.25rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #e2e8f0;
  }

  .puzzle-meta__title[data-celebrating="true"] {
    color: #facc15;
    text-shadow: 0 0 14px rgba(250, 204, 21, 0.4);
  }

  .puzzle-meta__glyph {
    font-size: 1.2rem;
    opacity: 0.8;
  }

  .puzzle-meta__name {
    font-size: 1.1em;
    white-space: nowrap;
  }

  .puzzle-meta__details {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    font-size: 0.8rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border: 1px solid transparent;
  }

  .chip--difficulty {
    background: rgba(59, 130, 246, 0.18);
    border-color: rgba(59, 130, 246, 0.35);
    color: #bfdbfe;
  }

  .chip--side {
    background: rgba(148, 163, 184, 0.18);
    border-color: rgba(148, 163, 184, 0.28);
    color: rgba(226, 232, 240, 0.9);
  }

  .chip--info {
    background: rgba(20, 184, 166, 0.18);
    border-color: rgba(16, 185, 129, 0.32);
    color: #99f6e4;
  }

  .chip--error {
    background: rgba(248, 113, 113, 0.16);
    border-color: rgba(239, 68, 68, 0.32);
    color: #fecaca;
  }

  .chip--hint {
    background: rgba(234, 179, 8, 0.16);
    border-color: rgba(234, 179, 8, 0.28);
    color: #fef9c3;
  }

  .chip--muted {
    background: rgba(100, 116, 139, 0.18);
    border-color: rgba(100, 116, 139, 0.28);
    color: rgba(226, 232, 240, 0.75);
  }

  @media (max-width: 680px) {
    .puzzle-meta {
      gap: 0.35rem;
      padding: 0.7rem 0.9rem;
    }

    .puzzle-meta__details {
      flex-wrap: wrap;
      gap: 0.35rem;
    }
  }
</style>
