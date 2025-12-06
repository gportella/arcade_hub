<script>
    import { onMount } from "svelte";
    import ServiceCard from "./lib/components/ServiceCard.svelte";
    import { loadServices, randomHubTitle } from "./lib/services.js";

    const services = loadServices();
    let headline = randomHubTitle();
    let headlineTransform = "none";
    let statusMap = Object.fromEntries(
        services.map((service) => [
            service.id,
            { state: "loading", message: "Checking…" },
        ]),
    );

    function randomBetween(min, max) {
        return Math.random() * (max - min) + min;
    }

    function computeHeadlineTransform() {
        const rotate = randomBetween(-4.5, 4.5);
        const skewX = randomBetween(-3, 3);
        const skewY = randomBetween(-2.5, 2.5);
        const translateX = randomBetween(-6, 6);
        const translateY = randomBetween(-4, 4);
        return `translate(${translateX.toFixed(1)}px, ${translateY.toFixed(1)}px) rotate(${rotate.toFixed(1)}deg) skew(${skewX.toFixed(1)}deg, ${skewY.toFixed(1)}deg)`;
    }

    function setStatus(id, next) {
        statusMap = {
            ...statusMap,
            [id]: {
                state: next.state,
                message: next.message ?? null,
            },
        };
    }

    async function probeService(service) {
        if (!service.healthUrl) {
            setStatus(service.id, {
                state: "online",
                message:
                    "Health endpoint not configured; link is always enabled.",
            });
            return;
        }

        setStatus(service.id, { state: "loading", message: "Checking…" });

        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 4000);

        try {
            const response = await fetch(service.healthUrl, {
                method: "GET",
                headers: { Accept: "application/json" },
                signal: controller.signal,
            });

            if (response.ok) {
                setStatus(service.id, {
                    state: "online",
                    message: `Responded at ${new Date().toLocaleTimeString()}.`,
                });
            } else {
                setStatus(service.id, {
                    state: "offline",
                    message: `Health check returned ${response.status} ${response.statusText}.`,
                });
            }
        } catch (error) {
            const isAbort =
                error instanceof DOMException && error.name === "AbortError";
            const friendlyMessage = (() => {
                if (isAbort) {
                    return "Timed out waiting for a response.";
                }
                if (error instanceof TypeError) {
                    return "Network error – could not reach the health endpoint.";
                }
                if (error && typeof error === "object" && "message" in error) {
                    return (
                        /** @type {{ message?: string }} */ (error).message ||
                        "Health check failed."
                    );
                }
                return "Health check failed.";
            })();

            setStatus(service.id, {
                state: "offline",
                message: friendlyMessage,
            });
        } finally {
            clearTimeout(timer);
        }
    }

    function refreshService(id) {
        const service = services.find((item) => item.id === id);
        if (!service) {
            return;
        }
        probeService(service);
    }

    onMount(() => {
        headlineTransform = computeHeadlineTransform();
        services.forEach(probeService);
    });
</script>

<main class="page">
    <header class="hero">
        <div class="hero__badge">Arcade Access</div>
        <h1 style={`transform: ${headlineTransform}`}>{headline}</h1>
    </header>

    <section class="grid" aria-live="polite">
        {#each services as service}
            <ServiceCard
                {service}
                status={statusMap[service.id] ?? {
                    state: "loading",
                    message: "Checking…",
                }}
                onRefresh={refreshService}
            />
        {/each}
    </section>
</main>

<style>
    .page {
        min-height: 100vh;
        max-width: 960px;
        margin: 0 auto;
        padding: clamp(2.5rem, 3vw + 2rem, 4.5rem)
            clamp(1.75rem, 2.5vw + 1.2rem, 3.5rem) 3.5rem;
        display: flex;
        flex-direction: column;
        gap: 2.5rem;
        position: relative;
    }

    .page::before {
        content: "";
        position: absolute;
        inset: 1.8rem;
        border-radius: 24px;
        border: 1px solid rgba(118, 136, 255, 0.25);
        pointer-events: none;
        mask: linear-gradient(#000, transparent);
    }

    .hero {
        display: flex;
        flex-direction: column;
        gap: 0.9rem;
        text-align: center;
    }

    h1 {
        margin: 0;
        font-size: clamp(2.5rem, 4vw + 1.5rem, 3.5rem);
        color: #f5f8ff;
        display: inline-block;
        transform-origin: center;
        will-change: transform;
        text-shadow:
            0 8px 25px rgba(95, 123, 255, 0.5),
            0 0 15px rgba(26, 223, 252, 0.55);
    }

    .hero__badge {
        align-self: center;
        padding: 0.2rem 1.3rem;
        border-radius: 999px;
        border: 1px solid rgba(95, 123, 255, 0.4);
        background: rgba(12, 18, 34, 0.65);
        color: rgba(195, 208, 255, 0.8);
        text-transform: uppercase;
        letter-spacing: 0.4em;
        font-size: 0.65rem;
        font-weight: 600;
    }

    .grid {
        display: grid;
        gap: 2rem;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        position: relative;
    }

    @media (max-width: 600px) {
        .page {
            padding-inline: 1.25rem;
        }
    }
</style>
