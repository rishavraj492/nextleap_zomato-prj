---
name: Nocturne Curated
colors:
  surface: '#151311'
  surface-dim: '#151311'
  surface-bright: '#3c3936'
  surface-container-lowest: '#100e0c'
  surface-container-low: '#1d1b19'
  surface-container: '#221f1d'
  surface-container-high: '#2c2927'
  surface-container-highest: '#373432'
  on-surface: '#e8e1dd'
  on-surface-variant: '#e2bfb5'
  inverse-surface: '#e8e1dd'
  inverse-on-surface: '#33302d'
  outline: '#a98a81'
  outline-variant: '#5a413a'
  surface-tint: '#ffb59f'
  primary: '#ffb59f'
  on-primary: '#5f1600'
  primary-container: '#f56033'
  on-primary-container: '#531200'
  inverse-primary: '#b02f00'
  secondary: '#f3be54'
  on-secondary: '#412d00'
  secondary-container: '#b88922'
  on-secondary-container: '#392700'
  tertiary: '#b9ccb2'
  on-tertiary: '#243422'
  tertiary-container: '#83967e'
  on-tertiary-container: '#1e2e1c'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbd1'
  primary-fixed-dim: '#ffb59f'
  on-primary-fixed: '#3b0a00'
  on-primary-fixed-variant: '#862200'
  secondary-fixed: '#ffdea6'
  secondary-fixed-dim: '#f3be54'
  on-secondary-fixed: '#271900'
  on-secondary-fixed-variant: '#5d4200'
  tertiary-fixed: '#d4e8cd'
  tertiary-fixed-dim: '#b9ccb2'
  on-tertiary-fixed: '#101f0e'
  on-tertiary-fixed-variant: '#3a4b37'
  background: '#151311'
  on-background: '#e8e1dd'
  surface-variant: '#373432'
typography:
  display-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
    letterSpacing: -0.03em
  display-lg-mobile:
    fontFamily: Geist
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 42px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Geist
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: -0.015em
  body-lg:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.005em
  body-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  label-lg:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0em
  label-md:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-caps:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.06em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 3rem
  margin-mobile: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system crafts an intimate, editorial late-night dining guide tailored for nocturnal food explorers in Bengaluru. The aesthetic mirrors the quiet focus of slipping into an understated, dimly lit bistro past midnight: warm, poised, confident, and utterly free of digital noise.

### Design Principles
- **Nocturnal Warmth:** Rather than cold synthetic darks or glaring cyber-neons, the atmosphere is defined by deep bistre tones, smoked charcoal, and incandescent amber points.
- **Text-First Architecture:** By entirely omitting food photography, the system shifts value to precise typographic hierarchy, rigorous editorial summaries, and contextual micro-details (e.g., kitchen closing times, crowd density, signature orders).
- **Subtle Restraint:** Visual depth relies on quiet tonal elevation and fine hairlines rather than heavy drop shadows, decorative cards, or glassy blurs. Interactions should feel deliberate, quiet, and fluid.

## Colors

The palette establishes an authentic low-light environment using warm carbon foundations punctuated by a singular volcanic ember accent and gilded indicators.

### Surface Tones
- **Base Canvas (`#100e0c`):** Deep smoked obsidian ground. Used for page-level backgrounds and low-focus canvases.
- **Raised Surface (`#1a1714`):** Secondary layer for app headers, sticky navigation bars, filter rails, and modal backdrops.
- **Card Surface (`#221e1b`):** The primary container for curated restaurant modules, dropdown panels, and popovers.
- **Hairline / Separator (`#3a332c`):** 1px structural stroke for borders, horizontal rules, and subtle element division.

### Text & Accents
- **Primary Text (`#f6f1ea`):** High-legibility warm linen. Used for headings, primary metadata, and prominent numbers.
- **Muted Text (`#a89f94`):** Smoked taupe. Used for secondary descriptions, timestamps, metadata labels, and inactive states.
- **Accent Ember (`#e8572a`):** Interactive focal point. Applied strictly to primary actions, active segment toggles, focus indicator rings, and selection indicators.
- **Accent Text (`#fff7f2`):** Pure warm chalk, reserved strictly for text resting on top of `#e8572a`.
- **Rating Gold (`#e7b34a`):** Warm bullion gold reserved for review scores, AI recommendation markers, and star icons.
- **Status Sage (`#9caf96`):** Muted botanical green. Conveys "Open late", "Kitchen active", and positive contextual chips.
- **Status Crimson (`#fb7185`):** Soft rose-coral for error alerts, "Kitchen closing soon", and unavailable statuses.

## Typography

The typography uses a unified, precision-engineered geometric sans stack (`Geist` preferred, falling back to `Inter`). Without images to anchor the page, type weights, tracking values, and strict vertical baselines carry the architectural weight.

### Editorial Hierarchy
- **Restaurant Names:** Rendered at `headline-lg` or `headline-md` with strict negative tracking (`-0.02em` to `-0.025em`) and semi-bold weights to mimic premium publication mastheads.
- **AI Synthesis & Editorial Quotes:** Set in `body-lg` with generous line-height (`1.625`) to offer high legibility during late-night screen viewing without eye strain.
- **Categorical & Temporal Badges:** Formatted using `label-caps` (uppercase, tracked +0.06em) to act as visual metadata anchors against darker cards.
- **Numerics & Ratings:** Set using monospaced features or tabular figures where applicable to maintain alignment in tables and ranking lists.

