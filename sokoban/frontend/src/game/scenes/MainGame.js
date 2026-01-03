// scenes/MainGame.js
import { Scene } from "phaser";
import { EventBus } from "../EventBus";
import { WorldBuilder } from "../world/WorldBuilder.js";
import { PushableBox } from "../entities/PushableBox.js";
import { TargetManager } from "../entities/TargetManager.js";
import { getDefaultLevelId, getLevelById, getLevelProgress, getNextLevelId, getPreviousLevelId } from "../levels/index.js";

/**
 * @typedef {Object} LevelGridConfig
 * @property {number} [size]
 * @property {number} [ox]
 * @property {number} [oy]
 * @property {number} [cols]
 * @property {number} [rows]
 *
 * @typedef {Object} LevelConfig
 * @property {string} id
 * @property {string} name
 * @property {LevelGridConfig} [grid]
 * @property {{ col: number, row: number }} [player]
 * @property {Array<{ col: number, row: number }>} [pushables]
 * @property {Array<{ col: number, row: number }>} [targets]
 * @property {boolean} [contour]
 * @property {Array<Record<string, unknown>>} [obstacles]
 * @property {Array<string>} [wallMask]
 * @property {number} [wallColor]
 */

const STORAGE_KEY = "sokoban.currentLevel";

const PLAYER_FRAME_SIZE = 64;
const PLAYER_FRAMES_PER_DIRECTION = 9;
const PLAYER_DIRECTION_ROW_INDEX = new Map([
    ["down", 0],
    ["left", 1],
    ["right", 2],
    ["up", 3]
]);
const PLAYER_DIRECTIONS = Array.from(PLAYER_DIRECTION_ROW_INDEX.keys());

const PLAYER_LAST_VARIANT_KEY = "player.soldier.lastVariant";

const PLAYER_VARIANTS = [
    {
        id: "orange_monk",
        layers: [
            "BODY_male.png",
            "LEGS_robe_skirt.png",
            "TORSO_robe_shirt_brown.png",
            "BELT_rope.png",
            "FEET_shoes_brown.png",
            "HEAD_robe_hood.png"
        ]
    },
    {
        id: "skeleton_plain",
        layers: [
            "BODY_skeleton.png"
        ]
    },
    {
        id: "skeleton_armored",
        layers: [
            "BODY_skeleton.png",
            "FEET_plate_armor_shoes.png",
            "LEGS_plate_armor_pants.png",
            "TORSO_plate_armor_torso.png",
            "TORSO_plate_armor_arms_shoulders.png",
            "HANDS_plate_armor_gloves.png",
            "HEAD_plate_armor_helmet.png"
        ]
    }
];

function sanitizeLayerKey(fileName) {
    return `lpc_${fileName.replace(/[^a-zA-Z0-9]+/g, "_").toLowerCase()}`;
}

const PLAYER_LAYER_LIBRARY = (() => {
    const unique = new Map();
    PLAYER_VARIANTS.forEach(variant => {
        variant.layers.forEach(file => {
            if (!unique.has(file)) {
                unique.set(file, sanitizeLayerKey(file));
            }
        });
    });
    return Array.from(unique.entries()).map(([file, key]) => ({ file, key }));
})();

const PLAYER_LAYER_MAP = new Map(PLAYER_LAYER_LIBRARY.map(({ file, key }) => [file, key]));

function readStoredLevelId() {
    if (typeof window === "undefined") return null;
    try {
        return window.localStorage.getItem(STORAGE_KEY);
    } catch (error) {
        console.warn("Unable to read level from storage", error);
        return null;
    }
}

function writeStoredLevelId(id) {
    if (typeof window === "undefined") return;
    try {
        window.localStorage.setItem(STORAGE_KEY, id);
    } catch (error) {
        console.warn("Unable to persist level to storage", error);
    }
}

export class MainGame extends Scene {
    constructor() { super("MainGame"); }

    init(data) {
        this.requestedLevelId = data && typeof data.levelId === "string" ? data.levelId : null;
        this.playerVariantId = null;
        this.playerVariantLayers = null;
    }

    preload() {
        this.preloadPlayerAssets();
    }

