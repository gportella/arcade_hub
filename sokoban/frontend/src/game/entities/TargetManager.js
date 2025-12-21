// entities/TargetManager.js
export class TargetManager {
    constructor(scene, grid, targets = [], textureKey = "targetTexture") {
        this.scene = scene;
        this.grid = grid;
        this.textureKey = textureKey;
        this.targets = [];
        this.targetSet = new Set();
        this.ensureTexture(textureKey, grid.size);
        targets.forEach(({ col, row }) => this.addTarget(col, row));
    }

    ensureTexture(key, size) {
        if (this.scene.textures.exists(key)) return;
        const g = this.scene.add.graphics();
        g.fillStyle(0x8bc34a, 0.3).fillRect(0, 0, size, size);
        g.lineStyle(4, 0x558b2f, 0.9).strokeRect(6, 6, size - 12, size - 12);
        g.generateTexture(key, size, size);
        g.destroy();
    }

    addTarget(col, row) {
        const pos = this.toXY(col, row);
        const sprite = this.scene.add.image(pos.x, pos.y, this.textureKey).setOrigin(0);
        sprite.setDisplaySize(this.grid.size, this.grid.size);
        sprite.setDepth(-1); // ensure targets render beneath the player and boxes
        this.targets.push({ sprite, col, row });
        this.targetSet.add(this.key(col, row));
        return sprite;
    }

    isTarget(col, row) {
        return this.targetSet.has(this.key(col, row));
    }

    areAllOccupied(pushables) {
        if (this.targetSet.size === 0) return false;
        const covered = new Set();
        for (const box of pushables) {
            const { col, row } = box.cell;
            if (!this.isTarget(col, row)) return false;
            covered.add(this.key(col, row));
        }
        return covered.size === this.targetSet.size;
    }

    destroy() {
        this.targets.forEach(({ sprite }) => sprite.destroy());
        this.targets = [];
        this.targetSet.clear();
    }

    key(col, row) {
        return `${col},${row}`;
    }

    toXY(col, row) {
        return { x: this.grid.ox + col * this.grid.size, y: this.grid.oy + row * this.grid.size };
    }
}
