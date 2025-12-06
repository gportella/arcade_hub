<script>
    export let service;
    export let status;
    export let onRefresh;

    $: indicator =
        status.state === "online"
            ? "Online"
            : status.state === "offline"
              ? "Offline"
              : "Checking";
    $: badgeClass = `status status--${status.state}`;

    function handleRefresh(event) {
        event.preventDefault();
        if (typeof onRefresh === "function") {
            onRefresh(service.id);
        }
    }
</script>

<article class="card">
    <header class="card__header">
        <h2>{service.name}</h2>
        <span class={badgeClass}>{indicator}</span>
    </header>
    {#if service.tagline}
        <div class="card__tagline">{service.tagline}</div>
    {/if}
    <p class="card__description">{service.description}</p>
    <footer class="card__footer">
        <a
            class="card__link"
            href={service.url}
            target="_blank"
            rel="noopener noreferrer"
        >
            Open App
        </a>
        {#if service.healthUrl}
            <button type="button" on:click={handleRefresh}>Recheck</button>
        {/if}
    </footer>
    {#if status.message}
        <div class="card__hint">{status.message}</div>
    {/if}
</article>

<style>
    .card {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 1rem;
        padding: 1.9rem;
        border-radius: 1.35rem;
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        box-shadow: var(--glow);
        overflow: hidden;
    }

    .card > * {
        position: relative;
        z-index: 1;
    }

    .card__header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    }

    h2 {
        margin: 0;
        font-size: clamp(1.35rem, 1.5vw + 1rem, 1.75rem);
        color: #f7f9ff;
        letter-spacing: 0.03em;
    }

    .card__description {
        margin: 0;
        color: var(--muted);
        font-size: 0.95rem;
    }

    .card__tagline {
        margin: 0;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.25em;
        color: rgba(168, 184, 255, 0.58);
    }

    .card__footer {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
    }

    .card__link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.55rem 1.25rem;
        border-radius: 999px;
        background: linear-gradient(
            120deg,
            rgba(95, 123, 255, 0.95),
            rgba(255, 75, 194, 0.9)
        );
        color: #fff;
        font-weight: 600;
        text-decoration: none;
        transition:
            transform 0.15s ease,
            box-shadow 0.15s ease;
    }

    .card__link:hover {
        transform: translateY(-1px);
        box-shadow: 0 18px 35px rgba(95, 123, 255, 0.35);
    }

    button {
        border: 1px solid rgba(95, 123, 255, 0.35);
        background: rgba(13, 19, 34, 0.6);
        border-radius: 999px;
        padding: 0.55rem 1.1rem;
        font-weight: 600;
        color: rgba(231, 238, 255, 0.85);
        cursor: pointer;
        transition:
            background 0.15s ease,
            border 0.15s ease;
    }

    button:hover {
        background: rgba(95, 123, 255, 0.25);
        border-color: rgba(95, 123, 255, 0.6);
    }

    .status {
        padding: 0.3rem 0.85rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        backdrop-filter: blur(8px);
    }

    .status--online {
        background: rgba(26, 223, 252, 0.2);
        color: #69faff;
    }

    .status--offline {
        background: rgba(255, 75, 194, 0.18);
        color: #ff73d0;
    }

    .status--loading {
        background: rgba(95, 123, 255, 0.16);
        color: rgba(190, 202, 255, 0.85);
    }

    .card__hint {
        font-size: 0.8rem;
        color: rgba(195, 205, 245, 0.65);
    }
</style>
