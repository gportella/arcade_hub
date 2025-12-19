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

        const addCell = (col, row, c) => {
            const pos = this.toXY(col, row);
            const rect = this.scene.add.rectangle(pos.x, pos.y, this.grid.size, this.grid.size, c || color).setOrigin(0);
            this.scene.physics.add.existing(rect, true); // static
            this.obstacles.push(rect);
            this.blocked.add(`${col},${row}`);
        };

        // Contour (outer ring)
        if (config.contour) {
            for (let c = 0; c < this.grid.cols; c++) { addCell(c, 0); addCell(c, this.grid.rows - 1); }
            for (let r = 0; r < this.grid.rows; r++) { addCell(0, r); addCell(this.grid.cols - 1, r); }
        }

        // Obstacles: single cells or horizontal ranges
        (config.obstacles || []).forEach(o => {
            if (o.colStart != null && o.colEnd != null && o.row != null) {
                for (let c = o.colStart; c <= o.colEnd; c++) addCell(c, o.row);
            } else if (o.col != null && o.row != null) {
                addCell(o.col, o.row);
            }
        });

        return this;
    }

    isBlocked(col, row) { return this.blocked.has(`${col},${row}`); }
    toXY(col, row) { return { x: this.grid.ox + col * this.grid.size, y: this.grid.oy + row * this.grid.size }; }
    getObstacleObjects() { return this.obstacles; }
}