<script>
    import { onMount, onDestroy } from "svelte";
    import { get } from "svelte/store";
    import { Chess } from "chess.js";
    import ChessBoard from "../ChessBoard.svelte";
    import { createMiniEngine } from "../engine/miniEngine.js";
    import {
        detectInitialLocale,
        locale,
        setLocale,
        supportedLocales,
        t,
    } from "../i18n";

    export let showcaseFen = "";
    export let onPlay = (_credentials) => {};
    export let onAdminLogin = (_credentials) => {};
    export let error = "";
    export let isLoading = false;

    let username = "";
    let password = "";

    const localeLabels = {
        en: "locale.english",
        ca: "locale.catalan",
    };
    const languageOptions = supportedLocales
        .map((code) => ({
            code,
            labelKey: localeLabels[code] ?? null,
        }))
        .filter((option) => option.labelKey);
    const detectedLocale = detectInitialLocale();
    let gameStatusKey = "";
    let gameStatusParams = {};
    let isGameOver = false;

    $: translatedLanguageOptions = languageOptions.map((option) => ({
        ...option,
        label: $t(option.labelKey),
    }));

    $: localeNote =
        $locale === detectedLocale
            ? $t("notice.language.detected")
            : $t("notice.language.manual");

    const loginGame = new Chess();
    let miniEngine = null;
    let boardPosition = showcaseFen;
    let isThinking = false;
    let previousShowcase = null;
    let isActive = true;

    function handleLocaleSelect(code) {
        if (!code) {
            return;
        }
        const current = get(locale);
        if (code === current) {
            return;
        }
        setLocale(code);
    }

    function describeSide(color) {
        const translator = get(t);
        return color === "w"
            ? translator("color.white")
            : translator("color.black");
    }

    function setGameStatus(key = "", params = {}) {
        gameStatusKey = key;
        gameStatusParams = params;
    }

    function evaluateGameOutcome() {
        if (loginGame.isCheckmate()) {
            const winner =
                loginGame.turn() === "w"
                    ? describeSide("b")
                    : describeSide("w");
            setGameStatus("landing.status.checkmate", { winner });
            isGameOver = true;
            return;
        }

        if (loginGame.isStalemate()) {
            setGameStatus("landing.status.stalemate");
            isGameOver = true;
            return;
        }

        if (loginGame.isThreefoldRepetition()) {
            setGameStatus("landing.status.repetition");
            isGameOver = true;
            return;
        }

        if (loginGame.isInsufficientMaterial()) {
            setGameStatus("landing.status.insufficient");
            isGameOver = true;
            return;
        }

        if (loginGame.isDraw()) {
            setGameStatus("landing.status.draw");
            isGameOver = true;
            return;
        }

        setGameStatus();
        isGameOver = false;
    }

    $: if ($locale) {
        evaluateGameOutcome();
    }

    function initialiseMiniGame() {
        miniEngine = createMiniEngine();
        miniEngine.reset();
        try {
            if (showcaseFen) {
                loginGame.load(showcaseFen);
            } else {
                loginGame.reset();
            }
        } catch (_error) {
            loginGame.reset();
        }
        boardPosition = loginGame.fen();
        previousShowcase = showcaseFen;
        setGameStatus();
        isGameOver = false;
        evaluateGameOutcome();
    }

    onMount(() => {
        initialiseMiniGame();
    });

    onDestroy(() => {
        isActive = false;
    });

    $: if (miniEngine && showcaseFen !== previousShowcase) {
        initialiseMiniGame();
    }

    const toUci = (move) => `${move.from}${move.to}${move.promotion ?? ""}`;

    async function handleBoardMove(event) {
        if (!miniEngine || isThinking || isGameOver) {
            return;
        }

        const { move } = event;
        if (!move) {
            return;
        }

        const playerMoveUci = toUci(move);
        const executed = loginGame.move(move);
        if (!executed) {
            return;
        }

        try {
            miniEngine.applyMove(playerMoveUci);
        } catch (_error) {
            loginGame.undo();
            boardPosition = loginGame.fen();
            evaluateGameOutcome();
            return;
        }

        boardPosition = loginGame.fen();
        evaluateGameOutcome();
        if (isGameOver || !isActive) {
            return;
        }

        isThinking = true;
        try {
            const reply = await miniEngine.think();
            if (!reply || !isActive) {
                evaluateGameOutcome();
                return;
            }

            const replyMove = {
                from: reply.slice(0, 2),
                to: reply.slice(2, 4),
            };
            if (reply.length > 4) {
                replyMove.promotion = reply[4];
            }

            const executed = loginGame.move(replyMove);
            if (executed) {
                boardPosition = loginGame.fen();
                evaluateGameOutcome();
            } else {
                try {
                    loginGame.load(boardPosition);
                } catch (_error) {
                    loginGame.reset();
                    boardPosition = loginGame.fen();
                }
                evaluateGameOutcome();
            }
        } finally {
            if (isActive) {
                isThinking = false;
            }
        }
    }

    const submit = () => {
        onPlay({ username, password });
    };

    const submitAdmin = () => {
        onAdminLogin({ username, password });
    };
