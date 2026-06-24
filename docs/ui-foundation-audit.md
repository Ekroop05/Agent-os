# UI Foundation Audit

## 1. Existing Styles
- The application currently relies on a single monolithic `index.css` file containing 1995 lines of CSS.
- Styles are applied using raw hex values (e.g., `#07080d`, `#e5eef7`, `#7dd3fc`) and `rgba` alpha layers.
- There is no centralized theming system. Hardcoded colors are scattered throughout the codebase.
- Responsiveness and layout are handled inline within global class definitions rather than reusable utility classes.
- Typography relies on a raw `font-family` stack applied to the `:root` element. There is no formalized typographic scale.
- Animations exist (e.g., `bgShift`, `rotate`, `pulseRoute`, `pulseRunning`), but they are deeply coupled to specific components (like `orbital-core` or `status-pill.running`).

## 2. Existing Components
- There is no formal `components/ui` directory.
- Reusable UI elements (Buttons, Cards, Pills) are currently built ad-hoc inside page-level files or global CSS blocks.
- Buttons use generic `button` tags with `.agent-actions button`, `.inline-form button`, or `.approve-button` classes, lacking a centralized React component.
- The `StatusPill` concept exists via `.status-pill` CSS classes, but not as an abstracted React component.

## 3. Existing Layout Structure
- The `App.jsx` file contains the `AppShell`, `Sidebar`, and main layout elements inline.
- Layout logic is tightly coupled to state management and routing (e.g., `Sidebar` is a functional component inside `App.jsx` or a separate file, but lacks a dedicated structural library).
- Grid systems are manually defined per page (e.g., `.dashboard-grid`, `.workspace-page`, `.stat-grid` with `grid-template-columns`).

## 4. Current Design Inconsistencies
- Lack of standard spacing: Margins and padding use arbitrary pixel values (e.g., `22px 28px`, `14px`, `18px`) rather than a predictable 8px grid.
- Color variations: Similar shades of gray and blue are defined using varying opacity layers and slightly different hex codes (`#0d1b24`, `#10141c`, `#0c111a`).
- Component variance: The same functional element (a button or input) may look slightly different depending on the parent container class.
- Missing Accessibility: Focus states, hover transitions, and ARIA labels are applied inconsistently or omitted entirely.

**Conclusion**: The codebase is ripe for a foundational UI framework using CSS variables, a centralized typography/spacing scale, and reusable React components that can be iteratively swapped in later sprints.
