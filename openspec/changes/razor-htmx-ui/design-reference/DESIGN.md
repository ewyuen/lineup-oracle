---
name: Tactical Intelligence Canvas
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#bbcabf'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#86948a'
  outline-variant: '#3c4a42'
  surface-tint: '#4edea3'
  primary: '#4edea3'
  on-primary: '#003824'
  primary-container: '#10b981'
  on-primary-container: '#00422b'
  inverse-primary: '#006c49'
  secondary: '#7bd0ff'
  on-secondary: '#00354a'
  secondary-container: '#00a6e0'
  on-secondary-container: '#00374d'
  tertiary: '#ffb3af'
  on-tertiary: '#650911'
  tertiary-container: '#fc7c78'
  on-tertiary-container: '#711419'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#6ffbbe'
  primary-fixed-dim: '#4edea3'
  on-primary-fixed: '#002113'
  on-primary-fixed-variant: '#005236'
  secondary-fixed: '#c4e7ff'
  secondary-fixed-dim: '#7bd0ff'
  on-secondary-fixed: '#001e2c'
  on-secondary-fixed-variant: '#004c69'
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3af'
  on-tertiary-fixed: '#410005'
  on-tertiary-fixed-variant: '#842225'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
  pitch-deep: '#080D1A'
  pitch-surface: '#0F172A'
  pitch-card: '#1E293B'
  pitch-border: '#334155'
  pitch-line: '#1E3A5F'
  signal-danger: '#EF4444'
  signal-warning: '#F59E0B'
  signal-success: '#10B981'
  provenance-ai: '#8B5CF6'
  provenance-tpl: '#64748B'
  club-hbc: '#38BDF8'
  club-nth: '#F97316'
  club-rav: '#A855F7'
  club-stb: '#EAB308'
  club-smv: '#14B8A6'
  club-wst: '#EC4899'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 2.25rem
    fontWeight: '700'
    lineHeight: 2.75rem
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 1.75rem
    fontWeight: '700'
    lineHeight: 2.25rem
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
  body-lg:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1rem
  data-mono-lg:
    fontFamily: JetBrains Mono
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.02em
  data-mono-md:
    fontFamily: JetBrains Mono
    fontSize: 0.875rem
    fontWeight: '500'
    lineHeight: 1.25rem
  data-mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 0.75rem
    fontWeight: '500'
    lineHeight: 1rem
  badge-provenance:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: '700'
    lineHeight: 0.875rem
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-desktop: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
  space-2xl: 3rem
---

## Brand & Style

This design system expresses high-clarity sports analytics, engineered for fast evaluation under high cognitive load. Designed specifically for a hackathon demonstration setting, the aesthetic blends the precision of an intelligence operations dashboard with the geometric rigor of modern football tactics boards.

### Tone & Personality
- **Analytical & Authoritative:** Cold, rational calculations presented with surgical typographic precision.
- **Calm & Focused:** A muted, dark tactical pitch environment that recedes into the background so data, status badges, and team formations command immediate focus.
- **No-Nonsense & Functional:** Zero decorative clutter, photographic assets, club badges, or branding fluff. Identity is achieved purely through high-contrast micro-typography, precise three-letter club tickers (e.g., `HBC`, `NTH`, `RAV`), and geometric status indicators.

### Visual Style
- **Dark Tactical Canvas:** A layered, low-reflection slate and obsidian field with subtle structural grid borders.
- **Electric Accent Contrast:** A calculated emerald green accent color signals vitality, starter probability, and verified system states without overwhelming the eyes.
- **Dual Visual Modes:**
  - *Analyst Mode:* High data density, monospaced probability indicators (`P(start) 82%`), algorithmic provenance badges (`[AI Model]`, `[Template]`), and bench delta chips.
  - *Fan Mode:* Generous typographic hierarchy, bold player names, squad numbers, and one-sentence natural language rationales formatted for quick scanning.

## Colors

The palette is tuned for high-contrast accessibility (WCAG AAA for text, WCAG AA for structural UI controls) against dark pitch canvas backdrops.

