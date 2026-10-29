# Design System: BundleGraph Developer Dashboard

## 1. Identity & Personality
- **Product**: BundleGraph — Evidence-Backed Hardware Bundle Engine & Settlement Verifier
- **Audience**: Systems engineers, audio technicians, e-commerce procurement operators, and hackathon judges inspecting deterministic constraint logic.
- **Personality**: Objective, forensic, dense, precise. High information density without visual noise.
- **Visual Reference**: Modern high-density developer dashboards (Linear, Vercel Dashboard, GitHub Actions, Shadcn UI). Flat web component primitives; zero fake hardware skeumorphism or faux knobs.

## 2. Dials (Antislop R-37)
- **ENERGY**: 2 (Structured, high-contrast, functional contrast, no decorative paint or random neon gradients)
- **RHYTHM**: 2 (Predictable modular grid, clean horizontal dividers, deliberate spacing scale, clear tabular alignment)
- **MOTION**: 1 (Fast, functional transitions: 150ms cubic-bezier for hover/focus, no gratuitous floating physics)

## 3. Color Palette (Slate Neutral Primitives)
- **Background Root**: `#030712` (Zinc-950 / Deep Slate ground)
- **Background Sub-surface (Nav/Header)**: `#090d16` (Slate-950)
- **Background Card / Container**: `#0f172a` (Slate-900)
- **Background Card Elevated / Hover**: `#1e293b` (Slate-800)
- **Borders**: 
  - Subtle: `rgba(255, 255, 255, 0.08)` / `#1e293b`
  - Normal: `rgba(255, 255, 255, 0.12)` / `#334155`
  - Focus / Active: `#38bdf8` / `#6366f1`
- **Text**:
  - Primary: `#f8fafc` (Slate-50)
  - Secondary: `#94a3b8` (Slate-400)
  - Muted: `#64748b` (Slate-500)
- **Purposeful Status Accents**:
  - Verified / Success: Emerald (`#10b981`, bg: `rgba(16, 185, 129, 0.1)`, border: `rgba(16, 185, 129, 0.25)`)
  - Warning / Clarification: Amber (`#f59e0b`, bg: `rgba(245, 158, 11, 0.1)`, border: `rgba(245, 158, 11, 0.25)`)
  - Error / Invalidation / Stock Outage: Rose (`#f43f5e`, bg: `rgba(244, 63, 94, 0.1)`, border: `rgba(244, 63, 94, 0.25)`)
  - System / Sandbox / Info: Sky (`#0284c7`, bg: `rgba(2, 132, 199, 0.1)`, border: `rgba(2, 132, 199, 0.25)`)

## 4. Typography & Data
- **Body & Controls**: System Sans (`Inter`, `-apple-system`, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)
- **Data, Hashes, Currency, Rule IDs**: Tabular Monospace (`JetBrains Mono`, `Geist Mono`, `ui-monospace`, Consolas, monospace), with `font-variant-numeric: tabular-nums`
- **Scale**: Strict Tailwind type scale (`text-xs` 12px, `text-sm` 14px, `text-base` 16px, `text-lg` 18px, `text-xl` 20px). No arbitrary font sizes.

## 5. Components & Structure
- **Cards**: Flat containers with 1px border `rgba(255, 255, 255, 0.08)` and `border-radius: 6px`. Header, body, and footer sections separated by clean hairlines.
- **Badges**: Crisp monospace/semi-bold chips with subtle tint and 1px border. No oversized pills.
- **Buttons**: Flat Shadcn-style: `primary` (solid slate-50 on dark, or high-contrast accent), `secondary` (slate-800 outline), `ghost`, `danger` (rose-600).
- **Icons**: Clean geometric SVGs from `lucide-react` (size 14-16px). No emoji icons (no 🎙️, 🔌, ⚡, ⚠️).
- **Tables & Grids**: Dense, border-collapsed, header with subtle uppercase tracking, zebra/hover rows, right-aligned monetary values.
