// @ts-nocheck

import { MainGame } from './scenes/MainGame';
import { AUTO, Game, Scale } from 'phaser';

// Find out more information about the Game Config at:
// https://docs.phaser.io/api-documentation/typedef/types-core#gameconfig
const baseConfig = {
    type: AUTO,
    parent: 'game-container',
    backgroundColor: '#2c2f33',
    scale: {
        mode: Scale.FIT,                 // fit inside available space while preserving aspect
        autoCenter: Scale.CENTER_BOTH,   // center canvas both horizontally and vertically
        width: 1024,
        height: 768
    },
    physics: {
        default: 'arcade',
        arcade: {
            gravity: { y: 0 },
            debug: false
        }
    },
    scene: [MainGame]
};

const StartGame = (parent, width, height) => {
    const resolvedWidth = Number.isFinite(width) && width > 0 ? width : baseConfig.scale.width;
    const resolvedHeight = Number.isFinite(height) && height > 0 ? height : baseConfig.scale.height;
    return new Game({
        ...baseConfig,
        parent,
        scale: {
            ...baseConfig.scale,
            width: resolvedWidth,
            height: resolvedHeight
        }
    });
};

export default StartGame;
