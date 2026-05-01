const fs = require('fs');
const { createChart } = require('lightweight-charts');
const { JSDOM } = require('jsdom');

const dom = new JSDOM(`<!DOCTYPE html><div id="container"></div>`);
const window = dom.window;
const document = window.document;

// Mock enough of DOM for LightweightCharts to throw errors or succeed
global.window = window;
global.document = document;
global.navigator = window.navigator;
global.HTMLElement = window.HTMLElement;

// This will just fail because lightweight charts needs a real browser environment
// But maybe we can catch a basic error
