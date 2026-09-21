#!/bin/bash
# Build the Mac download: one app for Apple Silicon and Intel, signed with the Developer ID
# certificate, notarized by Apple and stapled, zipped into dist/MattPaint-mac.zip.
# Needs: Node, Rust with the aarch64 and x86_64 Apple targets, the Developer ID Application
# certificate in the keychain, and an App Store Connect API key for the notary.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.cargo/bin:$PATH"
[ -d node_modules ] || npm install --silent
export APPLE_SIGNING_IDENTITY="$(security find-identity -v -p codesigning | sed -n 's/.*"\(Developer ID Application:[^"]*\)".*/\1/p' | head -1)"
[ -n "$APPLE_SIGNING_IDENTITY" ] || { echo "no Developer ID Application certificate on this Mac" >&2; exit 1; }
export APPLE_API_KEY="${ASC_KEY_ID:-VSXKZZ79TK}"
export APPLE_API_ISSUER="${ASC_ISSUER:-1ab8acba-26d0-4a22-b2e4-96398ed7ade5}"
export APPLE_API_KEY_PATH="$HOME/.appstoreconnect/private_keys/AuthKey_$APPLE_API_KEY.p8"
npx tauri build --target universal-apple-darwin --bundles app
APP="src-tauri/target/universal-apple-darwin/release/bundle/macos/MattPaint.app"
spctl --assess --type execute -vv "$APP"
mkdir -p dist
rm -f dist/MattPaint-mac.zip
ditto -c -k --keepParent "$APP" dist/MattPaint-mac.zip
ls -la dist/MattPaint-mac.zip
