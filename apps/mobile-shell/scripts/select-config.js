#!/usr/bin/env node
// Copies configs/<target>.json to capacitor.config.json before `cap sync`.
// This is what points the native Android/iOS shell at the live
// web-portal / admin-portal site via Capacitor's server.url option --
// same thin-wrapper approach as the desktop shell, so the app always shows
// the current deployed site rather than a bundled, potentially stale copy.
const fs = require('fs');
const path = require('path');

const target = process.argv[2];
if (!target) {
  console.error('Usage: node select-config.js <web-portal|admin-portal>');
  process.exit(1);
}

const src = path.join(__dirname, '..', 'configs', `${target}.json`);
const dest = path.join(__dirname, '..', 'capacitor.config.json');

if (!fs.existsSync(src)) {
  console.error(`No such config: ${src}`);
  process.exit(1);
}

fs.copyFileSync(src, dest);
console.log(`Using ${target} config -> ${dest}`);
