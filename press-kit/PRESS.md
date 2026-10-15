# MattPaint press kit

Everything here comes from the MattPaint repo (code, README, tests, git history, the GitHub
release). Anything not found in the repo is marked **TODO-VERIFY**.

## Fact sheet

| | |
|---|---|
| **Name** | MattPaint |
| **What it is** | A recreation of Microsoft Paint (Windows 10) for the web, phones and tablets, Mac and Windows |
| **Developer** | Matt Macosko / Nice Dreamz |
| **Platforms** | Any modern browser (Chrome, Edge, Firefox, Safari, including iPhone, iPad and Android). Mac app (Apple Silicon and Intel, macOS 11 or later, signed and notarized). Windows app (Windows 10 and 11). No Linux desktop build. |
| **App Store / Google Play** | **TODO-VERIFY**: no store listing or link exists in the repo. On iOS and Android it runs in the browser today. |
| **Price** | Free. No ads, no in-app purchases, no account. |
| **License** | MIT (open source) |
| **Current version** | Desktop 1.0.0 (`desktop/src-tauri/tauri.conf.json`, release tag `desktop-v1.0.0`) |
| **Built with** | Vanilla JavaScript, HTML5 Canvas and CSS, no dependencies and no build step. About 230 KB of HTML, JS and CSS, unminified. The desktop app uses the open source [Tauri](https://tauri.app) framework. |
| **Tests** | 65 in-page checks (`?test` on the URL). The Windows build runs a save, print and wallpaper self-test in CI before the installer is attached. |
| **Try it** | https://nicedreamzwholesale.com/paint/ (mirror: https://nicedreamzapp.github.io/MattPaint/) |
| **Mac download** | https://github.com/nicedreamzapp/MattPaint/releases/latest/download/MattPaint-mac.zip |
| **Windows download** | https://github.com/nicedreamzapp/MattPaint/releases/latest/download/MattPaint-windows-setup.exe |
| **Source** | https://github.com/nicedreamzapp/MattPaint |
| **Developer page** | https://nicedreamzwholesale.com/software/ |
| **Press contact** | **TODO-VERIFY**: email address for press |
| **Privacy policy** | **TODO-VERIFY**: none in the repo. From the code: no accounts, no analytics, no network requests from the app; pictures stay on the device. |

### Release history

From git history and the one GitHub release. There are no other tags.

| Date | What shipped |
|---|---|
| 2025-12-26 | First release: MattPaint, MS Paint for the web. Emoji icons for tools, brushes and shapes the same day. |
| 2026-08-06 | MIT license and CREDITS.md naming the upstream work |
| 2026-09-07 | Styling and copy updates |
| 2026-09-13 | Live demo, phone layout, favicon, built-in test suite. One top row, fixed View tab, copy and share your picture. Cache-busted assets, status bar spacing on phones, translation prompt turned off. |
| 2026-09-16 to 09-19 | Gen 6 of the painting experiment in `fast/`: scene engine, local model art director, offline painting |
| 2026-09-21 | **Desktop 1.0.0** for Mac and Windows (GitHub release "MattPaint for Mac and Windows 1.0", tag `desktop-v1.0.0`): real Save window, system print dialog, real wallpaper setting |
| 2026-09-27 | README rewrite: what it is, downloads, known limits |

### Assets

All in the repo, paths relative to the repo root.

| File | Size | What |
|---|---|---|
| `screenshot.png` | 1400 x 900 | MattPaint in a desktop browser |
| `screenshot-phone.png` | 390 x 844 | MattPaint on a phone |
| `desktop/icon-1024.png` | 1024 x 1024 | App icon |
| `gallery/_collection.jpg` | 1500 x 1026 | Paintings made stroke by stroke in MattPaint by the `fast/` experiment |

### Credits

MattPaint recreates Microsoft Paint (Microsoft's trademark; MattPaint is not affiliated with
Microsoft). It draws with the browser's HTML5 Canvas. The desktop app shell is
[Tauri](https://tauri.app). The painting experiment in `fast/` runs open-weight Gemma 4 and Qwen
vision models locally with Apple's [MLX](https://github.com/ml-explore/mlx) and
[mlx-vlm](https://github.com/Blaizzy/mlx-vlm), and its finishing pass borrows ideas from Robbie
Tilton's [Compositor](https://robbietilton.com/compositor). Parts of the README were written with
Anthropic's [Claude Code](https://claude.com/claude-code).

## Description, 50 words

MattPaint is Microsoft Paint from Windows 10, rebuilt to run anywhere: in any browser, on phones
and tablets, and as a free Mac and Windows app. Every classic tool is there, from the fill bucket
to the airbrush to the lightning bolt shape. No account, no ads, no tracking. Free and open source.

## Description, 150 words

MattPaint is a recreation of Microsoft Paint from Windows 10 that runs in any browser, on iPhone,
iPad and Android, and as a desktop app for Mac and Windows. The ribbon, palette and status bar sit
where you remember them, and the tools work the way you expect: pencil, nine brushes including
airbrush, crayon and watercolor, fill bucket, eyedropper, text, and every classic shape down to the
heart and the lightning bolt. You can select, crop, rotate, flip, resize, skew and zoom up to 800%,
with 50 steps of undo.

On phones the canvas fits the screen, the ribbon scrolls sideways, and you can share a picture
straight to the share sheet. The desktop app adds a real save window, the system print dialog and a
working Set as desktop background.

It is plain JavaScript and HTML5 Canvas, about 230 KB, with no libraries. No account, no ads, no
tracking. Free, MIT licensed.

## Five feature bullets

- Every classic Paint tool, nine brushes and every shape, including heart and lightning bolt
- Runs in any browser, on phones and tablets, and as a Mac and Windows app
- Select, crop, rotate, flip, resize, skew, zoom to 800%, 50 steps of undo
- Save PNG, JPEG or WebP, print, copy, or share from your phone
- Free and open source, no account, no ads, no tracking

## Pitch email to app reviewers

Subject: Paint from Windows 10, in a browser tab

Hi {name},

The airbrush still sprays dots. I rebuilt Microsoft Paint from Windows 10 so it runs in any
browser, on phones and tablets, and as a Mac and Windows app. Same ribbon, same palette, same fill
bucket, and the lightning bolt shape is in there too.

It's free, there's no account, and it doesn't track anything. The web version is about 230 KB of
plain JavaScript with no libraries.

Try it here: https://nicedreamzwholesale.com/paint/
Mac and Windows downloads and screenshots: https://nicedreamzwholesale.com/software/

Happy to answer anything or send more screenshots.

Matt Macosko
Nice Dreamz

<!-- TODO-VERIFY: confirm nicedreamzwholesale.com/software/ hosts the press kit before sending. -->
