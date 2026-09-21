// MattPaint as a desktop app. The web version saves by "downloading" a picture, prints through
// a pop-up window and can only tell you how to set a wallpaper. Inside the app those become the
// real thing: a Save dialog, the system print dialog, and a wallpaper that is actually set.
// Loaded before js/app.js, only in the desktop build (see copy-web.mjs).
(() => {
    const tauri = window.__TAURI__;
    if (!tauri) return;
    const invoke = tauri.core.invoke;

    // app.js makes a blob: link, clicks it and revokes it straight away. Keep each blob so the
    // click can still read it after the link is revoked.
    const blobs = new Map();
    const createObjectURL = URL.createObjectURL.bind(URL);
    URL.createObjectURL = (obj) => {
        const url = createObjectURL(obj);
        if (obj instanceof Blob) blobs.set(url, obj);
        return url;
    };

    const base64 = (blob) => new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(',')[1] || '');
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
    });

    const nativeAlert = window.alert.bind(window);
    let quietAlert = null;
    window.alert = (msg) => {
        // The web version's "go set it yourself" wallpaper instructions: the app sets it instead.
        if (quietAlert && String(msg).startsWith(quietAlert)) return;
        nativeAlert(msg);
    };

    const anchorClick = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () {
        const blob = this.download && blobs.get(this.href);
        if (!blob) return anchorClick.call(this);
        const name = this.download;
        blobs.delete(this.href);
        const wallpaper = /-wallpaper\.png$/.test(name);
        if (wallpaper) quietAlert = 'Image downloaded. To set as wallpaper';
        base64(blob)
            .then((data) => invoke(wallpaper ? 'set_wallpaper' : 'save_file', { name, data }))
            .then((done) => {
                if (wallpaper && done) nativeAlert('Your picture is now your desktop wallpaper.');
            })
            .catch((err) => nativeAlert((wallpaper ? 'Could not set the wallpaper: ' : 'Could not save: ') + err));
    };

    // Print: app.js writes the picture into a pop-up and prints that. Put it in a part of this
    // page that only shows on paper, and open the system print dialog for this window.
    const nativeOpen = window.open.bind(window);
    window.open = (url, target, features) => {
        if (url) return nativeOpen(url, target, features);
        let html = '';
        return {
            closed: false,
            close() {},
            focus() {},
            document: {
                write(chunk) { html += chunk; },
                close() {
                    const src = (html.match(/<img[^>]+src="([^"]+)"/) || [])[1];
                    if (src) printPicture(src);
                },
            },
        };
    };

    function printPicture(src) {
        let sheet = document.getElementById('desktop-print');
        if (!sheet) {
            sheet = document.createElement('div');
            sheet.id = 'desktop-print';
            document.body.appendChild(sheet);
            const style = document.createElement('style');
            style.textContent = '#desktop-print{display:none}' +
                '@media print{body>*:not(#desktop-print){display:none!important}' +
                '#desktop-print{display:flex;justify-content:center;align-items:center;min-height:100vh}' +
                '#desktop-print img{max-width:100%;height:auto}}';
            document.head.appendChild(style);
        }
        sheet.innerHTML = '';
        const img = document.createElement('img');
        img.onload = () => invoke('print_page').catch((err) => nativeAlert('Could not print: ' + err));
        img.src = src;
        sheet.appendChild(img);
    }

    // File > Exit closes the app.
    window.close = () => { invoke('quit'); };
})();
