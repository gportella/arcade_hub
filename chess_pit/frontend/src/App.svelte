<script>
  import LandingView from "./lib/views/LandingView.svelte";
  import GameHubView from "./lib/views/GameHubView.svelte";
  import GamePlayView from "./lib/views/GamePlayView.svelte";
  import ProfileView from "./lib/views/ProfileView.svelte";

  const VIEW = Object.freeze({
    LANDING: "landing",
    GAMES: "games",
    PLAY: "play",
    PROFILE: "profile",
  });

  const CANONICAL_FEN =
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
  const SHOWCASE_FEN =
    "r1bq1rk1/ppp2ppp/2n2n2/2bp4/4P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 2 9";

  const OPPONENT_POOL = [
    {
      id: "u-201",
      nickname: "Mia Lopez",
      avatar: "https://avatar.vercel.sh/mia?text=ML",
      title: "IM",
    },
    {
      id: "u-202",
      nickname: "Samuel Osei",
      avatar: "https://avatar.vercel.sh/samuel?text=SO",
      title: "CM",
    },
    {
      id: "u-203",
      nickname: "Priya Rao",
      avatar: "https://avatar.vercel.sh/priya?text=PR",
      title: "FM",
    },
    {
      id: "u-204",
      nickname: "Lena Fischer",
      avatar: "https://avatar.vercel.sh/lena?text=LF",
      title: "GM",
    },
  ];

  const PROFILE_PRESETS = {
    default: {
      user: {
        id: "u-101",
        nickname: "Nova Knight",
        avatar: "https://avatar.vercel.sh/nova?text=NK",
        rating: 1582,
        bio: "Classical enthusiast chasing IM norms.",
      },
      games: [
        {
          id: "g-3021",
          opponent: OPPONENT_POOL[0],
          status: "ongoing",
          summary: "French Defence, Tarrasch",
          fen: "r1bqk2r/ppp1bppp/2nbpn2/4N3/2BP4/2N2Q2/PPP2PPP/R1B2RK1 w kq - 4 10",
          initialFen:
            "rnbqkbnr/pppppppp/8/8/4P3/3P1N2/PPP2PPP/RNBQKB1R b KQkq - 1 3",
          pgn: "1. d4 e6 2. Nf3 d5 3. e4 Nf6 4. e5 Ne4 5. Bd3 Nc6 6. c3 Be7",
          yourColor: "white",
          lastUpdated: "2025-12-05T15:20:00Z",
        },
        {
          id: "g-3012",
          opponent: OPPONENT_POOL[1],
          status: "finished",
          summary: "Italian Game, Evans Gambit",
          fen: "8/5pk1/5np1/3p2P1/3P1PKP/2r5/8/8 w - - 1 45",
          initialFen: CANONICAL_FEN,
          pgn: "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. b4 Bxb4 5. c3 Ba5 6. d4 exd4 7. O-O d3 8. Qb3 Qf6 9. e5 Qg6 10. Re1 Nge7 11. Ba3 O-O 12. Nbd2 d6 13. exd6 cxd6 14. Ne4 d5 15. Bxd5 Nxd5 16. Qxd5 Rd8 17. Qg5 Qxg5 18. Nfxg5 Bf5 19. Nd6 Bc8 20. Ngxf7 d2 21. Re3 Bg4 22. f3 Bb6 23. Re4 Bf5 24. Nxf5 d1=Q+ 25. Rxd1 Rxd1+ 26. Kh2 Kxf7 27. Nd6+ Rxd6 28. Bxd6 Re8 29. Rf4+ Kg6 30. g4 Re2+ 31. Kh3 h6 32. h5+ Kh7 33. a4 Rc2 34. Rf7 Rxc3 35. Kg3 Nxd4 36. Be5 Ne2+ 37. Kg2 Bd4 38. Rxg7+ Kh8 39. Re7+ Bxe5 40. Rxe5",
          result: "1-0",
          yourColor: "black",
          lastUpdated: "2025-11-28T19:05:00Z",
        },
      ],
    },
    admin: {
      user: {
        id: "u-001",
        nickname: "Admin",
        avatar: "https://avatar.vercel.sh/admin?text=AD",
        rating: 1724,
        bio: "Maintains the hub and loves endgames.",
      },
      games: [
        {
          id: "g-4001",
          opponent: OPPONENT_POOL[2],
          status: "ongoing",
          summary: "Sicilian Defence, Dragon",
          fen: "r2q1rk1/pp1n1ppp/3bp3/2p1N3/2P1P3/2N1B3/PP2BPPP/2RQ1RK1 w - - 2 16",
          initialFen:
            "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 2",
          pgn: "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. Nc3 Bg7 6. Be3 Nf6 7. Be2 O-O 8. O-O d6 9. Nb3 Be6 10. f4 Rc8 11. Kh1 Na5 12. Nxa5 Qxa5 13. Bf3 b5 14. a3 Bc4 15. Re1 Nd7",
          yourColor: "white",
          lastUpdated: "2025-12-06T09:32:00Z",
        },
        {
          id: "g-3990",
          opponent: OPPONENT_POOL[3],
          status: "finished",
          summary: "Queen's Gambit Declined",
          fen: "6k1/5pp1/7p/3p4/2pP1B2/2P3P1/1P3P1P/6K1 b - - 0 42",
          initialFen: CANONICAL_FEN,
          pgn: "1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 b6 7. Be2 Bb7 8. O-O Nbd7 9. cxd5 Nxd5 10. Bxe7 Qxe7 11. Nxd5 Bxd5 12. Qa4 c5 13. Rfd1 Rfd8 14. Rac1 a6 15. dxc5 Nxc5 16. Qa3 a5 17. Nd4 Qg5 18. Bf1 Qg4 19. h3 Qg5 20. Nb5 Bf3 21. Rxd8+ Rxd8 22. Nd4 Bb7 23. b4 axb4 24. Qxb4 Nd7 25. Rc7 Bd5 26. Qd6 Nf8 27. Qxb6 Ng6 28. a4 Nh4 29. g3 Nf3+ 30. Nxf3 Bxf3 31. a5 Qd5 32. a6 Qd1 33. Qb5 Qa1 34. a7 Kh7 35. Rxf7 Be4 36. Qc4 Bd3 37. Rxg7+ Kxg7 38. Qc7+ Kg6 39. Qxd8 Qxf1+ 40. Kh2 Qxf2+ 41. Kh1 Be4#",
          result: "0-1",
          yourColor: "black",
          lastUpdated: "2025-11-18T21:47:00Z",
        },
      ],
    },
  };

  /** @type {"landing" | "games" | "play" | "profile"} */
  let currentView = VIEW.LANDING;
  let isAuthenticated = false;
  let currentUser = null;
  let games = [];
  let selectedGameId = null;
  let selectedGame = null;
  let orderedGames = [];
  let showNewGameForm = false;
  let newGameOpponentId = OPPONENT_POOL[0].id;
  let newGameColor = "white";
  let profileDraft = { nickname: "", avatar: "", bio: "" };
  let availableOpponents = OPPONENT_POOL;

  const formatTime = (iso) => {
    if (!iso) return "";
    const target = new Date(iso);
    const diff = Date.now() - target.getTime();
    const minute = 60000;
    const hour = 60 * minute;
    const day = 24 * hour;

    if (diff < minute) return "moments ago";
    if (diff < hour) {
      const value = Math.round(diff / minute);
      return `${value} min ago`;
    }
    if (diff < day) {
      const value = Math.round(diff / hour);
      return `${value} hr ago`;
    }
    if (diff < 7 * day) {
      const value = Math.round(diff / day);
      return `${value} day${value === 1 ? "" : "s"} ago`;
    }
    return target.toLocaleDateString();
  };

  const parseActiveColor = (fen) => {
    if (!fen) return "white";
    const parts = fen.split(" ");
    return parts[1] === "b" ? "black" : "white";
  };

  const prepareGames = (entries = []) =>
    entries.map((game) => {
      const fen = game.fen ?? CANONICAL_FEN;
      return {
        ...game,
        fen,
        initialFen: game.initialFen ?? fen,
        turn: game.turn ?? parseActiveColor(fen),
      };
    });

  const sortGames = (entries = []) =>
    entries.slice().sort((a, b) => {
      const statusA = a.status === "finished" ? 1 : 0;
      const statusB = b.status === "finished" ? 1 : 0;
      if (statusA !== statusB) return statusA - statusB;
      const timeA = new Date(a.lastUpdated ?? 0).getTime();
      const timeB = new Date(b.lastUpdated ?? 0).getTime();
      return timeB - timeA;
    });

  const authenticate = (role) => {
    const preset = PROFILE_PRESETS[role];
    if (!preset) return;

    currentUser = { ...preset.user };
    games = prepareGames(preset.games);
    profileDraft = {
      nickname: currentUser.nickname,
      avatar: currentUser.avatar,
      bio: currentUser.bio ?? "",
    };
    showNewGameForm = false;
    newGameColor = "white";
    const fallbackOpponent = OPPONENT_POOL.find(
      (entry) => entry.id !== currentUser.id,
    );
    if (fallbackOpponent) {
      newGameOpponentId = fallbackOpponent.id;
    }
    isAuthenticated = true;
    currentView = VIEW.GAMES;
    selectedGameId = null;
  };

  const logout = () => {
    isAuthenticated = false;
    currentUser = null;
    games = [];
    orderedGames = [];
    selectedGameId = null;
    selectedGame = null;
    showNewGameForm = false;
    currentView = VIEW.LANDING;
    profileDraft = { nickname: "", avatar: "", bio: "" };
    newGameOpponentId = OPPONENT_POOL[0].id;
    newGameColor = "white";
  };

  const openGame = (id) => {
    if (!id) return;
    selectedGameId = id;
    currentView = VIEW.PLAY;
  };

  const mutateGame = (id, mutator) => {
    games = games.map((game) => {
      if (game.id !== id) return game;
      return mutator({ ...game });
    });
  };

  const handleBoardMove = (event) => {
    if (!selectedGame || selectedGame.status !== "ongoing") return;
    const { fen } = event.detail ?? {};
    if (!fen) return;
    mutateGame(selectedGame.id, (game) => ({
      ...game,
      fen,
      turn: parseActiveColor(fen),
      lastUpdated: new Date().toISOString(),
    }));
  };

  const handleBoardUndo = (event) => {
    if (!selectedGame || selectedGame.status !== "ongoing") return;
    const { fen } = event.detail ?? {};
    if (!fen) return;
    mutateGame(selectedGame.id, (game) => ({
      ...game,
      fen,
      turn: parseActiveColor(fen),
      lastUpdated: new Date().toISOString(),
    }));
  };

  const handleBoardReset = (event) => {
    if (!selectedGame || selectedGame.status !== "ongoing") return;
    const fen = event.detail?.fen ?? selectedGame.initialFen;
    mutateGame(selectedGame.id, (game) => ({
      ...game,
      fen,
      turn: parseActiveColor(fen),
      lastUpdated: new Date().toISOString(),
    }));
  };

  const saveProfile = () => {
    if (!currentUser) return;
    currentUser = {
      ...currentUser,
      nickname: profileDraft.nickname.trim() || currentUser.nickname,
      avatar: profileDraft.avatar.trim() || currentUser.avatar,
      bio: profileDraft.bio.trim(),
    };
    profileDraft = {
      nickname: currentUser.nickname,
      avatar: currentUser.avatar,
      bio: currentUser.bio ?? "",
    };
  };

  const toggleNewGameForm = () => {
    showNewGameForm = !showNewGameForm;
  };

  const handleOpponentChange = (opponentId) => {
    newGameOpponentId = opponentId;
  };

  const handleColorChange = (color) => {
    newGameColor = color === "black" ? "black" : "white";
  };

  const launchGame = () => {
    if (!currentUser) return;
    const opponent = availableOpponents.find(
      (entry) => entry.id === newGameOpponentId,
    );
    if (!opponent) return;
    const id = `g-${Date.now()}`;
    const fen = CANONICAL_FEN;
    const now = new Date().toISOString();
    const game = {
      id,
      opponent,
      status: "ongoing",
      summary: "Friendly challenge",
      fen,
      initialFen: fen,
      pgn: "",
      result: null,
      yourColor: newGameColor,
      turn: parseActiveColor(fen),
      lastUpdated: now,
    };
    games = [game, ...games];
    selectedGameId = id;
    showNewGameForm = false;
    currentView = VIEW.PLAY;
  };

  const gameStatusLabel = (game) => {
    if (game.status === "finished") {
      return game.result ? `Final · ${game.result}` : "Final";
    }
    if (game.turn === game.yourColor) {
      return "Your move";
    }
    return `${game.opponent.nickname}'s move`;
  };

  const colorLabel = (color) => (color === "white" ? "White" : "Black");

  const openProfile = () => {
    currentView = VIEW.PROFILE;
  };

  const returnToGames = () => {
    currentView = VIEW.GAMES;
  };

  const handleProfileFieldChange = (field, value) => {
    profileDraft = { ...profileDraft, [field]: value };
  };

  $: availableOpponents = OPPONENT_POOL.filter(
    (opponent) => opponent.id !== currentUser?.id,
  );

  $: if (
    availableOpponents.length &&
    !availableOpponents.find((opponent) => opponent.id === newGameOpponentId)
  ) {
    newGameOpponentId = availableOpponents[0].id;
  }

  $: orderedGames = sortGames(games);

  $: {
    if (!orderedGames.length) {
      if (selectedGameId !== null) {
        selectedGameId = null;
      }
    } else if (!orderedGames.find((game) => game.id === selectedGameId)) {
      selectedGameId = orderedGames[0].id;
    }
  }

  $: selectedGame =
    orderedGames.find((game) => game.id === selectedGameId) ?? null;

  $: if (!isAuthenticated && currentView !== VIEW.LANDING) {
    currentView = VIEW.LANDING;
  }

  $: if (currentView === VIEW.PLAY && (!selectedGame || !isAuthenticated)) {
    currentView = isAuthenticated ? VIEW.GAMES : VIEW.LANDING;
  }
