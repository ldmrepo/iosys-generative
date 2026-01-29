# @iosys/qti-components

QTI 3.0 Assessment Item Component Library - Editor, Viewer, Assessment modes

## Packages

| Package | Description |
|---------|-------------|
| `@iosys/qti-core` | Core types and utilities for QTI/IML |
| `@iosys/qti-ui` | Shared UI components |
| `@iosys/qti-viewer` | Read-only viewer components |
| `@iosys/qti-assessment` | Assessment mode with scoring |
| `@iosys/qti-editor` | ProseMirror-based editor |

## Quick Start

```bash
# Install dependencies
pnpm install

# Build all packages
pnpm build

# Start demo app
pnpm --filter @iosys/qti-demo dev
```

## Usage

```tsx
import { QtiViewer } from '@iosys/qti-viewer'
import { QtiAssessment } from '@iosys/qti-assessment'
import { QtiEditor } from '@iosys/qti-editor'

// Viewer mode - read-only
<QtiViewer item={qtiItem} showAnswer={true} />

// Assessment mode - response input & scoring
<QtiAssessment
  item={qtiItem}
  onSubmit={handleSubmit}
  mode="practice"
/>

// Editor mode - WYSIWYG editing
<QtiEditor
  value={qtiItem}
  onChange={handleChange}
/>
```

## Development

```bash
# Type check all packages
pnpm typecheck

# Format code
pnpm format

# Clean build artifacts
pnpm clean
```

## Tech Stack

- **React 19** + TypeScript 5.7
- **ProseMirror** - Rich text editing
- **Tailwind CSS** - Styling
- **Vite** - Build tool
- **pnpm** - Package manager
- **Turborepo** - Monorepo orchestration
