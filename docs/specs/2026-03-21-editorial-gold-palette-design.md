# Editorial Gold Palette — Design Spec

**Date:** 2026-03-21
**Status:** Approved
**Approach:** Palette picker extension (low-risk preview)

## Overview

Add the Google Stitch "Editorial Ledger" design as a toggleable theme preset in the existing palette picker. Users can switch between the current blue/slate look and the gold/cream editorial look with one click. Zero risk to the current design — click "Default" to restore.

## Source Material

- Google Stitch export: `Gemini Stitch/stitch_return_manager_dashboard.zip`
- Design system: "The Editorial Ledger" — warm gold/cream palette, Newsreader serif headlines, Work Sans body text
- Creative direction: editorial/archival aesthetic, warm neutrals, intentional asymmetry between serif and sans-serif

## Architecture

### New Concept: Theme Presets

A `ThemePreset` combines all CSS token values + font configuration into a single selectable option. This sits above the existing bg/accent palette pickers.

```typescript
interface ThemePreset {
  name: string;
  swatch: string;           // preview color for the button
  // Surfaces
  surface: string;
  surfaceAlt: string;
  card: string;
  cardHover: string;
  zebra: string;
  // Navigation
  nav: string;
  navActive: string;
  navBorder: string;
  // Borders
  border: string;
  borderSubtle: string;
  // Inputs
  input: string;
  inputBorder: string;
  // Text
  tx: string;
  txSecondary: string;
  txMuted: string;
  txOnDark: string;
  // Primary
  primary: string;
  primaryHover: string;
  primarySubtle: string;
  primaryText: string;
  // Accent
  accent: string;
  accentHover: string;
  // Focus
  focusRing: string;
  // Fonts
  fontSans: string;
  fontHeadline: string | null;  // null = no headline font
  themeClass: string | null;    // CSS class to add to <html> (e.g., "theme-editorial")
}
```

### Token Mapping

| Token | Default (Blue/Slate) | Editorial Gold |
|-------|---------------------|----------------|
| `--surface` | `#e2e8f0` | `#f1eee5` |
| `--surface-alt` | `#cbd5e1` | `#e6e2d9` |
| `--card` | `#ffffff` | `#fdf9f0` |
| `--card-hover` | `#f1f5f9` | `#f7f3ea` |
| `--zebra` | `#f1f5f9` | `#f7f3ea` |
| `--nav` | `#1e40af` | `#493800` |
| `--nav-active` | `#2563eb` | `#745b00` |
| `--nav-border` | `#1d4ed8` | `#584400` |
| `--border` | `#94a3b8` | `#d0c5af` |
| `--border-subtle` | `#cbd5e1` | `#e6e2d9` |
| `--input` | `#ffffff` | `#fdf9f0` |
| `--input-border` | `#64748b` | `#7f7663` |
| `--tx` | `#0f172a` | `#1c1c17` |
| `--tx-secondary` | `#334155` | `#4d4635` |
| `--tx-muted` | `#64748b` | `#7f7663` |
| `--tx-on-dark` | `#f1f5f9` | `#fdf9f0` |
| `--primary` | `#2563eb` | `#745b00` |
| `--primary-hover` | `#1d4ed8` | `#584400` |
| `--primary-subtle` | `#dbeafe` | `#ffe08b` |
| `--primary-text` | `#1d4ed8` | `#584400` |
| `--accent` | `#d97706` | `#4259a9` (Stitch tertiary blue-indigo) |
| `--accent-hover` | `#b45309` | `#284190` |
| `--focus-ring` | `#2563eb40` | `#745b0040` |

**Note on accent:** The editorial theme uses the Stitch `tertiary` blue-indigo for `--accent` so it contrasts with the gold primary. A gold primary + gold accent would be indistinguishable.

### Fonts

**Editorial Gold fonts:**
- Headlines (`h1, h2, h3`): Newsreader (serif)
- Body/labels: Work Sans (sans-serif)

**Google Fonts URL (add to `index.html`):**
```html
<link
  href="https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Work+Sans:wght@300;400;500;600;700&display=swap"
  rel="stylesheet"
/>
```

**CSS prerequisite:** Change `body` font-family in `index.css` line 195 from hardcoded font stack to `font-family: var(--font-sans);` so runtime font swaps actually take effect.