### Surface System
- **`pitch-deep` (`#080D1A`):** The master canvas, viewport background, and structural pitch zone.
- **`pitch-surface` (`#0F172A`):** Tactical panels, fixture picker cards, and control trays.
- **`pitch-card` (`#1E293B`):** Interactive player cards, modal drawers, and dropdown menus.
- **`pitch-border` (`#334155`):** 1px structural framing for tactical zones, cards, and data dividers.

### Signals & Provenance
- **`primary_color_hex` (`#10B981`):** Active pitch green used for high-probability starters, confirmed availability, and active toggle states.
- **`secondary_color_hex` (`#38BDF8`):** Informational blue used for secondary focus elements, active tab outlines, and tactical slot identifiers.
- **`signal-danger` (`#EF4444`):** Flags injuries, red card suspensions, and inline submission errors.
- **`signal-warning` (`#F59E0B`):** Flags fitness doubts and the persistent, non-blocking service degradation alert bar.
- **`provenance-ai` (`#8B5CF6`):** Violet tag highlighting dynamic AI-generated rationale text.
- **`provenance-tpl` (`#64748B`):** Slate tag denoting deterministic rule/template rationale.

### Geometric Club Accents
Clubs are visually represented solely by their 3-letter codes accompanied by a 6px geometric dot token:
- **Harbor City (`HBC`):** `#38BDF8` (Sky)
- **Northmere (`NTH`):** `#F97316` (Amber-Orange)
- **Ravenside (`RAV`):** `#A855F7` (Purple)
- **Stonebridge (`STB`):** `#EAB308` (Yellow)
- **Summit Vale (`SMV`):** `#14B8A6` (Teal)
- **Westbrook (`WST`):** `#EC4899` (Pink)

## Typography

The typography system pairs **Inter** for clean UI hierarchy and human-readable narrative rationales with **JetBrains Mono** for probabilities, formation badges, shirt numbers, and provenance tags.

### Localization Considerations
All card headers, mode toggles, and status badges are engineered to support length variances between English, Spanish (`Español`), and Traditional Chinese (`繁體中文`):
- Action buttons avoid fixed character widths, using minimum tap targets (`min-h-[36px]`, `px-2.5`) with flexible inline layouts.
- Monospaced numerals guarantee alignment across tabular player lists regardless of active system language.
- Plain-language explanation strings in Fan Mode clamp to 2 lines max on mobile with accessible line-height (`1.4 - 1.5`).

## Layout & Spacing

The layout is built for server-rendered **ASP.NET Core Razor Pages** using modular partials updated via **HTMX** fragment swaps.

### Grid Architecture
- **Desktop (1024px+):** A 12-column layout. 
  - Fixture & Team Sidebar / Context Rail: 4 columns.
  - Tactical Starting XI Pitch Canvas: 8 columns.
- **Mobile (<1024px):** Single-column stacked layout with top sticky match selector, vertical scroll pitch representation, and fixed bottom team news input bar.

### Spacing Scale
- `space-xs` (4px): Spacing inside compact micro-buttons, status badge padding.
- `space-sm` (8px): Gaps between tactical row chips, player cards, and action pills.
- `space-md` (12px): Internal card padding, news input padding.
- `space-lg` (20px): Section divisions, spacing between tactical formation tiers (Forwards, Midfielders, Defenders, Keeper).
- `space-xl` (32px): Outer layout container spacing, fixture header gutters.

## Elevation & Depth

This system avoids blurred drop shadows and glossy skeuomorphism in favor of **structural tactical layering** and **low-contrast geometric borders**.

### Depth Hierarchy
1. **Pitch Base Layer (`#080D1A`):** The lowest layer, representing the tactical grass boundaries, etched with subtle pitch line markings (`#1E3A5F`, 1px solid).
2. **Surface Container (`#0F172A`):** Elevated panels for the Fixture Picker rail, Team News Prompt, and Status Tray. Defined by a 1px border (`#334155`).
3. **Interactive Player Card Tier (`#1E293B`):** Interactive cards that rest upon the formation grid. Hover states shift background color to `#27354A` with an accent outline (`#10B981` or `#38BDF8`).
4. **Transient HTMX Swap State:** When an HTMX request updates an element (`.htmx-swapping`), the component transitions down to `opacity: 0.4` with a 150ms ease-out fade, before settling into full opacity with a 100ms emerald pulse border (`#10B981`).
5. **Critical Alert Overlay:** Non-blocking warning banners use a flat surface with high-contrast amber/red left borders (4px solid), remaining anchored at the layout apex.

