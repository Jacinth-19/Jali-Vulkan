// Optional end-to-end browser smoke test against an already-running local preview.
// Uses the pinned headless Chromium only for testing, never for rendering the face.
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const { execFileSync } = require('node:child_process');
const { chromium: playwright } = require('playwright-core');
const chromium = require('@sparticuz/chromium');
(async () => {
  const support = path.resolve(__dirname, '../.cache/runtime/browser');
  fs.mkdirSync(support, { recursive: true });
  const archive = path.join(support, 'support.tar');
  fs.writeFileSync(archive, zlib.brotliDecompressSync(fs.readFileSync(path.join(__dirname, 'node_modules/@sparticuz/chromium/bin/al2023.tar.br'))));
  execFileSync('tar', ['-xf', archive, '-C', support]);
  const executablePath = await chromium.executablePath();
  const browser = await playwright.launch({ executablePath, args: chromium.args, headless: true,
    env: { ...process.env, LD_LIBRARY_PATH: `${support}/lib:/tmp:${process.env.LD_LIBRARY_PATH || ''}` } });
  let page; let stage = 'new page'; const failedRequests=[];
  try {
    page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => { if(response.status()>=400)failedRequests.push({url:response.url(),status:response.status()}); });
    stage='initial native frame';
    await page.goto(process.argv[2] || 'http://127.0.0.1:8080', { waitUntil: 'networkidle' });
    await page.waitForFunction(() => Number(document.querySelector('#frames').textContent)>0);
    const frameRequests=[];let movieRequests=0;
    page.on('request', request => { if(request.url().includes('/api/live/frame'))frameRequests.push(request.url());if(request.url().endsWith('.mp4'))movieRequests++; });
    stage='initial audio playback';
    await page.locator('#playOverlay').click();
    await page.waitForFunction(() => Number(document.querySelector('#canvas').dataset.audioSeconds)>0.5);
    stage='initial live frame progression';
    await page.waitForFunction(() => Number(document.querySelector('#frames').textContent)>5);
    await page.locator('#playButton').click();
    fs.mkdirSync('artifacts/browser-check', { recursive: true });
    await page.screenshot({ path: 'artifacts/browser-check/desktop.png', fullPage: true });
    await page.locator('#text').fill('Mama. Papa. We will see you soon.');
    stage='generated session playback';
    const previousSession = await page.locator('#canvas').getAttribute('data-session-id');
    await page.locator('#generate').click();
    await page.waitForFunction(previous => document.querySelector('#canvas').dataset.playing==='true' && document.querySelector('#canvas').dataset.sessionId!==previous, previousSession);
    if (await page.locator('#error').isVisible()) throw new Error(await page.locator('#error').textContent());
    await page.waitForFunction(() => Number(document.querySelector('#canvas').dataset.audioSeconds)>0.25);
    // Read presentation telemetry without racing the bounded native frame lock.
    const duration = Number(await page.locator('#canvas').getAttribute('data-duration-seconds'));
    if(!Number.isFinite(duration) || duration<=0)throw new Error('Missing decoded audio duration');
    const halfDuration = duration / 2;
    await page.locator('#playButton').click();
    await page.waitForFunction(() => document.querySelector('#canvas').dataset.playing==='false');
    const paused=await page.locator('#canvas').getAttribute('data-audio-seconds');
    await page.waitForTimeout(250);
    if(Math.abs(Number(await page.locator('#canvas').getAttribute('data-audio-seconds'))-Number(paused))>0.02)throw new Error('Audio clock advanced while paused');
    stage='seek to half duration';
    await page.locator('#seek').evaluate(e=>{e.value=500;e.dispatchEvent(new Event('input'));e.dispatchEvent(new Event('change'));});
    await page.waitForFunction(expected => Math.abs(Number(document.querySelector('#canvas').dataset.frameSeconds)-expected)<0.15, halfDuration);
    if(frameRequests.length<5 || movieRequests)throw new Error('Not a live frame path');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: 'artifacts/browser-check/mobile.png', fullPage: true });
    stage='natural playback end';
    await page.locator('#playButton').click();
    await page.waitForFunction(end => document.querySelector('#canvas').dataset.playing==='false' && Number(document.querySelector('#canvas').dataset.audioSeconds)>=end-0.05, duration);
    await page.waitForTimeout(150);
    if (await page.locator('#error').isVisible()) throw new Error(await page.locator('#error').textContent());
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    if (overflow) throw new Error('Mobile layout overflows horizontally');
    if (errors.length) throw new Error(errors.join('\n'));
    console.log('Browser smoke passed: Web Audio clock, live Vulkan frames, phoneme session generation, pause/seek, no movie playback, and mobile layout.');
  } catch (failure) {
    const state=page ? await page.evaluate(() => ({
      audio:document.querySelector('#canvas')?.dataset.audioSeconds,
      frame:document.querySelector('#canvas')?.dataset.frameSeconds,
      playing:document.querySelector('#canvas')?.dataset.playing,
      error:document.querySelector('#error')?.textContent,
      status:document.querySelector('#sessionState')?.textContent,
      audioContextState:typeof context==='undefined' ? null : context?.state,
      currentTime:typeof context==='undefined' ? null : context?.currentTime
    })).catch(()=>null) : null;
    console.error(JSON.stringify({stage,state,failedRequests:failedRequests.slice(-10)},null,2));
    if(page)await page.screenshot({path:'artifacts/browser-check/failure.png',fullPage:true}).catch(()=>{});
    throw failure;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
