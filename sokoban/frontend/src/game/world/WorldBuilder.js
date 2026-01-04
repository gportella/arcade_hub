// world/WorldBuilder.js
export class WorldBuilder {
    constructor(scene, grid) {
        this.scene = scene;
        this.grid = grid;
        this.blocked = new Set();       // "col,row"
        this.obstacles = [];            // static bodies
    }

    build(config) {
        const color = config.color || 0x888888;
        const singleTextureKey = typeof config.wallTextureKey === "string" && this.scene.textures?.exists(config.wallTextureKey)
            ? config.wallTextureKey
            : null;
        const arrayTextureKeys = Array.isArray(config.wallTextureKeys)
            ? config.wallTextureKeys.filter(key => this.scene.textures?.exists(key))
            : [];
        const textureChoices = arrayTextureKeys.length > 0
            ? arrayTextureKeys
            : (singleTextureKey ? [singleTextureKey] : []);

        const addCell = (col, row, c) => {
            const key = `${col},${row}`;
            if (this.blocked.has(key)) return;
            const pos = this.toXY(col, row);
            let textureKey = null;
            if (textureChoices.length) {
                const mix = ((col * 73856093) ^ (row * 19349663)) >>> 0;
                textureKey = textureChoices[mix % textureChoices.length];
            }

            const wall = textureKey
                ? this.scene.add.image(pos.x, pos.y, textureKey).setOrigin(0)
                : this.scene.add.rectangle(pos.x, pos.y, this.grid.size, this.grid.size, c || color).setOrigin(0);

            if (textureKey) {
                wall.setDisplaySize(this.grid.size, this.grid.size);
            }

            wall.setDepth(-200);
            this.scene.physics.add.existing(wall, true); // static
            const body = wall.body;
            if (body) {
                body.setSize(this.grid.size, this.grid.size, false);
                body.setOffset(0, 0);
                body.updateFromGameObject?.();
            }
            this.obstacles.push(wall);
            this.blocked.add(key);
        };

        // Contour (outer ring)
        if (config.contour) {
            for (let c = 0; c < this.grid.cols; c++) { addCell(c, 0); addCell(c, this.grid.rows - 1); }
            for (let r = 0; r < this.grid.rows; r++) { addCell(0, r); addCell(this.grid.cols - 1, r); }
        }

        // Obstacles: single cells, horizontal ranges, vertical ranges, or rectangles
        (config.obstacles || []).forEach(o => {
            const hasColRange = o.colStart != null && o.colEnd != null;
            const hasRowRange = o.rowStart != null && o.rowEnd != null;

            if (hasColRange && hasRowRange) {
                for (let c = o.colStart; c <= o.colEnd; c++) {
                    for (let r = o.rowStart; r <= o.rowEnd; r++) addCell(c, r);
                }
            } else if (hasColRange && o.row != null) {
                for (let c = o.colStart; c <= o.colEnd; c++) addCell(c, o.row);
            } else if (hasRowRange && o.col != null) {
                for (let r = o.rowStart; r <= o.rowEnd; r++) addCell(o.col, r);
            } else if (o.col != null && o.row != null) {
                addCell(o.col, o.row);
            }
        });

        if (Array.isArray(config.wallMask)) {
            config.wallMask.forEach((maskRow, row) => {
                if (typeof maskRow !== "string") return;
                for (let col = 0; col < maskRow.length; col++) {
                    const symbol = maskRow[col];
                    if (symbol === "1" || symbol === "#") {
                        addCell(col, row);
                    }
                }
            });
        }

        return this;
    }

    isBlocked(col, row) { return this.blocked.has(`${col},${row}`); }
    toXY(col, row) { return { x: this.grid.ox + col * this.grid.size, y: this.grid.oy + row * this.grid.size }; }
    getObstacleObjects() { return this.obstacles; }

}