## Layout & Spacing

The layout is structured around an editorial grid designed for reading ease and immediate discovery. Generous breathing room separates recommendation clusters, reinforcing a calm, deliberate vibe.

### Breakpoints & Grid Composition
- **Mobile (< 768px):** Single-column layout. Margin is `1.25rem`, gutters `1rem`. Restaurant cards span full-width to maximize reading area for dishes and timings.
- **Tablet (768px – 1024px):** 6-column grid with `2rem` margins. Cards can span 3 columns for side-by-side comparison, or 6 columns for detailed spotlight picks.
- **Desktop (> 1024px):** 12-column fixed-max content envelope (`1200px`) centered on the `#100e0c` canvas. Lateral margins set to `3rem`. Standard recommendation cards span 6 columns; wide editorial profiles occupy 8 columns flanked by a 4-column contextual sidebar (e.g., interactive map pins, current hours, live vibe meter).

### Rhythm
Components follow strict multi-step pacing: micro-elements within cards (ratings, tags) utilize `space-xs` and `space-sm`, internal card padding is pinned to `space-lg` (`1.5rem`), and section separations leverage `space-xl` (`2.5rem`) to create intentional spatial pauses.

## Elevation & Depth

Depth is established strictly through tonal surface layering and razor-sharp, low-contrast borders. Glassmorphism, blurred sheets, and bright cast shadows are excluded to keep the visual tone muted and grounded.

### Surface Hierarchy
- **Level 0 (Canvas):** `#100e0c` – The infinite background foundation.
- **Level 1 (Dock & Headers):** `#1a1714` – Slightly elevated surfaces that frame the interface, framed with a bottom or top `1px solid #3a332c` border.
- **Level 2 (Editorial Cards & Floating Sheets):** `#221e1b` – Interactive listing elements, delineated by a full `1px solid #3a332c` perimeter.
- **Level 3 (Dropdowns & Modals):** `#221e1b` paired with an ambient shadow: `0 12px 32px -4px rgba(0, 0, 0, 0.65)`, complemented by a lighter hairline stroke (`rgba(246, 241, 234, 0.08)`) to maintain silhouette definition against deep backgrounds.

Hover and focus states subtly shift the border color rather than exploding the card outward: borders brighten from `#3a332c` to `rgba(246, 241, 234, 0.22)` or `#e8572a` for primary triggers.

## Shapes

The interface balances precise structure with subtle softness via corner radiuses calibrated between 12px and 16px.

- **Primary Cards & Modals:** Standardized on `rounded-lg` (`16px / 1rem`). This cushions the card outline without feeling toy-like.
- **Buttons, Inputs & Chips:** Standardized on `rounded` (`8px to 12px / 0.5rem to 0.75rem`), maintaining functional cohesion with inner card elements.
- **Status Indicators & Avatars:** Fully rounded circular geometry (`rounded-full`) for live status blips (e.g., green dot for "Open Now") and numerical counter badges.

## Components

### Buttons
- **Primary:** Solid `#e8572a` fill with `#fff7f2` text. Height is 44px (touch-friendly), font is `label-lg`, radius is 12px. Focus ring is a 2px offset in `#e8572a`. Hover transitions to slightly deepened amber (`#d44a20`).
- **Secondary / Ghost:** Transparent background with a `1px solid #3a332c` boundary and `#f6f1ea` text. On hover, background shifts to `#1a1714` and border shifts to `#a89f94`.
- **Text Link Button:** No border or fill. `#f6f1ea` text with an underline offset of 4px; transitions to `#e8572a` on hover.

### Filter Chips & Tags
- **Filter Chip (Inactive):** Background `#1a1714`, hairline `#3a332c`, text `#a89f94`, radius 8px, padding `0.375rem 0.75rem`.
- **Filter Chip (Active):** Background `#221e1b`, border `#e8572a`, text `#f6f1ea`. A small 6px dot inside is tinted `#e8572a`.
- **Metadata Badge:** Small non-clickable badge (`label-caps`) with `#100e0c` fill and `#3a332c` border. Status-dependent text color (e.g., `#9caf96` for "Kitchen open till 3 AM").

### Recommendation Cards
- Zero imagery. The card structure comprises:
  1. **Header Row:** Restaurant name (`headline-md`), neighborhood indicator, and rating pill (featuring `#e7b34a` star icon with score).
  2. **AI Curated Synopsis:** 2-3 lines of `body-md` in `#f6f1ea` explaining specifically *why* this spot matches the current hour and vibe.
  3. **Editorial Highlights:** Small bulleted list using `#e8572a` dashes (`—`) highlighting must-order items and parking/table reality.
  4. **Footer:** Micro metadata (`body-sm`, `#a89f94`) displaying distance, last order cutoff, and quiet direct-call action.

### Input Fields & Search
- Surface is `#1a1714` with a `1px solid #3a332c` edge. Radius 12px.
- Placeholder text in `#a89f94`.
- Active focus smoothly highlights the border to `#e8572a` with zero outer blur spread, keeping the graphic boundary crisp.

### Rating & Time Sliders
- Track is a continuous 4px bar rendered in `#3a332c`.
- Active filled progress bar rendered in `#e8572a`.
- Thumb handle is a 18px circle in `#f6f1ea` with a subtle inner dot of `#e8572a`.

### Lists & Dividers
- Lists employ alternating row breathing room rather than zebra striping.
- Horizontal dividers are fixed `1px solid #3a332c` with margins aligned to the layout grid.