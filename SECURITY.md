# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems.

Report them privately through GitHub: go to the **Security** tab of this repo and click **Report a vulnerability** ([direct link](https://github.com/nicedreamzapp/MattPaint/security/advisories/new)). Only the maintainer sees the report.

Helpful details: what you found, how to reproduce it, which version or commit, whether it affects the web version or the Mac or Windows desktop app, and your browser or OS version.

I aim to reply within 3 days and to ship a fix or a clear plan within 30 days, depending on severity. You will be credited in the advisory unless you ask not to be.

## Supported versions

Fixes go into `main`, the live web version and the latest desktop release. Please update the desktop app before reporting if you are on an older version.

## What matters most here

The parts where a mistake could hurt someone:

- the native commands in `desktop/src-tauri/src/main.rs` (`save_file` and `set_wallpaper` write files and change the desktop wallpaper), and the content security policy in `desktop/src-tauri/tauri.conf.json`
- the desktop release builds: signing and notarizing in `desktop/build-mac.sh`, and the Windows build and release upload in `.github/workflows/desktop-windows.yml`
- opening images from disk or by drag and drop in `js/app.js`
- `fast/engine.py`, which starts a browser with a remote debugging port to drive the canvas
