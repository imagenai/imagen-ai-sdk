# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Build (outputs ESM + CJS + .d.ts to dist/)
npm run build

# Watch mode during development
npm run dev

# Run all tests
npm test

# Run a single test file
npx jest tests/client.test.ts

# Run tests with coverage (enforces 80% threshold)
npm run test:coverage

# Type-check without emitting (uses tsconfig.check.json which includes tests/)
npm run typecheck

# Lint
npm run lint
npm run lint:fix

# Format
npm run format
```

## Architecture

This is a dual-format (ESM + CJS) TypeScript SDK for the Imagen AI photo editing API. The build is handled by `tsup`, which bundles both formats from a single entry point (`src/index.ts`).

### Source layout

| File | Purpose |
|------|---------|
| `src/client.ts` | `ImagenClient` class — all HTTP calls and the polling loop |
| `src/models.ts` | Zod schemas + TypeScript types for all API request/response shapes |
| `src/convenience.ts` | Stateless helper functions (`quickEdit`, `getProfiles`, `getProfile`, `checkFilesMatchProfileType`) |
| `src/errors.ts` | Error hierarchy: `ImagenError` → `AuthenticationError`, `ProjectError`, `UploadError`, `DownloadError` |
| `src/enums.ts` | `PhotographyType` and `CropAspectRatio` enums |
| `src/utils.ts` | File extension sets (`RAW_EXTENSIONS`, `JPG_EXTENSIONS`) and filename utilities |

### Key design decisions

**Two-layer API surface.** `ImagenClient` is a low-level stateful class that maps 1:1 to REST endpoints. The `convenience.ts` functions are stateless thin wrappers that instantiate and close a client internally — useful for one-shot scripts. `quickEdit` chains the full workflow (create project → upload → edit → optional export → optional download) in a single call.

**Zod validation on all API responses.** Every HTTP response is parsed through a Zod schema before use. API field names use `snake_case`; schemas transform them to `camelCase` TypeScript types.

**Polling loop in `_waitForCompletion`.** Both `startEditing` and `exportProject` poll `/status` with exponential backoff (starting at `pollIntervalMs`, capped at 60 s, max wait 20 h). Pass `pollIntervalMs: 1` in tests to skip waits.

**Node 18 compatibility constraint.** `AbortSignal.any()` is Node 20.3+ only — the client manually chains abort listeners instead. Keep this in mind when using `AbortSignal`.

**`startEditing` must not send `Content-Type`.** The Imagen edit endpoint rejects requests with a `Content-Type` header — the client explicitly passes `headers: { "Content-Type": "" }` to suppress the default.

**`p-limit` is bundled (not external).** `tsup.config.ts` sets `noExternal: ["p-limit"]` so the ESM-only `p-limit` package is inlined into both output formats.

### TypeScript configuration

There are three tsconfig files:
- `tsconfig.json` — production build config (`NodeNext` module resolution, `src/` only)
- `tsconfig.check.json` — type-check config (includes `src/` and `tests/` together)
- `tsconfig.test.json` — Jest/ts-jest config (CommonJS module mode so Jest can run the tests)

### Testing

Tests live in `tests/`. All HTTP calls are mocked via `global.fetch = jest.fn()`. Mock calls must be ordered to match the exact sequence of `fetch` calls made by the method under test (see `workflow.test.ts` for the full call sequence). Coverage is enforced at 80% lines/functions/branches/statements.
