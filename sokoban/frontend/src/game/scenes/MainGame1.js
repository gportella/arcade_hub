// @ts-nocheck
import { Scene } from "phaser";
import { EventBus } from "../EventBus";

export class MainGame extends Scene {
    box;
    grid;
    boxCell;
    blocked;       // Set<string> => "col,row"
    isDragging;
    pointerHandler;
    pointerMoveHandler;
    pointerUpHandler;
    keyHandler;

    constructor() { super("MainGame"); }

    create() {
        // Grid setup
        const gridSize = 64, gridOffsetX = 0, gridOffsetY = 0;
        this.grid = {
            size: gridSize,
            ox: gridOffsetX,
            oy: gridOffsetY,
            cols: Math.floor((this.scale.width - gridOffsetX) / gridSize),
            rows: Math.floor((this.scale.height - gridOffsetY) / gridSize)
        };
        drawGrid(this, gridSize, gridOffsetX, gridOffsetY, this.scale.width, this.scale.height);

        // Player box (dynamic body aligned to top-left)
        const boxSize = 64;
        const g = this.add.graphics();
        g.fillStyle(0x4caf50, 1).fillRect(0, 0, boxSize, boxSize);
        g.lineStyle(2, 0x1b5e20, 1).strokeRect(0, 0, boxSize, boxSize);
        g.generateTexture("boxTexture", boxSize, boxSize);
        g.destroy();

        this.box = this.add.image(0, 0, "boxTexture").setOrigin(0).setInteractive({ useHandCursor: true });
        this.physics.add.existing(this.box);                  // dynamic body
        this.box.body.setCollideWorldBounds(true);
        this.box.body.setBounce(0);
        this.box.body.setImmovable(false);
        this.box.body.setSize(boxSize, boxSize, false);       // align to origin 0,0

        // World build via config (contour + obstacles)
        this.blocked = new Set();
        this.buildWorld({
            contour: true,
            obstacles: [
                { col: 3, row: 2 },
                { col: 5, row: 5 },
                // ranges for convenience
                { row: 4, colStart: 2, colEnd: 7 }
            ],
            color: 0x888888
        });

        // Initial cell and sync
        this.boxCell = { col: 1, row: 1 };
        this.syncBoxPosition();

        // Input (snap-to-cell)
        this.isDragging = false;
        this.pointerHandler = (pointer) => {
            const cell = this.pointToCell(pointer.worldX, pointer.worldY);
            this.setBoxCell(cell.col, cell.row);
        };
        this.pointerMoveHandler = (pointer) => {
            if (this.isDragging && pointer.isDown) this.pointerHandler(pointer);
        };
        this.pointerUpHandler = (pointer) => {
            if (!this.isDragging) return;
            this.isDragging = false;
            this.pointerHandler(pointer);
        };
        this.keyHandler = (event) => {
            const moves = {
                ArrowLeft: { dx: -1, dy: 0 }, ArrowRight: { dx: 1, dy: 0 },
                ArrowUp: { dx: 0, dy: -1 }, ArrowDown: { dx: 0, dy: 1 },
                KeyA: { dx: -1, dy: 0 }, KeyD: { dx: 1, dy: 0 },
                KeyW: { dx: 0, dy: -1 }, KeyS: { dx: 0, dy: 1 }
            };
            const move = moves[event.code];
            if (move) {
                event.preventDefault();
                this.setBoxCell(this.boxCell.col + move.dx, this.boxCell.row + move.dy);
            }
        };

        // Wire input
        this.box.on("pointerdown", (pointer) => { this.isDragging = true; this.pointerHandler(pointer); });
        this.input.on("pointermove", this.pointerMoveHandler, this);
        this.input.on("pointerup", this.pointerUpHandler, this);
        this.input.on("pointerupoutside", this.pointerUpHandler, this);
        this.input.keyboard.on("keydown", this.keyHandler, this);

        // Cleanup
        this.events.once("destroy", () => {
            this.box.off("pointerdown");
            this.input.off("pointermove", this.pointerMoveHandler, this);
            this.input.off("pointerup", this.pointerUpHandler, this);
            this.input.off("pointerupoutside", this.pointerUpHandler, this);
            this.input.keyboard.off("keydown", this.keyHandler, this);
        });

        EventBus.emit("current-scene-ready", this);
    }

    // World builder: contour + obstacles (cells or ranges)
    buildWorld(config) {
        const { size, ox, oy, cols, rows } = this.grid;
        const color = config.color ?? 0x888888;

        const addBlockedCell = (col, row, colorOverride) => {
            const x = ox + col * size, y = oy + row * size;
            const rect = this.add.rectangle(x, y, size, size, colorOverride ?? color).setOrigin(0);
            this.physics.add.existing(rect, true);     // static body
            this.physics.add.collider(this.box, rect);
            this.blocked.add(`${col},${row}`);
        };

        // Contour walls: outer ring of cells
        if (config.contour) {
            for (let c = 0; c < cols; c++) { addBlockedCell(c, 0); addBlockedCell(c, rows - 1); }
            for (let r = 0; r < rows; r++) { addBlockedCell(0, r); addBlockedCell(cols - 1, r); }
        }

        // Obstacles: support single cells or horizontal ranges
        for (const o of config.obstacles ?? []) {
            if (o.colStart !== undefined && o.colEnd !== undefined && o.row !== undefined) {
                for (let c = o.colStart; c <= o.colEnd; c++) addBlockedCell(c, o.row, color);
            } else if (o.col !== undefined && o.row !== undefined) {
                addBlockedCell(o.col, o.row, color);
            }
        }
    }

    setBoxCell(col, row) {
        const clamped = this.clampCell(col, row);
        const key = `${clamped.col},${clamped.row}`;
        if (this.blocked.has(key)) return;                 // don’t teleport into walls
        if (clamped.col === this.boxCell.col && clamped.row === this.boxCell.row) return;
        this.boxCell = clamped;
        this.syncBoxPosition();
    }

    syncBoxPosition() {
        const { size, ox, oy } = this.grid;
        const x = ox + this.boxCell.col * size;
        const y = oy + this.boxCell.row * size;
        this.box.body.reset(x, y);                         // move physics body precisely
        this.box.setPosition(x, y);                        // keep image in sync
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
}

// Utility: draw grid lines for visualization
function drawGrid(scene, size, ox, oy, w, h, color = 0xffffff, alpha = 0.12) {
    const grid = scene.add.graphics();
    grid.lineStyle(1, color, alpha);
    for (let x = ox; x <= w; x += size) { grid.beginPath(); grid.moveTo(x, oy); grid.lineTo(x, h); grid.strokePath(); }
    for (let y = oy; y <= h; y += size) { grid.beginPath(); grid.moveTo(ox, y); grid.lineTo(w, y); grid.strokePath(); }
    return grid;
}