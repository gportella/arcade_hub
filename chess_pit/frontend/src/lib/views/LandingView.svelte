<script>
    import { onMount, onDestroy } from "svelte";
    import { Chess } from "chess.js";
    import ChessBoard from "../ChessBoard.svelte";
    import { createMiniEngine } from "../engine/miniEngine.js";

    export let showcaseFen = "";
    export let onPlay = (_credentials) => {};
    export let onAdminLogin = (_credentials) => {};
    export let error = "";
    export let isLoading = false;

    let username = "";
    let password = "";

    const loginGame = new Chess();
    let miniEngine = null;
    let boardPosition = showcaseFen;
    let isThinking = false;
    let previousShowcase = null;
    let isActive = true;
    let gameStatus = "";
    let isGameOver = false;

    function describeSide(color) {
        return color === "w" ? "White" : "Black";
    }

    function evaluateGameOutcome() {
        if (loginGame.isCheckmate()) {
            const winner = loginGame.turn() === "w" ? describeSide("b") : describeSide("w");
            gameStatus = `${winner} wins by checkmate`;
            isGameOver = true;
            return;
        }

        if (loginGame.isStalemate()) {
            gameStatus = "Draw by stalemate";
            isGameOver = true;
            return;
        }

        if (loginGame.isThreefoldRepetition()) {
            gameStatus = "Draw by repetition";
            isGameOver = true;
            return;
        }

        if (loginGame.isInsufficientMaterial()) {
            gameStatus = "Draw by insufficient material";
            isGameOver = true;
            return;
        }

        if (loginGame.isDraw()) {
            gameStatus = "Draw";
            isGameOver = true;
            return;
        }

        gameStatus = "";
        isGameOver = false;
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
        gameStatus = "";
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
        <div class="landing-header">
            <span class="landing-badge">Arcade Hub · Chess Pit</span>
            <h1>Ready to rook on</h1>
            <p class="landing-copy">
                Fire up the board, then tap play to jump straight into your
                matches.
            </p>
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
            {#if gameStatus}
                <p class="landing-status" role="status" aria-live="polite">{gameStatus}</p>
            {/if}
        </div>
        <form class="landing-form" on:submit|preventDefault={submit}>
            <label for="username">Username</label>
            <input
                id="username"
                name="username"
                autocomplete="username"
                placeholder="player"
                bind:value={username}
                required
            />
            <label for="password">Password</label>
            <input
                id="password"
                name="password"
                type="password"
                autocomplete="current-password"
                placeholder="••••••••"
                bind:value={password}
                required
            />
            {#if error}
                <p class="error" role="alert">{error}</p>
            {/if}
            <div class="landing-actions">
                <button type="submit" disabled={isLoading}>
                    {isLoading ? "Signing in…" : "Play"}
                </button>
                <button
                    class="secondary compact"
                    type="button"
                    on:click={submitAdmin}
                    disabled={isLoading}
                >
                    Admin login
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

        .landing-actions {
            flex-direction: column;
            align-items: stretch;
        }

        .landing-actions button {
            width: 100%;
        }
    }
</style>
