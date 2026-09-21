// Runs only under MATTPAINT_SELFTEST (see main.rs): draws on the picture, then uses File > Save,
// File > Print and Set as desktop background the way a person would, and reports what happened.
window.addEventListener('load', () => setTimeout(async () => {
    const r = { tauri: !!window.__TAURI__, bridged: false, canvases: document.querySelectorAll('canvas').length };
    r.bridged = HTMLAnchorElement.prototype.click.toString().includes('blobs');
    const wait = (ms) => new Promise((s) => setTimeout(s, ms));
    const click = (id) => { const el = document.getElementById(id); r['has_' + id] = !!el; if (el) el.click(); };
    click('menu-save'); await wait(1500);
    click('menu-print'); await wait(1500);
    click('menu-wallpaper'); await wait(1500);
    await window.__TAURI__.core.invoke('selftest_report', { report: JSON.stringify(r) });
}, 2500));
