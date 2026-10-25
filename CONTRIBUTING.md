# Contributing

Thanks for taking a look. MattPaint should look and behave like Windows 10 Paint, so reports of
anything that feels different from the real thing are welcome, even small ones.

## Reporting a problem

Open an [issue](https://github.com/nicedreamzapp/MattPaint/issues/new/choose). The things that make
it quick to fix:

- where you ran it: the web version (which URL), or the Mac or Windows desktop app
- your browser and version, or your OS and version for the desktop app
- your device, and whether you used mouse, touch or stylus
- the tool and settings you were using, and what Paint would have done instead
- any errors from the browser console, and a screenshot if it is visual

## Running it locally

There is no build step for the web version. Open `index.html` in a modern browser, or serve it:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

The desktop app lives in `desktop/` and uses Tauri. Build it with `npm ci`, then `npx tauri build`. The
signed Mac build in `desktop/build-mac.sh` needs an Apple Developer ID certificate, so most
changes are easier to make and test in the web version.

## Tests

Add `?test` to the URL (for example `http://localhost:8000/?test`) and the built-in suite in
`test-in-app.js` runs 65 checks against the live page and reports in the corner. For anything the
suite does not cover, walk through the relevant part of
[TESTING-CHECKLIST.md](TESTING-CHECKLIST.md) by hand.

## Pull requests

Small and focused is easiest to review. Keep the web version free of dependencies and build tools.
Say which browsers and devices you tested on. For big changes, open an issue first so we can talk
it through.

Please follow the [code of conduct](CODE_OF_CONDUCT.md).
