// Captures the Teul title-screen town (the splash canvas, in its own native pixels, without the DOM title and
// buttons) from a local build of the game. Usage:
//   TEUL_BIDI=/path/to/teul/scripts/bidi.mjs TEUL_URL=http://127.0.0.1:8765/ OUT=dir node scripts/capture_teul.mjs [look...] [--frames N]
// look = splash@light:season, e.g. rift@night:autumn. Output: OUT/<look>.png (one frame) or OUT/<look>-NN.png (N frames).
import { writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
const { withFirefox } = await import(process.env.TEUL_BIDI);
const base = process.env.TEUL_URL ?? 'http://127.0.0.1:8765/';
const out = process.env.OUT ?? 'capture';
mkdirSync(out, { recursive: true });
const args = process.argv.slice(2);
const fi = args.indexOf('--frames');
const frames = fi >= 0 ? Number(args.splice(fi, 2)[1]) : 1;
const looks = args.length ? args : ['rift@night:autumn'];
const W = Number(process.env.VW ?? 960), H = Number(process.env.VH ?? 450);
await withFirefox(async (page) => {
  await page.viewport(W, H);
  for (const look of looks) {
    const [splash, at] = look.split('@');
    await page.goto(`${base}?lang=en&splash=${splash}&at=${at}`);
    for (let i = 0; i < 60; i++) {
      if (await page.eval(`!!document.querySelector('canvas.splash')`)) break;
      await page.sleep(250);
    }
    await page.sleep(2500);
    for (let f = 0; f < frames; f++) {
      const url = await page.eval(`document.querySelector('canvas.splash').toDataURL('image/png')`);
      const name = frames > 1 ? `${look.replace(/[@:]/g, '_')}-${String(f).padStart(2, '0')}.png` : `${look.replace(/[@:]/g, '_')}.png`;
      writeFileSync(path.join(out, name), Buffer.from(url.split(',')[1], 'base64'));
      if (frames > 1) await page.sleep(Number(process.env.STEP ?? 120));
    }
    console.log('captured', look);
  }
}, { width: W, height: H });
