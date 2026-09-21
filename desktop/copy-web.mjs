// Copies the web app into desktop/web for the desktop build, adding desktop.js before app.js.
// Runs before every build (tauri.conf.json beforeBuildCommand), on Mac and Windows alike.
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const out = join(here, 'web');

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });
cpSync(join(root, 'css'), join(out, 'css'), { recursive: true });
cpSync(join(root, 'js'), join(out, 'js'), { recursive: true });
cpSync(join(here, 'desktop.js'), join(out, 'desktop.js'));

let html = readFileSync(join(root, 'index.html'), 'utf8');
const appScript = /<script src="js\/app\.js[^"]*"><\/script>/;
if (!appScript.test(html)) throw new Error('index.html no longer loads js/app.js the way copy-web.mjs expects');
html = html.replace(appScript, (tag) => `<script src="desktop.js"></script>\n    ${tag}`);
writeFileSync(join(out, 'index.html'), html);
console.log('web app copied to', out);
