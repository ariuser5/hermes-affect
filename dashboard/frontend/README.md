# Dashboard frontend source

Editable browser source lives under `frontend/src/` and produces the IIFE
bundle required by Hermes at `../dist/index.js`. Generated output is committed
for deployment but must not be edited in place.

```text
frontend/src/
├── application/      # focused state polling, catalog, and composition
├── domain/           # response normalization, bounds, scales, labels
├── infrastructure/   # authenticated Hermes dashboard API client
├── presentation/     # selector, state view, SDK components, and styles
└── index.js           # thin conditional registration boundary
```

The source uses the React instance and components supplied by
`window.__HERMES_PLUGIN_SDK__`; it does not bundle React or use unsafe HTML.
The initial API request acts as a preflight: a disabled `404` or another
failure leaves the Affect tab unregistered. Once mounted, the page loads a
bounded session catalog and polls the selected state every five seconds. The
presentation exposes a native profile-grouped dropdown above the state view,
with Refresh and Load more controls beside it. It cancels timers and rejects
stale responses when selection changes, while retaining separate catalog and
state errors.

The deterministic build has no Node package dependencies:

```bash
python -m dashboard.tools.build_dashboard
python -m dashboard.tools.build_dashboard --check
node frontend/tests/domain.test.js
node frontend/tests/controller.test.js
node frontend/tests/session_navigator.test.js
node --check dist/index.js
```