    create() {
        const storedId = readStoredLevelId();
        const initialId = this.requestedLevelId || storedId || getDefaultLevelId();
        this.requestedLevelId = null;

        const playerVariant = this.selectPlayerVariant();
        this.playerVariantId = playerVariant.id;
        this.playerVariantLayers = [...playerVariant.layers];
        this.ensurePlayerAssetsReady(playerVariant);

        /** @type {LevelConfig} */
        const level = getLevelById(initialId);
        this.levelConfig = level;
        this.levelId = level.id;
        this.levelName = level.name;
        this.hasWon = false;
        this.nextLevelId = getNextLevelId(this.levelId);
        this.prevLevelId = getPreviousLevelId(this.levelId);
        writeStoredLevelId(this.levelId);

        const levelGrid = /** @type {LevelGridConfig} */ (level.grid || {});

        let size = levelGrid.size || 64;
        const parsedCols = levelGrid.cols || (level.wallMask ? level.wallMask[0]?.length : null);
        const parsedRows = levelGrid.rows || (level.wallMask ? level.wallMask.length : null);
        const fallbackCols = parsedCols || Math.max(1, Math.floor(this.scale.width / size));
        const fallbackRows = parsedRows || Math.max(1, Math.floor(this.scale.height / size));
        const derivedCols = fallbackCols;
        const derivedRows = fallbackRows;
        const maxWidthSize = Math.max(1, Math.floor(this.scale.width / derivedCols));
        const maxHeightSize = Math.max(1, Math.floor(this.scale.height / derivedRows));
        size = Math.min(size, maxWidthSize, maxHeightSize);
        if (size < 8) size = 8;

        const gridWidthPx = derivedCols * size;
        const gridHeightPx = derivedRows * size;
        const ox = levelGrid.ox !== undefined ? levelGrid.ox : Math.max(0, Math.floor((this.scale.width - gridWidthPx) / 2));
        const oy = levelGrid.oy !== undefined ? levelGrid.oy : Math.max(0, Math.floor((this.scale.height - gridHeightPx) / 2));
        this.moveSpeed = 220;
        this.moveTarget = null;
        this.cancelCommitThreshold = 0.15; // commit move even when key tap is brief
        this.pointerCode = "__pointer__";
        this.playerFacing = "down";

        this.grid = {
            size,
            ox,
            oy,
            cols: derivedCols,
            rows: derivedRows
        };

        const gridRight = this.grid.ox + this.grid.cols * this.grid.size;
        const gridBottom = this.grid.oy + this.grid.rows * this.grid.size;
        drawGrid(this, this.grid.size, this.grid.ox, this.grid.oy, gridRight, gridBottom);

        // const g = this.add.graphics();
        // g.fillStyle(0x4caf50, 1).fillRect(0, 0, size, size);
        // g.lineStyle(2, 0x1b5e20, 1).strokeRect(0, 0, size, size);
        // g.generateTexture("boxTexture", size, size);
        // g.destroy();

        this.box = this.physics.add.sprite(0, 0, this.getSoldierFrameKey(this.playerFacing, 0, this.playerVariantId))
            .setOrigin(0, 0)
            .setInteractive({ useHandCursor: true })
            .setDepth(500);
        this.box.setDisplaySize(this.grid.size, this.grid.size);
        const boxBody = this.getBoxBody();
        boxBody.setCollideWorldBounds(true);
        boxBody.setSize(this.grid.size, this.grid.size, false);
        boxBody.setOffset(0, 0);
        boxBody.setBounce(0);
        boxBody.setImmovable(false);
        this.playIdleAnimation();

        const worldConfig = {
            contour: level.contour !== undefined ? level.contour : true,
            obstacles: level.obstacles || [],
            wallMask: level.wallMask || [],
            color: level.wallColor || 0x888888
        };
        const world = new WorldBuilder(this, this.grid).build(worldConfig);
        this.world = world;

        if (this.input && this.input.manager && this.input.manager.canvas) {
            this.input.manager.canvas.style.touchAction = "none"; // disable browser scroll on touch
        }

        world.getObstacleObjects().forEach(obj => this.physics.add.collider(this.box, obj));

        const targetCells = level.targets || [];
        this.targets = new TargetManager(this, this.grid, targetCells);
        this.winText = this.add.text(this.scale.width / 2, 24, "Well done!", { fontFamily: "Arial", fontSize: "32px", color: "#ffffff" })
            .setOrigin(0.5, 0)
            .setDepth(600)
            .setVisible(false);

        const pushableCells = level.pushables || [];
        this.pushables = pushableCells.map((cell, index) => {
            const textureKey = `pushBoxTexture${index}`;
            return new PushableBox(this, this.grid, textureKey, this.grid.size, cell);
        });

        const playerCell = level.player || { col: 1, row: 1 };
        this.boxCell = { col: playerCell.col, row: playerCell.row };
        this.syncBoxPosition();

        this.moveStart = null;
        this.moveStartCell = null;
        this.moveTargetCell = null;
        this.moveDirection = null;
        this.cancelRequested = false;
        this.currentDirectionCode = null;
        this.pendingDirection = null;
        this.activeKeys = new Map();
        this.keyOrder = [];
        this.awaitingPushables = false;
        this.activePush = null;

        this.pointerActive = false;
        this.activePointerId = null;

        this.pointerHandlers = {
            boxDown: (pointer) => this.onPointerDown(pointer),
            move: (pointer) => this.onPointerMove(pointer),
            up: (pointer) => this.onPointerUp(pointer),
            upOutside: (pointer) => this.onPointerUp(pointer)
        };

        this.box.on("pointerdown", this.pointerHandlers.boxDown);
        this.input.on("pointermove", this.pointerHandlers.move);
        this.input.on("pointerup", this.pointerHandlers.up);
        this.input.on("pointerupoutside", this.pointerHandlers.upOutside);
        this.input.on("pointerdown", this.onGlobalPointerDown, this);
        this.input.on("pointerup", this.onGlobalPointerUp, this);
        this.input.on("pointerupoutside", this.onGlobalPointerUp, this);

        this.input.topOnly = false;
        if (this.input.setPollAlways) {
            this.input.setPollAlways();
        }
        const manager = this.input.manager;
        if (manager && Array.isArray(manager.pointers)) {
            manager.pointers.forEach(pointer => {
                if (pointer && typeof pointer.reset === "function") {
                    pointer.reset();
                }
            });
        }

        this.scaleResizeHandler = () => {
            this.scene.restart({ levelId: this.levelId });
        };
        if (this.scale) {
            this.scale.on("resize", this.scaleResizeHandler, this);
        }

        this.swipeState = null;

        const progress = getLevelProgress(this.levelId);
        EventBus.emit("level-changed", {
            id: this.levelId,
            name: this.levelName,
            index: progress.index,
            total: progress.total,
            hasNext: !!this.nextLevelId,
            hasPrev: !!this.prevLevelId,
            nextId: this.nextLevelId,
            prevId: this.prevLevelId
        });
        EventBus.emit("current-scene-ready", this);

        this.eventHandlers = {
            restart: () => this.scene.restart({ levelId: this.levelId }),
            loadLevel: (requestedId) => {
                if (typeof requestedId === "string" && requestedId.length > 0) {
                    this.scene.restart({ levelId: requestedId });
                }
            }
        };

        EventBus.on("request-restart", this.eventHandlers.restart);
        EventBus.on("request-load-level", this.eventHandlers.loadLevel);

        this.events.once("shutdown", () => {
            if (this.eventHandlers) {
                EventBus.off("request-restart", this.eventHandlers.restart);
                EventBus.off("request-load-level", this.eventHandlers.loadLevel);
            }
            if (this.box && this.pointerHandlers?.boxDown) {
                this.box.off("pointerdown", this.pointerHandlers.boxDown);
            }
            if (this.input) {
                if (this.pointerHandlers) {
                    this.input.off("pointermove", this.pointerHandlers.move);
                    this.input.off("pointerup", this.pointerHandlers.up);
                    this.input.off("pointerupoutside", this.pointerHandlers.upOutside);
                }
                this.input.off("pointerdown", this.onGlobalPointerDown, this);
                this.input.off("pointerup", this.onGlobalPointerUp, this);
                this.input.off("pointerupoutside", this.onGlobalPointerUp, this);
            }
            if (this.scale && this.scaleResizeHandler) {
                this.scale.off("resize", this.scaleResizeHandler, this);
            }
            this.pointerHandlers = null;
            this.swipeState = null;
        });

        const keyDirections = {
            ArrowLeft: { dx: -1, dy: 0 }, ArrowRight: { dx: 1, dy: 0 },
            ArrowUp: { dx: 0, dy: -1 }, ArrowDown: { dx: 0, dy: 1 },
            KeyA: { dx: -1, dy: 0 }, KeyD: { dx: 1, dy: 0 },
            KeyW: { dx: 0, dy: -1 }, KeyS: { dx: 0, dy: 1 }
        };

        this.input.keyboard.on("keydown", (event) => {
            const move = keyDirections[event.code];
            if (!move) return;
            event.preventDefault();
            this.handleKeyDown(event.code, move.dx, move.dy);
        }, this);

        this.input.keyboard.on("keyup", (event) => {
            if (!keyDirections[event.code]) return;
            event.preventDefault();
            this.handleKeyUp(event.code);
        }, this);

        this.checkWinCondition();
    }

