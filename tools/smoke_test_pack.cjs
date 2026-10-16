// Test both the served preview and the offline Windows-friendly file:// test pack.
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const { execFileSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');
const { chromium: playwright } = require('playwright-core');
const chromium = require('@sparticuz/chromium');
(async () => {
  const root = path.resolve(__dirname, '../artifacts/face-voice-test-pack');
  const support = path.resolve(__dirname, '../.cache/runtime/browser');
  fs.mkdirSync(support, { recursive: true });
  const archive = path.join(support, 'support.tar');
  fs.writeFileSync(archive, zlib.brotliDecompressSync(fs.readFileSync(path.join(__dirname, 'node_modules/@sparticuz/chromium/bin/al2023.tar.br'))));
  execFileSync('tar', ['-xf', archive, '-C', support]);
  const browser = await playwright.launch({ executablePath: await chromium.executablePath(), args: chromium.args, headless: true,
    env: { ...process.env, LD_LIBRARY_PATH: `${support}/lib:/tmp:${process.env.LD_LIBRARY_PATH || ''}` } });
  const served = process.argv[2] || 'http://127.0.0.1:8080';
  const allowedOrigin = new URL(served).origin;
  const results = [];
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  try {
    for (const url of [served, pathToFileURL(path.join(root, 'index.html')).href]) {
      const page = await context.newPage();
      const errors = [], external = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => { if (/^https?:/.test(request.url()) && !request.url().startsWith(allowedOrigin + '/')) external.push(request.url()); });
      await page.goto(url, { waitUntil: 'networkidle' });
      await page.waitForFunction(() => document.querySelector('#rig').dataset.ready === 'true' && document.querySelector('#rig').width > 100);
      const rest = await page.locator('#rig').screenshot();
      await page.locator('[data-pose="0.85,0,0"]').click();
      const open = await page.locator('#rig').screenshot();
      await page.locator('[data-pose="0.38,1,0"]').click();
      const round = await page.locator('#rig').screenshot();
      await page.locator('[data-pose="0.02,0,1"]').click();
      const closed = await page.locator('#rig').screenshot();
      if (rest.equals(open) || open.equals(round) || round.equals(closed)) throw new Error('Rig pose presets did not change visible geometry');
      const geometry = await page.evaluate(() => {
        const canvas = document.querySelector('#rig'), context = canvas.getContext('webgl2');
        return { ready: canvas.dataset.ready, error: context.getError(), pose: canvas.dataset.pose };
      });
      if (geometry.error !== 0) throw new Error('WebGL error after rig edits');
      for (const id of ['audio-normal', 'audio-closures', 'audio-vowels', 'baseline']) {
        await page.waitForFunction(id => document.getElementById(id).readyState >= 1 && document.getElementById(id).duration > 0, id);
        await page.locator('#' + id).evaluate(async player => { await player.play(); });
        await page.waitForFunction(id => document.getElementById(id).currentTime > 0.15, id);
        await page.locator('#' + id).evaluate(player => player.pause());
      }
      await page.locator('[data-pose="0,0,0"]').click();
      if (url.startsWith('http')) {
        await page.screenshot({ path: path.join(root, 'proof/desktop.png'), fullPage: true });
        await page.setViewportSize({ width: 390, height: 844 });
        await page.screenshot({ path: path.join(root, 'proof/mobile.png'), fullPage: true });
        if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Mobile overflow');
      }
      if (errors.length || external.length) throw new Error(JSON.stringify({ errors, external }));
      results.push({ mode: url.startsWith('file') ? 'offline file' : 'HTTP preview',
        result: 'passed', checks: ['GLB loaded', 'four distinct visible rig poses', 'WebGL has no error', 'three WAVs decoded and played', 'native baseline video played', 'no external network dependency'] });
      await page.close();
    }
  } finally { await browser.close(); }
  fs.writeFileSync(path.join(root, 'proof/browser-check.json'), JSON.stringify(results, null, 2) + '\n');
  console.log('Test pack browser checks passed:', results.map(r => r.mode).join(', '));
})().catch(error => { console.error(error); process.exitCode = 1; });
