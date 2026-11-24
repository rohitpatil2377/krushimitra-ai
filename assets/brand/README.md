# Brand assets

`logo.svg` — app icon (1024×1024, with background).
`logo-foreground.svg` — same artwork, transparent, for the Android adaptive icon foreground.

## Why these exist

`assets/icon.png` shipped as the **stock Expo template icon**: a blue chevron with the designer's
construction guides (dashed lines, crosshair, circles) still visible. It is placeholder art from
`create-expo-app`, it is blue in a leaf-green app, and it says nothing about farming. It must not
reach the Play Store.

## Design decisions

* **One shape, thick strokes.** The icon has to survive 48 px on a tab bar and a circular Android
  mask. Fine detail disappears at that size.
* **Brand green `#2E7D32`** from `src/constants/colors.ts` — not a new palette.
* **The scan arc is the only "AI" cue.** A sprout alone is every agri app; a sprout being *looked
  at* is this one. No circuit boards, no robots.
* **No text in the icon.** Devanagari at icon size turns to mud, and the launcher prints the app
  name beside it anyway.
* Nothing within 15% of the edge, so the adaptive-icon mask never clips a leaf.

## Converting to the PNGs the app needs

No converter is installed here. Any of these works:

```bash
# option 1 — one-off, no install
npx --yes sharp-cli -i assets/brand/logo.svg -o assets/icon.png resize 1024 1024
npx --yes sharp-cli -i assets/brand/logo-foreground.svg -o assets/android-icon-foreground.png resize 1024 1024
npx --yes sharp-cli -i assets/brand/logo.svg -o assets/splash-icon.png resize 1024 1024
npx --yes sharp-cli -i assets/brand/logo.svg -o assets/favicon.png resize 48 48

# option 2 — system tool
sudo apt install -y librsvg2-bin
rsvg-convert -w 1024 -h 1024 assets/brand/logo.svg -o assets/icon.png
```

`assets/android-icon-background.png` should be a flat `#E6F4FE`… change it to the brand background
`#F4F8F1` to match (`app.json` already sets `adaptiveIcon.backgroundColor`).

After replacing the PNGs, rebuild the APK — icons are baked in at build time.