</script>

<div class="app-frame">
  {#if currentView === VIEW.LANDING}
    <LandingView
      showcaseFen={SHOWCASE_FEN}
      onPlay={() => authenticate("default")}
      onAdminLogin={() => authenticate("admin")}
    />
  {:else if currentView === VIEW.GAMES && isAuthenticated}
    <GameHubView
      user={currentUser}
      games={orderedGames}
      {selectedGameId}
      {showNewGameForm}
      {availableOpponents}
      {newGameOpponentId}
      {newGameColor}
      {formatTime}
      {gameStatusLabel}
      onOpenGame={openGame}
      onToggleNewGameForm={toggleNewGameForm}
      onChangeOpponent={handleOpponentChange}
      onChangeColor={handleColorChange}
      onLaunchGame={launchGame}
      onOpenProfile={openProfile}
      onLogout={logout}
    />
  {:else if currentView === VIEW.PLAY && isAuthenticated && selectedGame}
    <GamePlayView
      game={selectedGame}
      {formatTime}
      {gameStatusLabel}
      {colorLabel}
      onMove={handleBoardMove}
      onUndo={handleBoardUndo}
      onReset={handleBoardReset}
      onBack={returnToGames}
      onLogout={logout}
    />
  {:else if currentView === VIEW.PROFILE && isAuthenticated}
    <ProfileView
      user={currentUser}
      {profileDraft}
      gameCount={orderedGames.length}
      onFieldChange={handleProfileFieldChange}
      onSave={saveProfile}
      onBack={returnToGames}
      onLogout={logout}
    />
  {/if}
</div>

<style>
  .app-frame {
    width: 100%;
    display: flex;
    justify-content: center;
  }
</style>
