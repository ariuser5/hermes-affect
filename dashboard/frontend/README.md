# Dashboard frontend source

Editable browser source lives under `frontend/src/` and produces the IIFE
bundle required by Hermes at `../dist/index.js`. Generated output is committed
for deployment but must not be edited in place.

```text
frontend/src/
├── application/      # non-overlapping polling, cancellation, stale state
├── domain/           # response normalization, bounds, scales, labels
├── infrastructure/   # authenticated Hermes dashboard API client
├── presentation/     # SDK components and theme-aware rendering
└── index.js           # thin conditional registration boundary
```

The source uses the React instance and components supplied by
`window.__HERMES_PLUGIN_SDK__`; it does not bundle React or use unsafe HTML.
The initial API request acts as a preflight: a disabled `404` or another
failure leaves the Affect tab unregistered. Once mounted, the page polls every
five seconds, cancels its timer on unmount, and retains the last valid snapshot
with a stale warning after a refresh failure.

The deterministic build has no Node package dependencies:

```bash
python -m dashboard.tools.build_dashboard
python -m dashboard.tools.build_dashboard --check
node frontend/tests/domain.test.js
node --check dist/index.js
```
