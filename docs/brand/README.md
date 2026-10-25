# QuantNest identity studies

Open [index.html](index.html) directly in a browser. This review page works offline and requires no backend. Concept 07, including the small centre seed, is the approved platform identity. Selecting other concepts here only changes the preview.

Choose a direction, switch between light and dark previews, toggle the gold accent and replay its short introduction. The lower section shows a website header, workspace sidebar, actual 16/24/32/48-pixel symbol sizes and one-colour versions. The download buttons export the selected direction with the preview's current colours.

## Seven directions

1. **Nested Q:** a rounded Q enclosure with an N-shaped counter and diagonal tail. The N is transparent negative space in the exported symbol.
2. **Woven N:** an upright N with diagonal seams. The mark focuses on connected steps and can animate as two assembling sections.
3. **Folded Nest:** three facets form a canopy, enclosure and core. This is an evolution of the folded character in the existing logo.
4. **Nest Current:** an asymmetric, curved ribbon wraps around an off-centre seed and opens into a sweeping Q. Its drawing animation follows the ribbon once, introducing a softer silhouette than the other concepts.
5. **Nest Union:** two matching rounded bands fit together around an open diagonal passage. The balanced, abstract emblem works in one colour; its two halves approach from opposite corners in the animated version.
6. **QuantNest Signature:** a woven-diamond emblem surrounding a seed, paired with a custom mixed-case alphabet. Refined spacing connects Quant and Nest; the Q has a short integrated tail. A gentle gold transition runs across Nest without repeated metallic stripes. The favicon is the independent woven emblem. Turn off Gold accent for a one-colour version.
7. **The Woven Core:** two broad bands form a tilted, softly rounded triangle around a small curved seed. Clear space separates the seed from the perimeter; the removed centre line remains absent. Two small diagonal breaks give the outline its character. It is paired with concept 06's refined lettering. The bands settle from opposite directions as the seed appears. This direction is selected by default for review.

These are original concept geometries for review and refinement.

## Wordmark

The first five concepts share rounded, editable SVG lettering to make their symbols easier to compare. QuantNest Signature and The Woven Core share the refined, wider mixed-case lettering, two-tone colour treatment and integrated Q tail. Neither alphabet depends on fonts. Their compact horizontal logos balance the emblem against the capital-letter height; standalone wordmark files are also included.

## Files

- `brand.js` is the source of truth for mark geometry, custom lettering, animation and SVG export.
- `index.html`, `preview.css` and `preview.js` make the standalone review page.
- `concepts-preview.png` compares all seven directions. The individual `*-preview.png` images show selected concepts in colour on navy, including `woven-core-preview.png`.
- `assets/` contains monochrome SVG symbols, horizontal logos and animated logos, plus the shared wordmark. Signature and Woven Core also include `*-colour-light.svg`, `*-colour-dark.svg` and standalone `*-wordmark-light.svg` / `*-wordmark-dark.svg` files. All have transparent backgrounds.
- `export-assets.mjs` regenerates those static files from `brand.js`:

  ```powershell
  node docs/brand/export-assets.mjs
  ```

Use the preview's download buttons for theme-specific gold versions. Black masters can be recoloured by changing the root SVG's `color`. For inline application use, remove that fixed root colour so `currentColor` inherits from the surrounding component. Gold downloads also set the symbol's fill explicitly.

## Motion and accessibility

Each introduction plays once, finishes in approximately 800 ms and leaves a fully readable static logo. SVG animation uses CSS; it requires no JavaScript at runtime. The preview's Replay button starts a new instance. There is no continuous idle loop.

All logo SVGs have an accessible name. They retain a complete static appearance when animation is disabled. Both the page and animated exports respect `prefers-reduced-motion`. Preview selection uses native radio inputs with keyboard navigation, and theme/replay/download controls have focus indicators.

## Platform integration

`frontend/src/shared/components/BrandLogo.jsx` is shared by the public/authentication header, workspace sidebar and site footer. It selects light or dark SVGs from the existing theme preference. Only the public/authentication header plays the short introduction; the workspace and footer use static artwork. The animated SVGs respect reduced motion.

Approved assets live in `frontend/public/brand/`. To regenerate platform SVGs after editing concept 07, run `node docs/brand/export-assets.mjs --platform`. Without `--platform`, only the concept-review assets change.

The browser icon uses the seed emblem on a navy tile for contrast on either browser theme. `favicon-32.png` is its 32 × 32 raster fallback, and `apple-touch-icon.png` is the 180 × 180 touch icon. `social.png` is the 1200 × 630 raster version of `social.svg`, used for public-page previews. When changing the SVG geometry, re-export these three PNGs at their named sizes too. The frontend build checks that the required platform assets exist.

The original PNG wordmark and favicon have been removed from the application. Historical marketing code in `docs/archive/` is retained as an archive.

## Shared platform loader

`frontend/src/shared/components/ui/global-loader.jsx` provides the one loading identity across routes, panels, tables, charts and actions. Its two emblem bands weave gently around the seed in a 1.8-second CSS loop. Colours follow the existing light/dark brand tokens; reduced motion shows the static emblem. Unlike the logo introduction, this animation runs only while work is pending.

- Use `<GlobalLoader text="Loading results…" />` for page content.
- Use `<GlobalLoader inline text="Loading options…" />` for a compact status.
- Use `<LoaderMark />` inside a busy button or an existing labelled progress status. The mark is decorative; keep an accessible text label and the button's disabled state.

Animation styles live in `frontend/src/index.css`. Keep progress percentages, cancellation controls and error states separate from the loader. Do not add artificial delays, page-blocking overlays for background refreshes, or another spinner component.