    update() {
        if (!this.moveTarget) return;

        const dx = this.moveTarget.x - this.box.x;
        const dy = this.moveTarget.y - this.box.y;
        const close = Math.abs(dx) < 2 && Math.abs(dy) < 2;

        if (this.cancelRequested) {
            const progress = this.computeProgress();
            const commit = progress >= this.cancelCommitThreshold;
            if (commit) {
                this.snapToCell(this.moveTargetCell);
                this.boxCell = { col: this.moveTargetCell.col, row: this.moveTargetCell.row };
                this.commitActivePush();
            } else {
                this.snapToCell(this.moveStartCell);
                this.boxCell = { col: this.moveStartCell.col, row: this.moveStartCell.row };
                this.cancelActivePush();
            }
            this.finishMove(true);
            return;
        }

        if (close) {
            this.snapToCell(this.moveTargetCell);
            this.boxCell = { col: this.moveTargetCell.col, row: this.moveTargetCell.row };
            this.finishMove(false);
        }
    }

    onPointerDown(pointer) {
        const active = this.getActivePointer(pointer);
        this.preventPointerDefault(active);
        this.pointerActive = true;
        this.activePointerId = active ? active.id : null;
        if (this.swipeState && this.swipeState.id === this.activePointerId) {
            this.swipeState.allowSwipe = false;
        }
        if (active) this.commandPointer(active);
    }