</script>

<main class="landing">
    <section class="landing-card glass-panel">
        {#if translatedLanguageOptions.length > 1}
            <div class="language-switcher">
                <div
                    class="landing-lang"
                    role="group"
                    aria-label={$t("landing.language.label")}
                >
                    {#each translatedLanguageOptions as option}
                        <button
                            type="button"
                            class:active={option.code === $locale}
                            on:click={() => handleLocaleSelect(option.code)}
                            aria-pressed={option.code === $locale}
                            aria-label={$t("landing.language.aria")}
                        >
                            {option.label}
                        </button>
                    {/each}
                </div>
                <p class="language-note">{localeNote}</p>
            </div>
        {/if}
        <div class="landing-header">
            <span class="landing-badge">{$t("landing.badge")}</span>
            <h1>{$t("landing.title")}</h1>
            <p class="landing-copy">{$t("landing.copy")}</p>
        </div>
        <div class="landing-board-shell">
            <ChessBoard
                startingFen={showcaseFen}
                positionFen={boardPosition}
                showStatus={false}
                showControls={false}
                interactive={!isThinking && !isGameOver}
                onMove={handleBoardMove}
            />
            {#if gameStatusKey}
                <p class="landing-status" role="status" aria-live="polite">
                    {$t(gameStatusKey, gameStatusParams)}
                </p>
            {/if}
        </div>
        <form class="landing-form" on:submit|preventDefault={submit}>
            <label for="username">{$t("landing.form.username")}</label>
            <input
                id="username"
                name="username"
                autocomplete="username"
                placeholder={$t("landing.form.usernamePlaceholder")}
                bind:value={username}
                required
            />
            <label for="password">{$t("landing.form.password")}</label>
            <input
                id="password"
                name="password"
                type="password"
                autocomplete="current-password"
                placeholder={$t("landing.form.passwordPlaceholder")}
                bind:value={password}
                required
            />
            {#if error}
                <p class="error" role="alert">{error}</p>
            {/if}
            <div class="landing-actions">
                <button type="submit" disabled={isLoading}>
                    {isLoading
                        ? $t("landing.actions.signingIn")
                        : $t("landing.actions.play")}
                </button>
                <button
                    class="secondary compact"
                    type="button"
                    on:click={submitAdmin}
                    disabled={isLoading}
                >
                    {$t("landing.actions.admin")}
                </button>
            </div>
        </form>
    </section>
</main>

<style>
    .landing {
        width: min(480px, 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
    }

    .landing-card {
        width: 100%;
        padding: clamp(1.75rem, 5vw, 2.5rem);
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    .language-switcher {
        align-self: flex-end;
        display: grid;
        gap: 0.35rem;
        text-align: right;
    }

    .landing-lang {
        display: inline-flex;
        gap: 0.35rem;
        padding: 0.25rem;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.45);
        backdrop-filter: blur(8px);
    }

    .landing-lang button {
        border: none;
        background: transparent;
        color: rgba(226, 232, 240, 0.75);
        font-weight: 600;
        font-size: 0.82rem;
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        cursor: pointer;
        transition: background 0.15s ease, color 0.15s ease;
    }

    .landing-lang button:hover {
        background: rgba(59, 130, 246, 0.28);
        color: #e0f2fe;
    }

    .landing-lang button.active {
        background: rgba(37, 99, 235, 0.65);
        color: #e0f2fe;
    }

    .language-note {
        margin: 0;
        font-size: 0.75rem;
        color: rgba(148, 163, 184, 0.7);
    }

    .landing-header {
        display: grid;
        gap: 0.75rem;
        text-align: center;
    }

    .landing-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 0.9rem;
        border-radius: 999px;
        background: rgba(37, 99, 235, 0.18);
        color: #93c5fd;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    h1 {
        font-size: clamp(2rem, 5.8vw, 2.75rem);
        margin: 0;
        color: #f8fafc;
    }

    .landing-copy {
        margin: 0;
        color: rgba(226, 232, 240, 0.76);
        max-width: 30ch;
        justify-self: center;
    }

    .landing-board-shell {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 0.75rem;
    }

    .landing-card :global(.chess-widget) {
        width: 100%;
    }

    .landing-card :global(.board) {
        width: min(400px, 100%);
        margin-inline: auto;
    }

    .landing-status {
        margin: 0;
        font-size: 0.9rem;
        color: rgba(226, 232, 240, 0.85);
    }

    .landing-actions {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        justify-content: center;
    }

    .landing-actions button:not(.compact) {
        flex: 1 1 auto;
        min-width: 0;
    }

    .landing-form {
        display: grid;
        gap: 0.75rem;
    }

    .error {
        margin: 0;
        color: #f87171;
        font-size: 0.9rem;
    }

    @media (max-width: 640px) {
        .landing-card {
            padding: 1.5rem;
            gap: 1.25rem;
        }

        .language-switcher {
            align-self: center;
            text-align: center;
        }

        .landing-actions {
            flex-direction: column;
            align-items: stretch;
        }

        .landing-actions button {
            width: 100%;
        }
    }
</style>
