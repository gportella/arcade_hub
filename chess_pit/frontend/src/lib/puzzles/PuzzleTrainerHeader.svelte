<script>
  import { createEventDispatcher } from "svelte";
  import { t } from "../i18n";

  /** @type {{ username?: string } | null} */
  export let user = null;

  const dispatch = createEventDispatcher();

  const handleBack = () => dispatch("back");
  const handleLogout = () => dispatch("logout");

  $: titleLabel = $t("puzzles.header.title");
  $: taglineLabel = $t("puzzles.header.tagline");
  $: backLabel = $t("puzzles.header.back");
  $: logoutLabel = $t("puzzles.header.logout");
  $: playerFallback = $t("puzzles.header.player");
  $: displayName = user?.username ?? playerFallback;
</script>

<header class="trainer-header">
  <div class="trainer-header__left">
    <button type="button" class="trainer-header__back" on:click={handleBack}>
      {backLabel}
    </button>
    <h1>{titleLabel}</h1>
    <p class="trainer-header__subtitle">{taglineLabel}</p>
  </div>
  <div class="trainer-header__actions">
    {#if user}
      <div class="trainer-header__user">
        <span class="trainer-header__avatar" aria-hidden="true">♟</span>
        <span>{displayName}</span>
      </div>
    {/if}
    <button type="button" class="trainer-header__logout" on:click={handleLogout}>
      {logoutLabel}
    </button>
  </div>
</header>

<style>
  .trainer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }

  .trainer-header__left {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  h1 {
    margin: 0;
    font-size: 1.6rem;
    letter-spacing: 0.06em;
    color: #f8fafc;
  }

  .trainer-header__subtitle {
    margin: 0;
    color: rgba(148, 163, 184, 0.75);
    font-size: 0.9rem;
    letter-spacing: 0.04em;
  }

  .trainer-header__actions {
    display: flex;
    gap: 0.65rem;
    align-items: center;
  }

  .trainer-header__user {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(15, 23, 42, 0.45);
    border: 1px solid rgba(148, 163, 184, 0.25);
    padding: 0.4rem 0.8rem;
    border-radius: 999px;
    font-size: 0.9rem;
    color: #e2e8f0;
  }

  .trainer-header__avatar {
    font-size: 1.1rem;
  }

  .trainer-header__back,
  .trainer-header__logout {
    border: 1px solid rgba(148, 163, 184, 0.3);
    background: rgba(15, 23, 42, 0.65);
    color: #e2e8f0;
    padding: 0.55rem 0.9rem;
    border-radius: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
  }

  .trainer-header__back:hover,
  .trainer-header__logout:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 22px rgba(15, 23, 42, 0.35);
  }

  .trainer-header__back {
    align-self: flex-start;
  }

  @media (max-width: 768px) {
    .trainer-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.75rem;
    }

    .trainer-header__actions {
      width: 100%;
      justify-content: space-between;
    }
  }
</style>