    onPointerMove(pointer) {
        const active = this.getActivePointer(pointer);
        if (active) this.preventPointerDefault(active);
        if (!active || !active.isDown) return;
        if (!this.pointerActive) return;
        if (this.activePointerId !== null && active.id !== this.activePointerId) return;
        this.commandPointer(active);
    }

    onPointerUp(pointer) {
        const active = this.getActivePointer(pointer);
        if (active) this.preventPointerDefault(active);
        if (this.activePointerId !== null && active && active.id !== this.activePointerId) return;
        if (!this.pointerActive) return;
        this.pointerActive = false;
        this.activePointerId = null;

        if (this.pendingDirection && this.pendingDirection.code === this.pointerCode) {
            this.pendingDirection = null;
        }

        if (this.moveTarget && this.currentDirectionCode === this.pointerCode) {
            this.cancelRequested = true;
        }
    }

    onGlobalPointerDown(pointer) {
        this.swipeState = {
            id: pointer.id,
            x: pointer.worldX,
            y: pointer.worldY,
            allowSwipe: true
        };
    }

    onGlobalPointerUp(pointer) {
        if (!this.swipeState || this.swipeState.id !== pointer.id) {
            return;
        }
        const state = this.swipeState;
        this.swipeState = null;
        if (!state.allowSwipe) {
            return;
        }
        this.handleSwipe(state, pointer);
    }

    commandPointer(pointer) {
        const cell = this.pointToCell(pointer.worldX, pointer.worldY);
        this.setBoxCell(cell.col, cell.row, this.pointerCode);
    }

