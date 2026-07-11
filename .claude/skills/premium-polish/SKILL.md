---
name: premium-polish
description: Industry-grade visual and UX polish pass for the Murya app (React/Vite frontend). Use when asked to improve the look, make the UI premium/professional, fix visual inconsistencies, or run a design QA pass.
---

# Murya Premium Polish

Design QA + upgrade pass for the Murya frontend. The brand is settled — never invent a new one: **gold-on-obsidian, Arewa geometry, courtly Hausa ("Hausan Zaure") tone**. Vibes (Classic/Royal/Cyberpunk/Academic) re-theme via CSS custom properties (`--dyn-*` tokens); all styling must go through those tokens so every vibe stays coherent.

## Ground rules

1. **Tokens only.** No hardcoded colors in components — use the `dyn-*` Tailwind classes / CSS vars. A hex value in a component is a defect.
2. **Bilingual voice.** UI copy is Hausa-first with English glosses in parentheses, matching existing patterns ("Shigar da umarni (Message input)"). Never English-only for user-facing strings.
3. **Both worlds.** Every change must be checked in at least Classic + one other vibe, and at mobile (375px) + desktop widths. Murya's audience is mobile-heavy (Nigeria/Sahel) — mobile is the primary target, not an afterthought.
4. **A11y is part of premium.** Focus states visible, touch targets ≥44px, `aria-*` on interactive dials/listboxes (existing pattern in Sidebar.tsx), contrast legible on the obsidian ground.
5. **Performance is part of premium.** This app ships to low-end Android on slow networks: no new heavy dependencies, no large images, keep the bundle lean. Check `npm run build` output size before/after.

## The pass

### 1. Inventory & screenshot
Start the dev server (`preview_start` with the `frontend` launch config) or open https://app.murya.ng. Screenshot: welcome state, a conversation with a long streamed reply, sidebar open (all dials expanded), voice-live state, admin/NeuralReview panel, mobile width, and at least two vibes.

### 2. Hunt classes of visual defects
- **Spacing rhythm**: inconsistent gaps between sibling groups; margins fighting flex/grid `gap`.
- **Type hierarchy**: sizes/weights that don't step cleanly; truncation that hides Hausa diacritics (ƙ ɓ ɗ ƴ must never clip).
- **State gaps**: missing hover/active/disabled/loading states; buttons that don't look pressable; playing-audio state unclear.
- **Overflow**: long Hausa words (they run long — "tattaunawarmu"), long streamed replies, tiny screens. Nothing may horizontally scroll the page.
- **Empty/error states**: every fetch that can fail needs a designed failure state in Hausa, not a blank area.
- **Loading**: streaming already has warmup heartbeats — make sure the UI shows a dignified thinking state, not a frozen screen.
- **Motion**: transitions consistent (existing pattern: 200–500ms ease-out); respect `prefers-reduced-motion`.

### 3. Fix, verify, iterate
Fix in source (components/, index.css). After each batch: reload preview, re-screenshot, compare. Typecheck with `npx tsc --noEmit 2>&1 | grep -v "^New folder"`.

### 4. Ship
`npm run build` must succeed with no size regression. Present before/after screenshots to the user. Deploy only with explicit approval: `npx vercel --prod` (aliases to app.murya.ng).

## Key files
- `App.tsx` — root layout, chat flow, voice-live state machine
- `components/Sidebar.tsx` — dials (vibe/speaker/gender), `OptionButton` shared control
- `components/MessageItem.tsx` — chat bubbles, feedback, play-speech, axiom trace
- `components/NeuralReview.tsx` — admin dataset/corrections panel
- `index.css` / Tailwind config — the `--dyn-*` vibe token definitions
