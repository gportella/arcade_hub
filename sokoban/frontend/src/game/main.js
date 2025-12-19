// @ts-nocheck

import { MainGame } from './scenes/MainGame';
import { AUTO, Game } from 'phaser';

// Find out more information about the Game Config at:
// https://docs.phaser.io/api-documentation/typedef/types-core#gameconfig
const config = {
    type: AUTO,
    width: 1024,
    height: 768,
    parent: 'game-container',
    backgroundColor: '#2c2f33',
    physics: {
        default: 'arcade',
        arcade: {
            gravity: { y: 0 },
            debug: false
        }
    },
    scene: [MainGame]
};

const StartGame = (parent) => {

    return new Game({ ...config, parent });

}

export default StartGame;