    preventPointerDefault(pointer) {
        const ev = pointer.event;
        if (ev && typeof ev.preventDefault === "function" && ev.cancelable) ev.preventDefault();
        if (ev && typeof ev.stopPropagation === "function") ev.stopPropagation();
    }

    getActivePointer(fallback) {
        if (this.input && this.input.activePointer) {
            const active = this.input.activePointer;
            if (active && (fallback ? active.id === fallback.id || active.isDown : true)) return active;
        }
        return fallback || null;
    }

    setBoxCell(col, row, code = null) {
        const c = this.clampCell(col, row);
        const dx = c.col - this.boxCell.col;
        const dy = c.row - this.boxCell.row;
        if (dx === 0 && dy === 0) return;

        let stepX = Math.sign(dx);
        let stepY = Math.sign(dy);
        if (stepX && stepY) {
            if (Math.abs(dx) >= Math.abs(dy)) stepY = 0;
            else stepX = 0;
        }
        if (stepX) stepY = 0;
        else if (stepY) stepX = 0;

        if (!stepX && !stepY) return;

        if (this.moveTarget || !this.pushables.every(p => !p.isMoving())) {
            this.pendingDirection = { dx: stepX, dy: stepY, code: code || null };
            return;
        }

        this.tryMove(stepX, stepY, code || null);
    }

    syncBoxPosition() {
        this.snapToCell(this.boxCell);
        this.moveTarget = null;
        this.moveStart = null;
        this.moveStartCell = null;
        this.moveTargetCell = null;
        this.moveDirection = null;
        this.currentDirectionCode = null;
        this.pendingDirection = null;
        this.cancelRequested = false;
        this.playIdleAnimation();
    }

    handleKeyDown(code, dx, dy) {
        if (!this.activeKeys.has(code)) {
            this.activeKeys.set(code, { dx, dy });
            this.keyOrder = this.keyOrder.filter(c => c !== code);
            this.keyOrder.push(code);
        }

        const direction = { dx, dy, code };
        if (this.moveTarget || !this.pushables.every(p => !p.isMoving())) {
            this.pendingDirection = direction;
            return;
        }

        if (!this.tryMove(dx, dy, code)) {
            this.pendingDirection = direction;
        } else {
            this.pendingDirection = null;
        }
    }

    handleKeyUp(code) {
        if (!this.activeKeys.has(code)) return;
        this.activeKeys.delete(code);
        this.keyOrder = this.keyOrder.filter(c => c !== code);

        if (this.pendingDirection && this.pendingDirection.code === code) {
            this.pendingDirection = null;
        }

        if (this.currentDirectionCode === code) {
            this.cancelRequested = true;
        }
    }

    tryMove(dx, dy, code) {
        if (!dx && !dy) return false;
        if (this.moveTarget) return false;
        if (!this.pushables.every(p => !p.isMoving())) return false;

        const nextCol = this.boxCell.col + dx;
        const nextRow = this.boxCell.row + dy;
        if (!this.isInsideGrid(nextCol, nextRow)) return false;

        const pushable = this.findPushableAt(nextCol, nextRow);
        let pushPlan = null;

        if (pushable) {
            if (pushable.isMoving()) return false;
            const beyondCol = nextCol + dx;
            const beyondRow = nextRow + dy;
            if (!this.isInsideGrid(beyondCol, beyondRow)) return false;
            if (this.world.isBlocked(beyondCol, beyondRow)) return false;
            if (this.findPushableAt(beyondCol, beyondRow)) return false;
            pushPlan = { box: pushable, from: { col: nextCol, row: nextRow }, to: { col: beyondCol, row: beyondRow } };
        } else if (this.world.isBlocked(nextCol, nextRow)) {
            return false;
        }

        this.beginMove(nextCol, nextRow, dx, dy, code, pushPlan);
        return true;
    }

