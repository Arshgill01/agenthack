---
name: HackerRank Orchestrate Claims Audit Dashboard Design System
description: Showa-era Japanese Retro (Neo-Brutalist) aesthetic design system
colors:
  primary: "#c83838"
  neutral-bg: "#f5f2eb"
  neutral-grid: "#e2ded5"
  ink-dark: "#1d2436"
  ink-muted: "#5e6b84"
  retro-green: "#3b6046"
  retro-mustard: "#b58d22"
rounded:
  sm: "4px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  stat-card:
    backgroundColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "24px"
  badge-success:
    backgroundColor: "#e6f4eb"
    textColor: "{colors.retro-green}"
    rounded: "{rounded.sm}"
  badge-danger:
    backgroundColor: "#fdf2f2"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
---

## Overview
This design system implements a Showa-era Japanese Retro (Neo-Brutalist) print aesthetic. It prioritizes physical materiality, highly structured outline grids, offset flat 3D shadows, and mechanical monospaced numeric scales over modern digital gradients or ambient glow styles.

## Colors
The color palette represents warm, traditional, and tactile pigments:
- **Paper Background** (`#f5f2eb`): Textured warm cream mimicking recycled Showa-era print sheets.
- **Ink Dark** (`#1d2436`): Deep charcoal/navy for typography, table rows, and heavy boundaries.
- **Stamp Red** (`#c83838`): Vermilion Japanese lacquer-stamp red used for critical fail states and verified Hanko seals.
- **Sage Green** (`#3b6046`): Soft organic green for successful validation states.
- **Mustard Yellow** (`#b58d22`): Ochre warning tone for minor discrepancies and low confidence flags.

## Typography
Typography is split strictly into mechanical data hierarchies and elegant editorial display titles:
- **Display Headings**: `Playfair Display` serif with a heavy, editorial weight (`font-weight: 900`).
- **Data & Labels**: `Space Mono` monospaced type style for exact counts, identifiers, rates, and parameters.
- **Prose Reading**: `Inter` sans-serif stack optimized for visual justifications and explanation text.

## Elevation
This aesthetic rejects ambient light drop shadows:
- **Flat 3D Shadow**: Blocks use flat offsets of `4px 4px 0px var(--ink-dark)` (increasing to `6px 6px 0px` on hover interactions).
- **Physical Grid Elevation**: Visual separation is established strictly through `2px` and `1px` solid ink boundaries instead of high-blur overlays.

## Components
Common interactive visual blocks:
- **Hanko Verified Seal**: Double-bordered tilted stamp on the top header (`検 査 済 / VERIFIED`).
- **Claims Cards**: Outlined white cards with flat shadows and left border accents corresponding to their match outcomes.
- **Search & Filters**: Outlined input fields with offset flat shadows.
- **Detailed Drawer**: Light background drawers (`#faf9f6`) sliding down with crisp dividers.

## Do's and Don'ts
- **DO** use solid `2px` black outlines and flat offsets.
- **DO** use `Space Mono` for numbers and token values.
- **DON'T** use ambient drop shadows or linear gradient fills.
- **DON'T** use border-radii larger than `4px` for main container blocks.
- **DON'T** pair text with soft background glow filters.
