// entities/PushableBox.js
export class PushableBox {
    constructor(scene, grid, textureKey = "pushBoxTexture", size = 64, startCell = { col: 4, row: 3 }) {
        this.scene = scene;
        this.grid = grid;
        this.size = size;
        this.cell = { col: startCell.col, row: startCell.row };
        this.tween = null;

        // Simple texture for the pushable box
        if (scene.textures.exists(textureKey)) {
            scene.textures.remove(textureKey);
        }

        const g = scene.add.graphics();
        g.fillStyle(0xffc107, 1).fillRect(0, 0, size, size);
        g.lineStyle(2, 0xff6f00, 1).strokeRect(0, 0, size, size);
        g.generateTexture(textureKey, size, size);
        g.destroy();

        this.sprite = scene.add.image(0, 0, textureKey).setOrigin(0);
        this.setCell(startCell.col, startCell.row);
    }

    setCell(col, row) {
        this.stopTween();
        this.cell.col = col;
        this.cell.row = row;
        const pos = toXY(this.grid, col, row);
        this.sprite.setPosition(pos.x, pos.y);
    }

    isAt(col, row) {
        return this.cell.col === col && this.cell.row === row;
    }

    isMoving() {
        return !!this.tween;
    }

    moveToCell(col, row, speed, onComplete) {
        this.stopTween();
        const pos = toXY(this.grid, col, row);
        const distance = Math.hypot(pos.x - this.sprite.x, pos.y - this.sprite.y);
        const duration = speed > 0 ? (distance / speed) * 1000 : 0;

        this.cell.col = col;
        this.cell.row = row;

        if (duration <= 0) {
            this.sprite.setPosition(pos.x, pos.y);
            if (onComplete) onComplete();
            return;
        }

        this.tween = this.scene.tweens.add({
            targets: this.sprite,
            x: pos.x,
            y: pos.y,
            ease: "Linear",
            duration,
            onComplete: () => {
                this.tween = null;
                if (onComplete) onComplete();
            }
        });
    }

    cancelMove(col, row) {
        this.setCell(col, row);
    }

    stopTween() {
        if (this.tween) {
            this.tween.stop();
            this.tween = null;
        }
    }
}

function toXY(grid, col, row) {
    return { x: grid.ox + col * grid.size, y: grid.oy + row * grid.size };
}