    beginMove(col, row, dx, dy, code, pushPlan) {
        const { size, ox, oy } = this.grid;
        const tx = ox + col * size;
        const ty = oy + row * size;

        this.moveStart = { x: this.box.x, y: this.box.y };
        this.moveStartCell = { col: this.boxCell.col, row: this.boxCell.row };
        this.moveTargetCell = { col, row };
        this.moveDirection = { dx, dy };
        this.moveTarget = { x: tx, y: ty };
        this.currentDirectionCode = code || null;
        this.cancelRequested = false;

        this.updatePlayerFacing(dx, dy);
        this.playWalkAnimation();

        this.activePush = pushPlan || null;
        if (pushPlan) {
            pushPlan.box.moveToCell(pushPlan.to.col, pushPlan.to.row, this.moveSpeed, () => {
                if (this.activePush && this.activePush.box === pushPlan.box && this.activePush.to.col === pushPlan.to.col && this.activePush.to.row === pushPlan.to.row) {
                    this.activePush = null;
                }
                this.onPushableMoveFinished();
            });
        }

        const body = this.getBoxBody();
        const dxPixels = tx - this.box.x;
        const dyPixels = ty - this.box.y;
        const len = Math.hypot(dxPixels, dyPixels);

        if (len === 0) {
            this.snapToCell(this.moveTargetCell);
            this.boxCell = { col, row };
            this.finishMove(false);
            return;
        }

        body.setVelocity((dxPixels / len) * this.moveSpeed, (dyPixels / len) * this.moveSpeed);
    }

    computeProgress() {
        if (!this.moveStart || !this.moveTarget || !this.moveDirection) return 1;
        const axis = this.moveDirection.dx !== 0 ? "x" : "y";
        const start = this.moveStart[axis];
        const target = this.moveTarget[axis];
        const current = this.box[axis];
        const total = target - start;
        if (total === 0) return 1;
        const travelled = current - start;
        return Math.min(Math.max(travelled / total, 0), 1);
    }

    snapToCell(cell) {
        const { size, ox, oy } = this.grid;
        const x = ox + cell.col * size;
        const y = oy + cell.row * size;
        const body = this.getBoxBody();
        body.reset(x, y);
        body.setVelocity(0, 0);
        this.box.setPosition(x, y);
    }

    finishMove(interrupted) {
        const body = this.getBoxBody();
        body.setVelocity(0, 0);
        this.playIdleAnimation();
        this.moveTarget = null;
        this.moveStart = null;
        this.moveDirection = null;
        this.moveStartCell = null;
        this.moveTargetCell = null;
        this.cancelRequested = false;
        this.currentDirectionCode = null;

        if (!this.pushables.every(p => !p.isMoving())) {
            this.awaitingPushables = true;
            return;
        }

        this.scheduleNextMove();
    }

    scheduleNextMove() {
        if (this.moveTarget) return;

        const next = this.consumeNextDirection();
        if (!next) return;

        this.tryMove(next.dx, next.dy, next.code || null);
    }

    consumeNextDirection() {
        if (this.pendingDirection) {
            const dir = this.pendingDirection;
            if (!dir.code || dir.code === this.pointerCode || this.activeKeys.has(dir.code)) {
                this.pendingDirection = null;
                return dir;
            }
            this.pendingDirection = null;
        }

        for (let i = this.keyOrder.length - 1; i >= 0; i--) {
            const code = this.keyOrder[i];
            const dir = this.activeKeys.get(code);
            if (dir) {
                return { code, dx: dir.dx, dy: dir.dy };
            }
        }
        return null;
    }

    findPushableAt(col, row) {
        return this.pushables.find(p => p.isAt(col, row)) || null;
    }

    commitActivePush() {
        if (!this.activePush) return;
        const { box, to } = this.activePush;
        box.cancelMove(to.col, to.row);
        this.activePush = null;
        this.awaitingPushables = false;
        this.checkWinCondition();
    }

    cancelActivePush() {
        if (!this.activePush) return;
        const { box, from } = this.activePush;
        box.cancelMove(from.col, from.row);
        this.activePush = null;
        this.awaitingPushables = false;
        this.checkWinCondition();
    }

    onPushableMoveFinished() {
        if (this.moveTarget) return;
        if (!this.pushables.every(p => !p.isMoving())) return;
        this.awaitingPushables = false;
        this.scheduleNextMove();
        this.checkWinCondition();
    }

