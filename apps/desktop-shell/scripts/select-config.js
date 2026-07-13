#!/usr/bin/env node
// Copies configs/<target>.json to configs/active.json before packaging, so
// main.js can require a fixed path without needing a runtime env var.
const fs = require('fs');
const path = require('path');

const target = process.argv[2];
if (!target) {
  console.error('Usage: node select-config.js <web-portal|admin-portal>');
  process.exit(1);
}

const src = path.join(__dirname, '..', 'src', 'configs', `${target}.json`);
const dest = path.join(__dirname, '..', 'src', 'configs', 'active.json');

if (!fs.existsSync(src)) {
  console.error(`No such config: ${src}`);
  process.exit(1);
}

fs.copyFileSync(src, dest);
console.log(`Using ${target} config -> ${dest}`);
