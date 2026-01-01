import { derived, writable, get } from "svelte/store";

const STORAGE_KEY = "rook-on.locale";
const FALLBACK_LOCALE = "en";

const MESSAGES = {
    en: {
        "locale.english": "English",
        "locale.catalan": "Català (Girona)",
        "landing.badge": "Arcade Hub · Chess Pit",
        "landing.title": "Ready to rook on",
        "landing.copy":
            "Fire up the board, then tap play to jump straight into your matches.",
        "landing.status.checkmate": "{winner} wins by checkmate",
        "landing.status.stalemate": "Draw by stalemate",
        "landing.status.repetition": "Draw by repetition",
        "landing.status.insufficient": "Draw by insufficient material",
        "landing.status.draw": "Draw",
        "landing.form.username": "Username",
        "landing.form.password": "Password",
        "landing.form.usernamePlaceholder": "player",
        "landing.form.passwordPlaceholder": "••••••••",
        "landing.form.error.required": "Username and password are required.",
        "landing.actions.play": "Play",
        "landing.actions.signingIn": "Signing in…",
        "landing.actions.admin": "Admin login",
        "landing.language.label": "Language",
        "landing.language.manual": "Change language",
        "landing.language.aria": "Toggle language",
        "time.moments": "moments ago",
        "time.minutes": "{count} {unit} ago",
        "time.hours": "{count} {unit} ago",
        "time.days": "{count} {unit} ago",
        "color.white": "White",
        "color.black": "Black",
        "color.whiteLower": "white",
        "color.blackLower": "black",
        "game.summary.default": "Friendly challenge",
        "game.summary.engine": "Engine match vs {name}",
        "game.status.final": "Final",
        "game.status.finalWithResult": "Final · {result}",
        "game.status.aborted": "Aborted",
        "game.status.yourMove": "Your move",
        "game.status.opponentMove": "{name}'s move",
        "hub.header.title": "Games",
        "hub.header.subtitle": "{ongoing} ongoing · {total} total",
        "hub.actions.logout": "Log out",
        "hub.actions.profile": "Edit profile",
        "hub.actions.profileAria": "Edit profile",
        "hub.section.matches": "Your matches",
        "hub.actions.refresh": "Refresh",
        "hub.actions.new": "New challenge",
        "hub.actions.close": "Close",
        "hub.form.opponent": "Opponent",
        "hub.form.color": "Play as",
        "hub.form.depth": "Engine depth",
        "hub.form.depthPlaceholder": "1-64",
        "hub.form.depthHelp": "Choose how many plies the engine searches (1-64).",
        "hub.form.depthHint": "Default: {value}",
        "hub.form.timeInitial": "Initial time (minutes)",
        "hub.form.timeInitialPlaceholder": "Leave blank for untimed",
        "hub.form.timeInitialHelp": "Set minutes per side. Leave blank for untimed games.",
        "hub.form.timeIncrement": "Increment (seconds)",
        "hub.form.timeIncrementPlaceholder": "0",
        "hub.form.timeIncrementHelp": "Optional per-move bonus seconds.",
        "hub.form.engineMode": "Engine pacing",
        "hub.form.engineModeDepth": "Depth limited",
        "hub.form.engineModeTime": "Timed play",
        "hub.form.engineModeHelp": "Pick either a search depth or a clock for engine challenges.",
        "hub.form.launch": "Launch game",
        "hub.empty": "No games yet. Start a new challenge to begin.",
        "play.back": "← Games",
        "play.backAria": "Back to games",
        "play.logout": "Log out",
        "play.meta": "You play {colorTitle}",
        "play.updated": "Updated {time}",
        "play.controls.board": "Board controls",
        "play.controls.resign": "Resign",
        "play.info.summary": "Summary",
        "play.info.result": "Result",
        "play.info.pgn": "PGN",
        "play.clock.heading": "Clocks",
        "play.clock.label": "Time control",
        "play.clock.unlimited": "Untimed",
        "play.clock.minutesSuffix": "min",
        "play.clock.secondsSuffix": "s",
        "play.clock.increment": "+{value}{unit}",
        "play.clock.live": "Live clock",
        "play.placeholder": "No game selected.",
        "analysis.heading": "Post-game analysis",
        "analysis.button": "Analyze with {engine}",
        "analysis.running": "Analyzing…",
        "analysis.loading": "The engine is thinking…",
        "analysis.pending": "No analysis yet. Run it to review the final position.",
        "analysis.unavailable.engine": "Analysis engine unavailable.",
        "analysis.unavailable.status": "Finish the game to unlock analysis.",
        "analysis.field.engine": "Engine",
        "analysis.field.depth": "Depth",
        "analysis.field.score": "Score (white)",
        "analysis.field.mate": "Mate threat",
        "analysis.field.bestMove": "Best move",
        "analysis.field.variation": "Principal variation",
        "analysis.noScore": "No score reported.",
        "analysis.mate": "Mate in {moves} ({color})",
        "analysis.mateWhite": "white to move",
        "analysis.mateBlack": "black to move",
        "analysis.noBest": "No move found.",
        "analysis.noLine": "No principal variation.",
        "analysis.lastRun": "Last analyzed {time}",
        "analysis.engineFallback": "the engine",
        "analysis.probability.heading": "Win / draw / loss odds",
        "analysis.probability.timeline": "Odds progression",
        "analysis.probability.aria": "Probability chart for analyzed moves",
        "analysis.probability.white": "White wins",
        "analysis.probability.draw": "Draw",
        "analysis.probability.black": "Black wins",
        "analysis.error.generic": "Analysis failed.",
        "analysis.error.unfinished": "Analysis is available after the game finishes.",
        "analysis.error.noEngine": "Analysis engine not available.",
        "analysis.timeline.heading": "Move breakdown",
        "analysis.timeline.move": "Move {number} · {player}",
        "analysis.timeline.played": "Played",
        "analysis.timeline.evalBefore": "Eval before",
        "analysis.timeline.evalAfter": "Eval after",
        "analysis.timeline.delta": "Shift",
        "analysis.timeline.best": "Engine suggestion",
        "analysis.timeline.variation": "Line",
        "analysis.timeline.noDelta": "—",
        "analysis.annotation.brilliant": "Brilliant move",
        "analysis.annotation.checkmate": "Checkmate",
        "analysis.annotation.strong": "Strong move",
        "analysis.annotation.interesting": "Interesting idea",
        "analysis.annotation.dubious": "Dubious move",
        "analysis.annotation.mistake": "Mistake",
        "analysis.annotation.blunder": "Blunder",
        "analysis.viewer.heading": "Move insight",
        "analysis.viewer.prev": "Prev",
        "analysis.viewer.next": "Next",
        "analysis.viewer.close": "Close replay",
        "analysis.viewer.counter": "{current} / {total}",
        "analysis.viewer.sliderAria": "Scrub through analyzed moves",
        "analysis.viewer.empty": "Start the replay to explore the engine suggestions.",
        "profile.back": "Back to games",
        "profile.logout": "Log out",
        "profile.gamesCount": "{count} game{suffix} in your library",
        "profile.stats.wins": "Wins: {count}",
        "profile.stats.losses": "Losses: {count}",
        "profile.stats.draws": "Draws: {count}",
        "profile.stats.rating": "Rating: {value}",
        "profile.update": "Update profile",
        "profile.form.avatar": "Avatar URL",
        "profile.form.avatarPlaceholder": "https://...",
        "profile.form.password": "New password",
        "profile.form.passwordPlaceholder": "Leave blank to keep current password",
        "profile.form.save": "Save changes",
        "profile.placeholder": "No user loaded.",
        "avatar.label": "Avatar of {name}",
        "label.engine": "Engine",
        "label.unknown": "Unknown",
        "label.rating": "Rating",
        "label.ratingValue": "Rating: {value}",
        "errors.loadHub": "Failed to load games.",
        "errors.loadGame": "Failed to load game.",
        "errors.engineRequest": "Engine move request failed.",
        "errors.engineUnavailable":
            "Chess engine unavailable. Install the required host binary (e.g. skaks) and retry.",
        "errors.engineTerminated":
            "Chess engine terminated unexpectedly. Please try again soon.",
        "errors.createGame": "Unable to create game.",
        "errors.moveRecord": "Move could not be recorded.",
        "errors.resign": "Unable to resign from the game.",
        "errors.profileUpdate": "Failed to update profile.",
        "errors.loginIncomplete": "Unable to finish signing in.",
        "errors.login": "Unable to sign in.",
        "notice.language.detected": "Detected from your region",
        "notice.language.manual": "Change language manually",
    },
    ca: {
        "locale.english": "Anglès",
        "locale.catalan": "Català (Girona)",
        "landing.badge": "Arcade Hub · Chess Pit",
        "landing.title": "A punt per fer el primer moviment",
        "landing.copy":
            "Obre el tauler i prem jugar per entrar a les teves partides.",
        "landing.status.checkmate": "Les {winner} guanyen per escac i mat",
        "landing.status.stalemate": "Taules per ofegat",
        "landing.status.repetition": "Taules per repetició",
        "landing.status.insufficient": "Taules per material insuficient",
        "landing.status.draw": "Taules",
        "landing.form.username": "Usuari",
        "landing.form.password": "Contrasenya",
        "landing.form.usernamePlaceholder": "jugador",
        "landing.form.passwordPlaceholder": "••••••••",
        "landing.form.error.required": "Cal introduir usuari i contrasenya.",
        "landing.actions.play": "Jugar",
        "landing.actions.signingIn": "Iniciant sessió…",
        "landing.actions.admin": "Accés administració",
        "landing.language.label": "Idioma",
        "landing.language.manual": "Canvia l'idioma",
        "landing.language.aria": "Canvia l'idioma",
        "time.moments": "fa uns instants",
        "time.minutes": "fa {count} {unit}",
        "time.hours": "fa {count} {unit}",
        "time.days": "fa {count} {unit}",
        "color.white": "Blanques",
        "color.black": "Negres",
        "color.whiteLower": "blanques",
        "color.blackLower": "negres",
        "game.summary.default": "Repte amistós",
        "game.summary.engine": "Partida contra el motor {name}",
        "game.status.final": "Final",
        "game.status.finalWithResult": "Final · {result}",
        "game.status.aborted": "Anul·lada",
        "game.status.yourMove": "El teu torn",
        "game.status.opponentMove": "Torn de {name}",
        "hub.header.title": "Partides",
        "hub.header.subtitle": "{ongoing} en joc · {total} totals",
        "hub.actions.logout": "Tanca sessió",
        "hub.actions.profile": "Edita el perfil",
        "hub.actions.profileAria": "Edita el perfil",
        "hub.section.matches": "Les teves partides",
        "hub.actions.refresh": "Actualitza",
        "hub.actions.new": "Nou repte",
        "hub.actions.close": "Tanca",
        "hub.form.opponent": "Rival",
        "hub.form.color": "Juga amb",
        "hub.form.depth": "Profunditat del motor",
        "hub.form.depthPlaceholder": "1-64",
        "hub.form.depthHelp": "Indica quants migmoviments explora el motor (1-64).",
        "hub.form.depthHint": "Per defecte: {value}",
        "hub.form.timeInitial": "Temps inicial (minuts)",
        "hub.form.timeInitialPlaceholder": "Deixa-ho en blanc",
        "hub.form.timeInitialHelp": "Defineix els minuts per jugador. Deixa-ho en blanc per jugar sense rellotge.",
        "hub.form.timeIncrement": "Increment (segons)",
        "hub.form.timeIncrementPlaceholder": "0",
        "hub.form.timeIncrementHelp": "Segons extra per jugada (opcional).",
        "hub.form.engineMode": "Ritme contra el motor",
        "hub.form.engineModeDepth": "Profunditat limitada",
        "hub.form.engineModeTime": "Partida amb rellotge",
        "hub.form.engineModeHelp": "Escull entre una profunditat de càlcul o un rellotge quan reptes el motor.",
        "hub.form.launch": "Inicia la partida",
        "hub.empty": "Encara no tens partides. Comença un repte per jugar.",
        "play.back": "← Partides",
        "play.backAria": "Torna a les partides",
        "play.logout": "Tanca sessió",
        "play.meta": "Jugues amb les {colorLower}",
        "play.updated": "Actualitzat {time}",
        "play.controls.board": "Controls del tauler",
        "play.controls.resign": "Rendir-se",
        "play.info.summary": "Resum",
        "play.info.result": "Resultat",
        "play.info.pgn": "PGN",
        "play.clock.heading": "Rellotges",
        "play.clock.label": "Control de temps",
        "play.clock.unlimited": "Sense límit",
        "play.clock.minutesSuffix": "min",
        "play.clock.secondsSuffix": "s",
        "play.clock.increment": "+{value}{unit}",
        "play.clock.live": "Rellotge en directe",
        "play.placeholder": "Cap partida seleccionada.",
        "analysis.heading": "Anàlisi de la partida",
        "analysis.button": "Analitza amb {engine}",
        "analysis.running": "Analitzant…",
        "analysis.loading": "El motor està pensant…",
        "analysis.pending": "Encara no hi ha cap anàlisi. Executa-la per revisar la posició final.",
        "analysis.unavailable.engine": "El motor d'anàlisi no està disponible.",
        "analysis.unavailable.status": "Completa la partida per activar l'anàlisi.",
        "analysis.field.engine": "Motor",
        "analysis.field.depth": "Profunditat",
        "analysis.field.score": "Avaluació (blanques)",
        "analysis.field.mate": "Amenaça de mat",
        "analysis.field.bestMove": "Millor jugada",
        "analysis.field.variation": "Variació principal",
        "analysis.noScore": "Sense avaluació.",
        "analysis.mate": "Mat en {moves} ({color})",
        "analysis.mateWhite": "torn de blanques",
        "analysis.mateBlack": "torn de negres",
        "analysis.noBest": "No s'ha trobat cap jugada.",
        "analysis.noLine": "Cap variació principal.",
        "analysis.lastRun": "Darrera anàlisi {time}",
        "analysis.engineFallback": "el motor",
        "analysis.probability.heading": "Probabilitats de victòria / taules / derrota",
        "analysis.probability.timeline": "Evolució de les probabilitats",
        "analysis.probability.aria": "Gràfic de probabilitats de les jugades analitzades",
        "analysis.probability.white": "Victòria de blanques",
        "analysis.probability.draw": "Taules",
        "analysis.probability.black": "Victòria de negres",
        "analysis.error.generic": "Ha fallat l'anàlisi.",
        "analysis.error.unfinished": "L'anàlisi estarà disponible quan acabi la partida.",
        "analysis.error.noEngine": "No hi ha cap motor d'anàlisi disponible.",
        "analysis.timeline.heading": "Anàlisi jugada a jugada",
        "analysis.timeline.move": "Jugada {number} · {player}",
        "analysis.timeline.played": "Jugada",
        "analysis.timeline.evalBefore": "Avaluació abans",
        "analysis.timeline.evalAfter": "Avaluació després",
        "analysis.timeline.delta": "Canvi",
        "analysis.timeline.best": "Suggeriment del motor",
        "analysis.timeline.variation": "Línia",
        "analysis.timeline.noDelta": "—",
        "analysis.annotation.brilliant": "Jugada brillant",
        "analysis.annotation.checkmate": "Escac i mat",
        "analysis.annotation.strong": "Jugada forta",
        "analysis.annotation.interesting": "Jugada interessant",
        "analysis.annotation.dubious": "Jugada dubtosa",
        "analysis.annotation.mistake": "Error",
        "analysis.annotation.blunder": "Error greu",
        "analysis.viewer.heading": "Anàlisi de la jugada",
        "analysis.viewer.prev": "Anterior",
        "analysis.viewer.next": "Següent",
        "analysis.viewer.close": "Tanca la repetició",
        "analysis.viewer.counter": "{current} / {total}",
        "analysis.viewer.sliderAria": "Desplaça't per les jugades analitzades",
        "analysis.viewer.empty": "Inicia la repetició per veure els suggeriments del motor.",
        "profile.back": "Torna a les partides",
        "profile.logout": "Tanca sessió",
        "profile.gamesCount": "{count} partida{suffix} a la teva biblioteca",
        "profile.stats.wins": "Victòries: {count}",
        "profile.stats.losses": "Derrotes: {count}",
        "profile.stats.draws": "Taules: {count}",
        "profile.stats.rating": "ELO: {value}",
        "profile.update": "Actualitza el perfil",
        "profile.form.avatar": "URL de l'avatar",
        "profile.form.avatarPlaceholder": "https://...",
        "profile.form.password": "Nova contrasenya",
        "profile.form.passwordPlaceholder": "Deixa-ho en blanc per mantenir la contrasenya actual",
        "profile.form.save": "Desa els canvis",
        "profile.placeholder": "No s'ha carregat cap usuari.",
        "avatar.label": "Avatar de {name}",
        "label.engine": "Motor",
        "label.unknown": "Desconegut",
        "label.rating": "ELO",
        "label.ratingValue": "ELO: {value}",
        "errors.loadHub": "No s'han pogut carregar les partides.",
        "errors.loadGame": "No s'ha pogut carregar la partida.",
        "errors.engineRequest": "No s'ha pogut demanar el moviment del motor.",
        "errors.engineUnavailable":
            "Motor d'escacs no disponible. Instal·la el binari requerit (p. ex. skaks) i torna-ho a provar.",
        "errors.engineTerminated":
            "El motor d'escacs s'ha aturat de manera inesperada. Torna-ho a provar més endavant.",
        "errors.createGame": "No s'ha pogut crear la partida.",
        "errors.moveRecord": "No s'ha pogut registrar el moviment.",
        "errors.resign": "No s'ha pogut abandonar la partida.",
        "errors.profileUpdate": "No s'ha pogut actualitzar el perfil.",
        "errors.loginIncomplete": "No s'ha pogut completar l'inici de sessió.",
        "errors.login": "No s'ha pogut iniciar sessió.",
        "notice.language.detected": "Detectat segons la teva regió",
        "notice.language.manual": "Canvia l'idioma manualment",
    },
};

