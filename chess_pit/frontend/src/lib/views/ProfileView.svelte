<script>
    export let user = null;
    export let profileDraft = { nickname: "", avatar: "", bio: "" };
    export let gameCount = 0;
    export let onFieldChange = () => {};
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

    <section class="profile-card glass-panel">
        <div class="identity">
            <img
                src={profileDraft.avatar || user.avatar}
                alt={`Avatar of ${profileDraft.nickname || user.nickname}`}
            />
            <div>
                <h1>{profileDraft.nickname || user.nickname}</h1>
                <p class="rating">Rating {user.rating}</p>
                <p class="meta">
                    {gameCount} game{gameCount === 1 ? "" : "s"} in your library
                </p>
            </div>
        </div>
        {#if user.bio}
            <p class="bio">Current bio: {user.bio}</p>
        {/if}
    </section>

    <section class="profile-form glass-panel">
        <h2>Edit profile</h2>
        <form on:submit|preventDefault={onSave}>
            <label for="nickname">Display name</label>
            <input
                id="nickname"
                name="nickname"
                placeholder="Chess alias"
                value={profileDraft.nickname}
                on:input={(event) =>
                    handleInput(
                        "nickname",
                        /** @type {HTMLInputElement} */ (event.currentTarget)
                            .value,
                    )}
            />

            <label for="avatar">Avatar URL</label>
            <input
                id="avatar"
                name="avatar"
                placeholder="https://..."
                value={profileDraft.avatar}
                on:input={(event) =>
                    handleInput(
                        "avatar",
                        /** @type {HTMLInputElement} */ (event.currentTarget)
                            .value,
                    )}
            />

            <label for="bio">Bio</label>
            <textarea
                id="bio"
                name="bio"
                rows="3"
                placeholder="Add a short tagline"
                value={profileDraft.bio}
                on:input={(event) =>
                    handleInput(
                        "bio",
                        /** @type {HTMLTextAreaElement} */ (event.currentTarget)
                            .value,
                    )}
            ></textarea>

            <div class="form-actions">
                <button type="submit">Save changes</button>
            </div>
        </form>
    </section>
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

    .rating {
        margin: 0.35rem 0;
        color: #93c5fd;
        font-weight: 600;
    }

    .meta {
        margin: 0;
        color: rgba(226, 232, 240, 0.7);
    }

    .bio {
        margin: 0;
        color: rgba(226, 232, 240, 0.7);
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

    textarea {
        font-family: inherit;
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
