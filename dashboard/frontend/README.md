# Dashboard frontend source

Editable browser source will live under `frontend/src/` and produce the single
IIFE bundle required by Hermes at `../dist/index.js`. Generated output must not
be edited in place.

The source will mirror the main plugin's separation of concerns:

```text
frontend/src/
├── application/      # polling, cancellation, and page state transitions
├── domain/           # response validation, display scales, and labels
├── infrastructure/   # authenticated Hermes dashboard API client
├── presentation/     # SDK components and theme-aware rendering
└── index.js          # thin Hermes dashboard registration boundary
```

Use the React instance and components supplied by
`window.__HERMES_PLUGIN_SDK__`; do not bundle React. Avoid JSX unless the chosen
deterministic build step clearly improves maintainability. The final bundle
must remain inspectable, small, and compatible with the pinned Hermes image.

Do not create `src/`, `dist/`, a package manifest, or a build tool until the
first implementation phase selects and documents the build approach in
[`../PLAN.md`](../PLAN.md).

