# Vex Frontend Rules

## Stack
- **React 19** with TypeScript (strict mode)
- **Vite 7** for build/dev
- **Tauri 2** for desktop wrapper
- **CSS Modules** or plain CSS (no CSS-in-JS)
- **No Redux/Zustand** — use React Context + useReducer for global state

## Project Structure
```
vex-app/
├── src/
│   ├── components/       # Reusable UI components
│   ├── hooks/            # Custom React hooks
│   ├── services/         # API clients (tauri invoke / fetch)
│   ├── types/            # TypeScript interfaces
│   ├── utils/            # Pure helper functions
│   ├── App.tsx           # Root component
│   ├── main.tsx          # Entry point
│   └── vite-env.d.ts
├── src-tauri/            # Tauri Rust backend
├── package.json
├── tsconfig.json
├── vite.config.ts
└── .eslintrc.cjs (if exists)
```

## Component Guidelines

### File Organization
- One component per file: `ComponentName.tsx`
- Colocated styles: `ComponentName.css`
- Colocated tests: `ComponentName.test.tsx` (if needed)

### Component Patterns
```tsx
// Functional component with proper typing
interface Props {
  title: string;
  onAction: (id: string) => void;
  optional?: number;
}

export function ComponentName({ title, onAction, optional = 10 }: Props) {
  // Hooks first
  const [state, setState] = useState<SomeType>(initial);

  // Event handlers
  const handleClick = useCallback((id: string) => {
    onAction(id);
  }, [onAction]);

  // Render
  return (
    <div className="component-name">
      <h2>{title}</h2>
      <button onClick={() => handleClick("id")}>Action</button>
    </div>
  );
}
```

### State Management
- **Local state**: `useState` / `useReducer`
- **Shared state**: React Context + `useReducer` (create `StateContext.tsx`)
- **Server state**: Custom hooks (`useReminders`, `useChat`) with `useEffect` + `useState`
- **No external state libraries**

### Props & Types
- Define `Props` interface directly in component file
- Use `type` for unions, `interface` for objects
- **No `any`** — use `unknown` + type guards
- Export types if reused: `export type ComponentProps = Props`

## API Communication

### Tauri Commands
```ts
// src/services/tauri.ts
import { invoke } from '@tauri-apps/api/core';

export async function apiChat(message: string, history: ChatMessage[]) {
  return await invoke<ChatResponse>('chat', { message, history });
}
```

### REST (if needed)
```ts
// src/services/http.ts
const BASE = 'http://127.0.0.1:8000';

export async function fetchHealth() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<HealthResponse>;
}
```

## Styling
- **CSS Modules** preferred: `ComponentName.module.css`
- **CSS Variables** for theming (defined in `:root` in `App.css`)
- **No Tailwind** — vanilla CSS with custom properties
- Mobile-first responsive (but desktop-only Tauri app)

## TypeScript Configuration
- `strict: true` in `tsconfig.json`
- `noUncheckedIndexedAccess: true`
- `exactOptionalPropertyTypes: true`
- Path aliases: `@/*` → `src/*`

## Development Commands
```bash
# Dev server (Vite + Tauri)
cd vex-app && npm run tauri dev

# Type check only
npm run build  # runs tsc && vite build

# Lint (if eslint configured)
npm run lint
```

## Prohibited Patterns
- ❌ Class components
- ❌ `useEffect` without dependency array
- ❌ Inline styles (`style={{}}`) — use CSS classes
- ❌ `any` type (use `unknown` + narrowing)
- ❌ Direct DOM manipulation (use refs sparingly)
- ❌ Prop drilling > 2 levels (use Context)
- ❌ Mutating props or state directly