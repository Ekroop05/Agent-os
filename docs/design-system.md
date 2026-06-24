# Agent OS Design System

This document outlines the foundation of the Agent OS UI, establishing tokens, typography, layout structures, and reusable components. This ensures consistency and accessibility across all new features.

## 1. Design Tokens (`theme.css`)
We use CSS variables attached to `:root` to ensure standard spacing and colors across the app.

### Colors
- **Primary**: `--color-primary` (`#8B5CF6`)
- **Backgrounds**: `--bg-base`, `--bg-surface`, `--bg-surface-hover`
- **Status**: `--status-success` (Green), `--status-warning` (Yellow/Orange), `--status-danger` (Red), `--status-info` (Blue)
- **Text**: `--text-primary`, `--text-secondary`, `--text-tertiary`

### Spacing (8px Grid)
- **Variables**: `--space-4`, `--space-8`, `--space-12`, `--space-16`, `--space-24`, `--space-32`, `--space-48`, `--space-64`
- Always use these variables for margins and paddings to ensure consistent rhythm.

## 2. Typography (`typography.css`)
Uses the `Inter` font stack with specific sizing utility classes.
- `.text-display`: 48px Bold
- `.text-h1`: 36px Bold
- `.text-h2`: 30px Semibold
- `.text-h3`: 24px Semibold
- `.text-body`: 16px Normal
- `.text-caption`: 14px Medium

## 3. UI Components (`frontend/src/components/ui`)
Reusable React components that enforce design rules without containing any business logic.

- **`Button`**: Flexible actions. Variants: `primary`, `secondary`, `ghost`, `danger`.
- **`Card`**: Container with `Card.Header`, `Card.Body`, `Card.Footer`.
- **`StatusPill`**: Indicates states like `running`, `completed`, `failed`. Displays an animated pulsing dot for running states.
- **`ProgressBar`**: Accessible slider for visualizing completion percentages.
- **`Input`**: Form field with built-in accessibility labeling and focus states.
- **`Modal`**: Base accessible dialog wrapper with Escape key listener and body scroll lock.
- **`Tooltip`**: Hover-accessible helper text.
- **`Loader`**: Minimal CSS spinner.
- **`EmptyState`**: Layout for "no data found" views.

## 4. Layout Foundation (`frontend/src/layout`)
Base structural wrappers used to build out app pages consistently.

- **`AppShell`**: Outermost layout container.
- **`Sidebar`**: Left-side navigation wrapper.
- **`Topbar`**: Top navigation header.
- **`ContentContainer`**: Main page content area with optional max-width constraints.

## 5. Accessibility Standards
- All inputs have associated `<label>`s or `aria-labels`.
- All interactive elements possess distinct `:focus-visible` or `:focus` states using `--shadow-focus`.
- Modals restrict interaction outside of their bounding box and handle keyboard `Escape` closing.
- Screen-reader only classes (`.sr-only`) are utilized in loaders.

## Usage Example
```jsx
import { Button, Card, StatusPill } from '../components/ui';

function Example() {
  return (
    <Card>
      <Card.Header>
        <h3 className="text-h3">Agent Status</h3>
      </Card.Header>
      <Card.Body>
        <StatusPill status="running" />
        <p className="text-body" style={{ marginTop: 'var(--space-16)' }}>
          The agent is currently processing tasks.
        </p>
      </Card.Body>
      <Card.Footer>
        <Button variant="danger">Stop Agent</Button>
      </Card.Footer>
    </Card>
  );
}
```