    checkWinCondition() {
        if (!this.targets) return;
        const solved = this.targets.areAllOccupied(this.pushables);
        if (solved && !this.hasWon) {
            this.hasWon = true;
            if (this.winText) this.winText.setVisible(true);
            console.log("Well done!");
            const nextId = getNextLevelId(this.levelId);
            EventBus.emit("level-complete", { id: this.levelId, name: this.levelName, nextId });

            if (nextId) {
                this.time.delayedCall(900, () => {
                    this.scene.restart({ levelId: nextId });
                });
            }
        } else if (!solved) {
            this.hasWon = false;
            if (this.winText) this.winText.setVisible(false);
        }
    }

    isInsideGrid(col, row) {
        return col >= 0 && col < this.grid.cols && row >= 0 && row < this.grid.rows;
    }

    getBoxBody() {
        const body = this.box.body;
        return /** @type {import("phaser").Physics.Arcade.Body} */ (body);
    }

    pointToCell(x, y) {
        const { size, ox, oy } = this.grid;
        const col = Math.floor((x - ox) / size);
        const row = Math.floor((y - oy) / size);
        return this.clampCell(col, row);
    }

    clampCell(col, row) {
        const maxCol = this.grid.cols - 1, maxRow = this.grid.rows - 1;
        return { col: Math.min(Math.max(col, 0), maxCol), row: Math.min(Math.max(row, 0), maxRow) };
    }

    updatePlayerFacing(dx, dy) {
        const direction = this.vectorToDirection(dx, dy);
        if (direction) {
            this.playerFacing = direction;
        }
    }

    vectorToDirection(dx, dy) {
        if (!dx && !dy) return null;
        if (Math.abs(dx) > Math.abs(dy)) {
            return dx > 0 ? "right" : "left";
        }
        if (Math.abs(dy) > 0) {
            return dy > 0 ? "down" : "up";
        }
        return null;
    }

    playWalkAnimation() {
        if (!this.box || !this.box.anims || !this.playerVariantId) return;
        const key = this.getWalkAnimationKey(this.playerFacing || "down", this.playerVariantId);
        if (!this.anims.exists(key)) return;
        if (this.box.anims.currentAnim?.key !== key) {
            this.box.anims.play(key, true);
        }
    }

    playIdleAnimation() {
        if (!this.box || !this.box.anims || !this.playerVariantId) return;
        const key = this.getIdleAnimationKey(this.playerFacing || "down", this.playerVariantId);
        if (!this.anims.exists(key)) return;
        if (this.box.anims.currentAnim?.key !== key) {
            this.box.anims.play(key, true);
        }
    }

    getSoldierFrameKey(direction, index, variantId = this.playerVariantId || "default") {
        return `soldier_${variantId}_${direction}_${index}`;
    }

    getWalkAnimationKey(direction, variantId = this.playerVariantId || "default") {
        return `soldier-${variantId}-walk-${direction}`;
    }

    getIdleAnimationKey(direction, variantId = this.playerVariantId || "default") {
        return `soldier-${variantId}-idle-${direction}`;
    }

    handleSwipe(state, pointer) {
        if (!state) return;
        const upX = pointer ? pointer.worldX : state.x;
        const upY = pointer ? pointer.worldY : state.y;

        const dx = upX - state.x;
        const dy = upY - state.y;
        const absDx = Math.abs(dx);
        const absDy = Math.abs(dy);
        const minDistance = Math.max(18, this.grid.size * 0.25);

        if (absDx < minDistance && absDy < minDistance) {
            return;
        }

        let dirX = 0;
        let dirY = 0;
        if (absDx > absDy) {
            dirX = dx > 0 ? 1 : -1;
        } else {
            dirY = dy > 0 ? 1 : -1;
        }

        if (dirX || dirY) {
            this.tryMove(dirX, dirY, this.pointerCode);
        }
    }