const supportedLocales = Object.keys(MESSAGES);

function normaliseLocale(input) {
    if (!input || typeof input !== "string") {
        return FALLBACK_LOCALE;
    }
    const base = input.toLowerCase();
    if (supportedLocales.includes(base)) {
        return base;
    }
    const simplified = base.split("-")[0];
    if (supportedLocales.includes(simplified)) {
        return simplified;
    }
    return FALLBACK_LOCALE;
}

function safeGetStorage() {
    if (typeof window === "undefined") {
        return null;
    }
    try {
        return window.localStorage ?? null;
    } catch (_error) {
        return null;
    }
}

function loadStoredLocale() {
    const storage = safeGetStorage();
    if (!storage) {
        return null;
    }
    try {
        const value = storage.getItem(STORAGE_KEY);
        return value ? normaliseLocale(value) : null;
    } catch (_error) {
        return null;
    }
}

function persistLocale(value) {
    const storage = safeGetStorage();
    if (!storage) {
        return;
    }
    try {
        storage.setItem(STORAGE_KEY, value);
    } catch (_error) {
        /* ignore */
    }
}

function detectNavigatorLocale() {
    if (typeof navigator === "undefined") {
        return null;
    }
    const candidates = Array.isArray(navigator.languages)
        ? navigator.languages
        : [navigator.language, navigator.userLanguage, navigator.browserLanguage].filter(
            Boolean,
        );
    for (const candidate of candidates) {
        const normalised = normaliseLocale(candidate);
        if (normalised === "ca") {
            return normalised;
        }
        if (normalised === "en") {
            return normalised;
        }
    }
    return null;
}

function translate(localeCode, key, params) {
    const dictionary = MESSAGES[localeCode] ?? MESSAGES[FALLBACK_LOCALE];
    const fallbackDictionary = MESSAGES[FALLBACK_LOCALE];
    const template = dictionary[key] ?? fallbackDictionary[key] ?? key;
    if (!params) {
        return template;
    }
    return template.replace(/\{(\w+)\}/g, (_match, token) => {
        if (!(token in params)) {
            return "";
        }
        const value = params[token];
        return value === undefined || value === null ? "" : String(value);
    });
}

const locale = writable(FALLBACK_LOCALE);

const t = derived(locale, ($locale) => {
    return (key, params) => translate($locale, key, params);
});

function setLocale(next) {
    const target = normaliseLocale(next);
    locale.set(target);
    persistLocale(target);
}

function detectInitialLocale() {
    const stored = loadStoredLocale();
    if (stored) {
        return stored;
    }
    const detected = detectNavigatorLocale();
    if (detected) {
        return detected;
    }
    return FALLBACK_LOCALE;
}

function getActiveLocale() {
    return get(locale);
}

export { supportedLocales, locale, t, setLocale, detectInitialLocale, getActiveLocale };