**Application:** When editorial theme is active:
- Set `--font-sans` on `:root` to `"Work Sans", "Inter", sans-serif`
- Set `--font-headline` on `:root` to `"Newsreader", Georgia, serif`
- Add `.theme-editorial` class to `<html>`
- CSS rule: `.theme-editorial h1, .theme-editorial h2, .theme-editorial h3 { font-family: var(--font-headline); }`

When default theme is restored:
- Remove `--font-sans` override (falls back to Inter via @theme)
- Remove `--font-headline`
- Remove `.theme-editorial` class

### Hardcoded Blue Classes to Fix

Three places use hardcoded `text-blue-200` for nav text that will look wrong on dark brown nav:

1. `AppShell.tsx:465` — inactive nav tab text
2. `FormEditor.tsx:527` — breadcrumb link
3. `FormEditor.tsx:539` — breadcrumb link

**Fix:** Replace `text-blue-200` with `text-tx-on-dark opacity-70` (or equivalent token-based class). This makes nav text adapt to whatever nav color the theme sets.

### Dark Mode Interaction

When an editorial theme preset is active, dark mode toggle becomes a no-op (the inline styles from the preset have higher specificity than `.dark` class rules). This is acceptable for a preview feature. If editorial dark mode is desired later, we'd add a dark variant to the theme preset.

**Implementation:** When editorial theme is active, the dark mode toggle button should be hidden or disabled to avoid confusion.

## UI Changes

### Palette Picker Dropdown

Add a "Themes" row at the top of the existing palette dropdown:

```
┌─────────────────────────────────┐
│ THEMES                          │
│ [⬜ Default] [🟫 Editorial Gold]│
│                                 │
│ BACKGROUND                      │
│ [Slate] [Blue Mist] [Warm] ... │
│                                 │
│ ACCENT                          │
│ [Blue] [Indigo] [Teal] ...     │
└─────────────────────────────────┘
```

- **Default swatch:** `#2563eb` (current blue)
- **Editorial Gold swatch:** `#745b00` (gold primary)
- Selecting a theme preset overrides bg and accent (dims individual pickers to show they're overridden)
- Selecting "Default" re-enables individual pickers and restores previous bg/accent selections
- Theme selection persisted in `localStorage` key `sherpa-theme-preset`

### Initialization Flow (on page load)

1. Read `sherpa-theme-preset` from localStorage
2. If it contains a preset name (e.g., `"editorial-gold"`): apply full preset, skip bg/accent restore
3. If null or `"default"`: read `sherpa-bg-palette` and `sherpa-accent-palette`, apply as before

This ensures theme preset takes precedence over individual palette selections.

### Restore Behavior

When switching from Editorial Gold back to Default:
- Clear all theme-set inline styles
- Re-apply the user's saved bg/accent palette indices from localStorage
- Re-enable bg/accent pickers in the dropdown

## Files Changed

1. **`client/src/renderer/index.html`** — Add Google Fonts `<link>` for Newsreader + Work Sans
2. **`client/src/renderer/index.css`** — Change body font-family to `var(--font-sans)`, add `.theme-editorial` headline font rule, add `--font-headline` @theme token
3. **`client/src/renderer/components/AppShell.tsx`** — Add `ThemePreset` type, preset data, `applyThemePreset()` / `clearThemePreset()` functions, "Themes" row in palette dropdown UI, hide dark mode toggle when preset active
4. **`client/src/renderer/pages/FormEditor.tsx`** — Replace `text-blue-200` with token-based class (2 instances)

## What Does NOT Change

- Data entry color coding (red/yellow/green) — critical UX convention, untouched
- Success/warning/danger semantic colors — kept as-is
- All React component structure — zero structural changes
- Existing bg/accent palette pickers — still available within default theme

## Testing

- Manual visual verification: toggle between Default and Editorial Gold on Return Manager page
- Verify data entry color coding still works (red/yellow/green)
- Verify dark mode toggle is hidden when editorial theme active
- Verify persistence across page refresh
- Verify "Default" fully restores original look (including previous bg/accent selections)
- Check nav text legibility on both dark blue and dark brown nav backgrounds