    selectPlayerVariant() {
        if (!PLAYER_VARIANTS.length) {
            throw new Error("No player variants configured");
        }
        const lastId = this.registry.get(PLAYER_LAST_VARIANT_KEY) || null;
        if (PLAYER_VARIANTS.length === 1) {
            const only = PLAYER_VARIANTS[0];
            this.registry.set(PLAYER_LAST_VARIANT_KEY, only.id);
            return only;
        }

        let chosen = null;
        let attempt = 0;
        while (!chosen && attempt < 8) {
            const candidate = PLAYER_VARIANTS[Math.floor(Math.random() * PLAYER_VARIANTS.length)];
            if (!lastId || candidate.id !== lastId || attempt >= 3) {
                chosen = candidate;
            }
            attempt++;
        }

        if (!chosen) {
            chosen = PLAYER_VARIANTS[0];
        }

        this.registry.set(PLAYER_LAST_VARIANT_KEY, chosen.id);
        return chosen;
    }

    preloadPlayerAssets() {
        const basePath = "../assets/figures/lpc_entry/png/walkcycle";
        PLAYER_LAYER_LIBRARY.forEach(spec => {
            if (this.textures.exists(spec.key)) return;
            const url = new URL(`${basePath}/${spec.file}`, import.meta.url).href;
            this.load.spritesheet(spec.key, url, { frameWidth: PLAYER_FRAME_SIZE, frameHeight: PLAYER_FRAME_SIZE });
        });
    }

    ensurePlayerAssetsReady(variant) {
        const layerKeys = variant.layers.map(file => {
            const key = PLAYER_LAYER_MAP.get(file);
            if (!key) {
                console.warn(`No texture mapping registered for layer file ${file}`);
            }
            return key;
        }).filter(Boolean);

        const missingTexture = layerKeys.find(layerKey => !this.textures.exists(layerKey));
        if (missingTexture) {
            console.warn(`Player layer texture missing: ${missingTexture}`);
            return;
        }

        PLAYER_DIRECTIONS.forEach((direction, dirIndex) => {
            const rowIndex = PLAYER_DIRECTION_ROW_INDEX.get(direction) ?? dirIndex;
            for (let frameIndex = 0; frameIndex < PLAYER_FRAMES_PER_DIRECTION; frameIndex++) {
                const compositeKey = this.getSoldierFrameKey(direction, frameIndex, variant.id);
                if (this.textures.exists(compositeKey)) {
                    this.textures.remove(compositeKey);
                }

                const renderTexture = this.make.renderTexture({ width: PLAYER_FRAME_SIZE, height: PLAYER_FRAME_SIZE, add: false }, false);
                layerKeys.forEach(layerKey => {
                    const frameNumber = rowIndex * PLAYER_FRAMES_PER_DIRECTION + frameIndex;
                    renderTexture.drawFrame(layerKey, frameNumber, 0, 0);
                });
                renderTexture.saveTexture(compositeKey);
                renderTexture.destroy();
            }

            const walkKey = this.getWalkAnimationKey(direction, variant.id);
            if (this.anims.exists(walkKey)) {
                this.anims.remove(walkKey);
            }
            this.anims.create({
                key: walkKey,
                frames: this.buildSoldierAnimationFrames(direction, variant.id),
                frameRate: 10,
                repeat: -1
            });

            const idleKey = this.getIdleAnimationKey(direction, variant.id);
            if (this.anims.exists(idleKey)) {
                this.anims.remove(idleKey);
            }
            this.anims.create({
                key: idleKey,
                frames: [{ key: this.getSoldierFrameKey(direction, 0, variant.id) }],
                frameRate: 1,
                repeat: -1
            });
        });
    }

    buildSoldierAnimationFrames(direction, variantId = this.playerVariantId) {
        const frames = [];
        for (let frameIndex = 1; frameIndex < PLAYER_FRAMES_PER_DIRECTION; frameIndex++) {
            frames.push({ key: this.getSoldierFrameKey(direction, frameIndex, variantId) });
        }
        return frames;
    }
}

function drawGrid(scene, size, ox, oy, w, h, color = 0xffffff, alpha = 0.12) {
    const grid = scene.add.graphics();
    grid.lineStyle(1, color, alpha);
    for (let x = ox; x <= w; x += size) { grid.beginPath(); grid.moveTo(x, oy); grid.lineTo(x, h); grid.strokePath(); }
    for (let y = oy; y <= h; y += size) { grid.beginPath(); grid.moveTo(ox, y); grid.lineTo(w, y); grid.strokePath(); }
    return grid;
}