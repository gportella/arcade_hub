<script>
    /**
     * @type {{ username: string; avatar_url?: string | null; games_won: number; games_lost: number; games_drawn: number } | null}
     */
    export let user = null;
    /** @type {{ avatarUrl: string; password: string }} */
    export let profileDraft = { avatarUrl: "", password: "" };
    export let gameCount = 0;
    export let onFieldChange = (_field, _value) => {};
    export let onSave = () => {};
    export let onBack = () => {};
    export let onLogout = () => {};

    const handleInput = (field, value) => {
        onFieldChange(field, value);
    };
</script>

<main class="profile">
    <header class="profile-header">
        <button class="secondary small" on:click={onBack}>Back to games</button>
        <div class="header-actions">
            <button class="secondary small" on:click={onLogout}>Log out</button>
        </div>
    </header>

    {#if user}
        <section class="profile-card glass-panel">
            <div class="identity">
                <img
                    src={profileDraft.avatarUrl || user.avatar_url || ""}
                    alt={`Avatar of ${user.username}`}
                />
                <div>
                    <h1>{user.username}</h1>
                    <p class="meta">
                        {gameCount} game{gameCount === 1 ? "" : "s"} in your library
                    </p>
                    <ul class="stats">
                        <li>Wins: {user.games_won}</li>
                        <li>Losses: {user.games_lost}</li>
                        <li>Draws: {user.games_drawn}</li>
                    </ul>
                </div>
            </div>
        </section>

        <section class="profile-form glass-panel">
            <h2>Update profile</h2>
            <form on:submit|preventDefault={onSave}>
                <label for="avatar">Avatar URL</label>
                <input
                    id="avatar"
                    name="avatar"
                    placeholder="https://..."
                    value={profileDraft.avatarUrl}
                    on:input={(event) =>
                        handleInput(
                            "avatarUrl",
                            /** @type {HTMLInputElement} */ (
                                event.currentTarget
                            ).value,
                        )}
                />

                <label for="password">New password</label>
                <input
                    id="password"
                    name="password"
                    type="password"
                    placeholder="Leave blank to keep current password"
                    value={profileDraft.password}
                    on:input={(event) =>
                        handleInput(
                            "password",
                            /** @type {HTMLInputElement} */ (
                                event.currentTarget
                            ).value,
                        )}
                />

                <div class="form-actions">
                    <button type="submit">Save changes</button>
                </div>
            </form>
        </section>
    {:else}
        <p class="placeholder">No user loaded.</p>
    {/if}
</main>

<style>
    .profile {
        width: min(640px, 100%);
        display: flex;
        flex-direction: column;
        gap: clamp(1.25rem, 4vw, 1.75rem);
        margin: 0 auto;
    }

    .profile-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .header-actions {
        display: flex;
        gap: 0.75rem;
    }

    .small {
        padding: 0.5em 1.1em;
        font-size: 0.9rem;
    }

    .profile-card {
        padding: clamp(1.5rem, 4vw, 2rem);
        display: flex;
        flex-direction: column;
        gap: 1.1rem;
    }

    .identity {
        display: flex;
        gap: 1rem;
        align-items: center;
    }

    .identity img {
        width: 72px;
        height: 72px;
        border-radius: 24px;
        object-fit: cover;
        border: 2px solid rgba(148, 163, 184, 0.35);
    }

    .identity h1 {
        margin: 0;
        font-size: clamp(1.6rem, 4vw, 1.9rem);
        color: #f8fafc;
    }

    .meta {
        margin: 0;
        color: rgba(226, 232, 240, 0.7);
    }

    .stats {
        margin: 0.4rem 0 0;
        padding-left: 1.1rem;
        color: rgba(226, 232, 240, 0.75);
        display: grid;
        gap: 0.2rem;
    }

    .profile-form {
        padding: clamp(1.5rem, 4vw, 2rem);
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
    }

    .profile-form h2 {
        margin: 0;
        color: #f8fafc;
        font-size: 1.2rem;
    }

    form {
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
    }

    .form-actions {
        display: flex;
        justify-content: flex-end;
    }

    @media (max-width: 640px) {
        .identity {
            align-items: flex-start;
        }

        .identity img {
            width: 64px;
            height: 64px;
        }

        .profile-card,
        .profile-form {
            padding: 1.25rem;
        }
    }
</style>
