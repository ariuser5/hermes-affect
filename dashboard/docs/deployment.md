# Dashboard deployment

## Docker integration

The feature will run inside Hermes' existing dashboard process and use its
published port. It must not add a service, sidecar, health check, bind mount, or
host port for the first release.

The opt-in environment setting is:

```yaml
HERMES_AFFECT_DASHBOARD: "${HERMES_AFFECT_DASHBOARD:-0}"
```

The complete enablement conditions are:

1. `hermes-affect` is installed and enabled.
2. Hermes' dashboard is enabled.
3. `HERMES_AFFECT_DASHBOARD=1` is set explicitly.
4. The existing dashboard authentication provider is configured successfully.

The feature reads and, for the narrow authenticated tuning controls, writes
the same `HERMES_AFFECT_STATE_DIR` as the main plugin. It must not modify SOUL
configuration or any session other than the selected exact session.

## Source and artifact installation

Hermes discovers a dashboard extension below the installed plugin checkout:

```text
<hermes-home>/plugins/hermes-affect/dashboard/
```

The source repository contains `manifest.json`, `plugin_api.py`, and the
pre-built `dist/` assets in this directory. Editable browser source remains
under `frontend/src/`; generated assets are rebuilt and reviewed before a
release with `python -m dashboard.tools.build_dashboard`.

## Enable and disable behavior

Enabling the flag requires recreating or restarting the container so both the
dashboard process and browser bundle see one stable setting. After installation
or asset changes, the dashboard may also require its documented plugin rescan
or a restart.

Disabling the flag must make the backend return `404` and prevent the frontend
from registering the Affect tab. Affect processing and persisted state continue
unchanged.

## Validation sequence

1. Validate the projection and endpoint locally with temporary state.
2. Validate the browser bundle and manifest without a running deployment.
3. Smoke-test the pinned Hermes image with the feature disabled.
4. Smoke-test it enabled on loopback or an isolated test instance.
5. Confirm unauthenticated requests are rejected by Hermes.
6. Confirm the existing dashboard port is the only published web port.
7. Confirm only the exact-session `expression_gain` apply/restore routes can
   mutate state and that no excluded fields are exposed.
8. Confirm the retained-session catalog is bounded and exact selection cannot
   cross a sanitized profile/session path collision.
9. Only after explicit authorization, propose and validate the infrastructure
   repository setting on the real deployment.

No Raspberry Pi, SSH, live Compose, or deployment command is authorized by
this document.

## Rollback

Set `HERMES_AFFECT_DASHBOARD=0` and recreate or restart the affected container.
If the entire plugin revision is rolled back, follow the main plugin rollback
procedure while preserving the affect state directory. Dashboard rollback must
not delete state.
