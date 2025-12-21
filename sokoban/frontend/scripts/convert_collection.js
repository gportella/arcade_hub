import { readFileSync, writeFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const inputPath = path.resolve(__dirname, "../src/game/levels/collection.sok");
const outputPath = path.resolve(__dirname, "../src/game/levels/collection_converted.sok");

const LEVEL_HEADER = "; set=collection name=Collection Maze";
const ID_PREFIX = "collection";
const SYMBOL_MAP = {
    "&": "*", // barrel already on target -> box on target
    "*": "$", // barrel -> pushable box
    "?": " "  // unknown -> empty floor
};

function convertCollection(input) {
    const text = input.replace(/\r\n?/g, "\n");
    const blockPattern = /(?:^|\n)\*{5,}\nMaze:\s*(\d+)([\s\S]*?)(?=(?:\n\*{5,}\n)|$)/g;
    const converted = [];
    let match;

    while ((match = blockPattern.exec(text)) !== null) {
        const mazeIndex = match[1];
        const block = match[2];
        const lengthMatch = block.match(/Length:\s*\d+/);
        if (!lengthMatch) continue;
        const layoutStart = block.indexOf(lengthMatch[0]) + lengthMatch[0].length;
        const rawLayout = block.slice(layoutStart).replace(/^\s*\n/, "");
        const rows = rawLayout.split("\n");

        const cleanedRows = trimTrailingEmpty(rows).map(line => line.replace(/[&*?]/g, ch => SYMBOL_MAP[ch] || ch));
        if (cleanedRows.length === 0) continue;

        const idSuffix = mazeIndex.padStart(2, "0");
        const header = `${LEVEL_HEADER}\n; id=${ID_PREFIX}-${idSuffix}`;
        converted.push(`${header}\n${cleanedRows.join("\n")}`);
    }

    return converted.join("\n\n") + "\n";
}

function trimTrailingEmpty(lines) {
    const cloned = [...lines];
    while (cloned.length > 0 && cloned[cloned.length - 1].trim().length === 0) {
        cloned.pop();
    }
    return cloned;
}

function main() {
    const source = readFileSync(inputPath, "utf8");
    const converted = convertCollection(source);
    writeFileSync(outputPath, converted, "utf8");
    console.log(`Wrote ${outputPath}`);
}

main();
