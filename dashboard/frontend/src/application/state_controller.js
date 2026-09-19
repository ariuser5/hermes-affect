feature.application = (function () {
  const POLL_INTERVAL_MS = 5000;

  function useDashboardState(initialResponse) {
    const statePair = SDK.hooks.useState(initialResponse);
    const response = statePair[0];
    const setResponse = statePair[1];
    const errorPair = SDK.hooks.useState(false);
    const hasError = errorPair[0];
    const setHasError = errorPair[1];

    SDK.hooks.useEffect(function () {
      let cancelled = false;
      let timer = null;

      async function poll() {
        try {
          const raw = await feature.infrastructure.loadState();
          if (!cancelled) {
            setResponse(feature.domain.normalizeResponse(raw));
            setHasError(false);
          }
        } catch (_error) {
          if (!cancelled) setHasError(true);
        } finally {
          if (!cancelled) timer = window.setTimeout(poll, POLL_INTERVAL_MS);
        }
      }

      timer = window.setTimeout(poll, POLL_INTERVAL_MS);
      return function () {
        cancelled = true;
        if (timer !== null) window.clearTimeout(timer);
      };
    }, []);

    return { response: response, hasError: hasError };
  }

  async function bootstrap() {
    try {
      const raw = await feature.infrastructure.loadState();
      const initialResponse = feature.domain.normalizeResponse(raw);
      const Page = feature.presentation.createPage(initialResponse);
      registry.register("hermes-affect", Page);
    } catch (_error) {
      // A disabled feature deliberately returns 404. Remaining unregistered
      // keeps the optional tab out of navigation without leaking details.
      window.console.info("[hermes-affect] dashboard feature is disabled or unavailable");
    }
  }

  return { useDashboardState: useDashboardState, bootstrap: bootstrap };
})();

