# UI design guide (for the implementer)

Written for: Copilot implementing the `razor-htmx-ui` change.

The visual design was made in Google Stitch and is saved in [design-reference/](design-reference/): `DESIGN.md` (colours, type, spacing, components) and five screenshots. It is a **look reference, not a spec**. The mockups show many things our API cannot provide. The specs in `specs/` and the API contract in ARCHITECTURE.md win whenever they disagree with a picture.

Do not copy generated HTML (it loads Tailwind, Google Fonts and an icon font from CDNs). Write plain Razor and one CSS file.

## The screens

| File | Shows | Use it for |
|---|---|---|
| `1-analyst.png` | Analyst page: header, fixture and club toggle, four formation tiers with cards, alternatives strips, news box | Main layout and card in analyst mode |
| `3-fan.png` | Fan mode: same page, no numbers, bigger names, plain sentences | Card in fan mode |
| `4-spanish.png` | Spanish page | Word choices only (see Languages); its layout is the analyst layout |
| `5-degraded.png` | Banner at top, XI kept, red message under the news box | Banner and error placement |
| `2-injury-swap.png` | After an injury: swap banner, audit log, flagged player in reserves | Only the idea that the XI updates in place; most of it is cut |

## What to use

- **Tokens** from `DESIGN.md` as CSS variables: surface and pitch colours, `signal-danger` (injury, suspension, errors), `signal-warning` (doubt, banner), emerald accent for high P(start) and active toggles, slate for the Template badge, violet for the AI badge. Inter for text, JetBrains Mono for numbers, P(start) and badges (system fonts are fine if the font files are not vendored).
- **Layout:** from 1024px two columns (left rail about 4/12: fixture picker, club toggle, news box and message; right about 8/12: the pitch). Below 1024px everything stacks in that order.
- **Pitch:** four tiers, forwards on top, then midfielders, defenders, goalkeeper at the bottom, as rows of cards (CSS flex, faint pitch lines drawn with CSS borders). A tier header with the line name and count ("Forwards, 3").
- **Player card:** shirt number, name, position, explanation, and a row of three buttons Injure, Suspend, Doubt (min height 32px desktop, 38px touch; red ring on injure and suspend, amber on doubt).
  - Analyst: `P(start) 88%`, green, amber below 50%.
  - Fan: no number and no badge, bigger name, the explanation sentence.
- **Alternatives:** a muted strip under each tier listing the API's alternatives for that position (analyst: with percentages; fan: names only). They are per position, not per player.
- **Badge:** one pill for the lineup in analyst mode: "Template" when `llm_used` is false, "AI" when true. Not one per card.
- **Fixture picker:** list ordered by matchday ("Matchday 3: Harbor City vs Northmere"), club toggle (home, away) with a small colour dot per club, and a star to set the favourite club (star marks it in the picker).
- **News box:** text box and a submit button, with an inline red message under it for API errors. A failed submit never clears the pitch.
- **Banner:** a non-blocking amber bar at the top: "Service unavailable. Showing the last lineup." with a Retry button. The XI stays visible.
- **After an injury, suspension or doubt:** swap the new lineup into `#lineup` and write one line in the message area, for example "Ari Crest marked injured; XI updated". Use the `.htmx-swapping` fade from `DESIGN.md`.
- **Mode switch and language selector** in the top bar: Analyst / Fan pill, language dropdown with English, Español, 繁體中文.

## What to leave out (do not build)

These appear in the mockups but the API has no data for them, or the page does not exist.

- Model confidence, "P(overall fit)", latency, engine state, algorithm seed, inference node, stream reliability, queue status, "Live" badge.
- Win, draw and loss probability, projected xG, heatmaps, "Primary Flank Collision", chemistry, "Fan notes", pressing index, coach and style lines.
- Kickoff time, venue, other fixtures strip, the user avatar.
- Sidebar pages Matchday Hub, Model Analytics and Squad Rosters. There is one page.
- The 22-player pitch with both teams and its tabs (the API predicts one club at a time).
- The swap audit log, the "Late News swap" banner, the flagged player in the reserves strip, the "Revert news" button.
- "Cached model", "changes are processed locally" and similar claims in the degraded banner: there is no cache.
- Per-card "Alt:" lines and per-card AI or Template badges.
- Club tickers (HBC, NTH): the API returns full club names, so show those.
- Crests, logos, photos, any `img` element. Club identity is the name plus a colour dot.

Optional and skipped: the fixed bottom news bar on mobile.

## Club colour dots

A small map in the UI project, with a neutral grey for any club not listed:

| Club | Colour |
|---|---|
| Harbor City | `#38BDF8` |
| Northmere | `#F97316` |
| Ravenside | `#A855F7` |
| Stonebridge | `#EAB308` |
| Summit Vale | `#14B8A6` |
| Westbrook | `#EC4899` |

## Languages

All page text (labels, buttons, headings, messages, banner) comes from `.resx` files for en, es and zh-Hant; player explanations are shown as the API returns them. Spanish words seen in the mockup you can reuse: Lesión (Injure), Sanción (Suspend), Duda (Doubt), Alternativas, Delanteros, Mediocampistas, Defensas, Guardameta, P(titular). Write the zh-Hant set yourself in the same style. The Spanish mockup truncates long labels and still has English in places; do not copy that: let labels wrap, avoid fixed widths, and keep every key translated.

## Data on screen

Show only what the API returns: club and player names, shirt number, position, formation, `p_start`, explanation, alternatives, `llm_used`, matchday. The names in the screenshots are placeholders; the real names come from the API (the seeded synthetic roster).

## Order of work

1. Task 1.2: make the ASCII wireframe from screens 1, 3 and 5 and the lists above.
2. Build with stub data first (tests use a stub API), then run once against the real API.
3. Check the page against `3-fan.png` and `5-degraded.png` last; match the structure, not the invented content.
