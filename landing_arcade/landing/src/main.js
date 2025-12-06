import { mount } from 'svelte';
import './app.css';
import App from './App.svelte';

document.addEventListener('DOMContentLoaded', () => {
    mount(App, {
        target: document.getElementById('app'),
    });
});