## Shapes

The design uses a **Soft (Level 1)** geometric standard. This keeps components crisp, tactical, and clean without looking toy-like or purely brutalist.

- **Standard Cards & Modals:** `rounded` (0.25rem / 4px) to `rounded-md` (0.375rem / 6px).
- **Player Card Containers:** 4px radius with 1px border.
- **Tactical Micro-Buttons & Badges:** 4px radius with strict alignment.
- **Probability Pills & Mode Switchers:** Fully rounded pill shapes (`rounded-full`) exclusively used for toggles and categorical indicator badges to differentiate data controls from structural cards.

## Components

### 1. Player Card (`_PlayerCard.cshtml`)
- **Container:** Dark slate surface (`#1E293B`), 1px border (`#334155`), 4px rounded radius. Contains shirt number, full name, probability metric, rationale snippet, and action micro-buttons.
- **Analyst Mode State:**
  - Displays shirt number (`data-mono-md`), player surname (`font-semibold`), and starter metric: `P(start) 82%` in green (`#10B981`) or sub-50% in amber (`#F59E0B`).
  - Provenance Pill: `[AI Model]` (`bg-[#8B5CF6]/15 text-[#A78BFA]`) or `[Template]` (`bg-[#64748B]/20 text-[#94A3B8]`).
  - Bench Replacement Odds: Bottom subtle row showing next best replacement (e.g., `Alt: R. Vance 44%`).
- **Fan Mode State:**
  - Omits probability numbers and provenance pills. Highlights squad number and prominent player name.
  - Plain language explanation: concise, 14px typography (e.g., *"Likely starter: started 4 of the last 5, strong shooting form."*).
- **HTMX Micro-Buttons:**
  - A three-button cluster along the card base: `Injure`, `Suspend`, `Doubt`.
  - Target: Parent row or pitch target via `hx-post="/api/lineup/player-status"` and `hx-swap="outerHTML"`.
  - Minimum tap height: 32px on desktop, 38px on touch devices.
  - Active hover/focus rings match alert colors: Red for Injury/Suspension, Amber for Doubt.

### 2. Tactical Pitch Formation (`_PitchFormation.cshtml`)
- **Structure:** 4 vertical tactical tiers arranged Keeper (bottom), Defenders, Midfielders, Forwards (top).
- **Pitch Backdrop:** Minimalist dark canvas marked by single-pixel center circle and penalty box perimeter lines (`#1E3A5F`).
- **Bench Reserve Strip:** Positioned beneath each tactical row, rendering up to two bench alternatives in muted, semi-transparent cards (`opacity-70`).

### 3. Fixture Selector & Club Toggle (`_FixturePicker.cshtml`)
- **Matchday Selector:** Dropdown / list organized by Matchday with clear club tickers and kick-off timestamps.
- **Favourite Club Indicator:** Geometric star indicator (`★` / `☆`) next to user's saved club. Tapping fires an HTMX patch saving club preference.
- **Club Toggle Tabs:** Dual-tab bar displaying Home vs. Away club tickers (e.g., `HBC` vs `NTH`), accented with the designated club color dot.

### 4. Team News Prompt Bar (`_TeamNewsBar.cshtml`)
- **Input Field:** Monospaced-capable text field with placeholder *"Enter late news (e.g. Harbor City: Ari Crest is out with a hamstring injury)..."*.
- **Submit Button:** High-contrast emerald button with HTMX indicator spinner state (`hx-indicator="#news-spinner"`).
- **Validation Area:** Inline red alert box directly under the input, triggered on parsing failure without wiping the current active pitch lineup.

### 5. Status & Degraded Service Banners
- **Degraded Service Banner (`#F59E0B`):** Non-blocking notification banner anchored at top: *"Live sync degraded: Showing cached analytical model."* Includes a manual refresh button.
- **Error Alert Banner (`#EF4444`):** Fixed message box displayed when an HTMX fragment fails to resolve, retaining the last valid XI on the pitch canvas.