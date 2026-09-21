feature.application = (function () {
  const POLL_INTERVAL_MS = 5000;
  const DEFAULT_PAGE_SIZE = 50;

  function isCurrentRequest(generation, activeGeneration, requestSelection, selection) {
    return (
      generation === activeGeneration &&
      feature.domain.sameSelection(requestSelection, selection)
    );
  }

  function responseMatchesSelection(response, selection) {
    if (!response || response.available !== true || !response.state) return false;
    if (selection.mode === "latest") return true;
    return (
      response.state.profileId === selection.profileId &&
      response.state.sessionId === selection.sessionId
    );
  }

  function useDashboardState(initialResponse) {
    const responsePair = SDK.hooks.useState(initialResponse);
    const response = responsePair[0];
    const setResponse = responsePair[1];
    const selectionPair = SDK.hooks.useState(feature.domain.latestSelection());
    const selection = selectionPair[0];
    const setSelection = selectionPair[1];
    const errorPair = SDK.hooks.useState(false);
    const hasError = errorPair[0];
    const setHasError = errorPair[1];
    const selectedErrorPair = SDK.hooks.useState(null);
    const selectedStateError = selectedErrorPair[0];
    const setSelectedStateError = selectedErrorPair[1];
    const loadingPair = SDK.hooks.useState(false);
    const selectedStateLoading = loadingPair[0];
    const setSelectedStateLoading = loadingPair[1];
    const catalogPair = SDK.hooks.useState({
      items: [],
      limit: DEFAULT_PAGE_SIZE,
      offset: 0,
      hasMore: false,
    });
    const catalog = catalogPair[0];
    const setCatalog = catalogPair[1];
    const catalogLoadingPair = SDK.hooks.useState(false);
    const catalogLoading = catalogLoadingPair[0];
    const setCatalogLoading = catalogLoadingPair[1];
    const catalogErrorPair = SDK.hooks.useState(null);
    const catalogError = catalogErrorPair[0];
    const setCatalogError = catalogErrorPair[1];
    const stateGeneration = SDK.hooks.useRef(0);
    const stateMounted = SDK.hooks.useRef(false);
    const catalogGeneration = SDK.hooks.useRef(0);

    SDK.hooks.useEffect(
      function () {
        let cancelled = false;
        let timer = null;
        const requestSelection = selection;
        const generation = stateGeneration.current + 1;
        stateGeneration.current = generation;

        async function poll() {
          setSelectedStateLoading(true);
          try {
            const raw = await feature.infrastructure.loadState(requestSelection);
            if (
              !cancelled &&
              isCurrentRequest(generation, stateGeneration.current, requestSelection, selection)
            ) {
              const normalized = feature.domain.normalizeResponse(raw);
              setResponse(normalized);
              setHasError(false);
              setSelectedStateError(
                requestSelection.mode === "exact" && !normalized.available
                  ? { kind: "unavailable" }
                  : null
              );
            }
          } catch (_error) {
            if (
              !cancelled &&
              isCurrentRequest(generation, stateGeneration.current, requestSelection, selection)
            ) {
              if (requestSelection.mode === "exact") {
                setSelectedStateError({ kind: "unavailable" });
              } else {
                setHasError(true);
              }
            }
          } finally {
            if (
              !cancelled &&
              isCurrentRequest(generation, stateGeneration.current, requestSelection, selection)
            ) {
              setSelectedStateLoading(false);
              timer = window.setTimeout(poll, POLL_INTERVAL_MS);
            }
          }
        }

        const pollImmediately = requestSelection.mode === "exact" || stateMounted.current;
        stateMounted.current = true;
        if (pollImmediately) {
          poll();
        } else {
          timer = window.setTimeout(poll, POLL_INTERVAL_MS);
        }
        return function () {
          cancelled = true;
          if (timer !== null) window.clearTimeout(timer);
        };
      },
      [selection.mode, selection.profileId, selection.sessionId]
    );

    async function loadCatalogPage(replace) {
      if (!replace && (!catalog.hasMore || catalogLoading)) return;
      const requestId = catalogGeneration.current + 1;
      catalogGeneration.current = requestId;
      const offset = replace ? 0 : catalog.items.length;
      setCatalogLoading(true);
      if (replace) setCatalogError(null);
      try {
        const raw = await feature.infrastructure.loadSessions(DEFAULT_PAGE_SIZE, offset);
        if (requestId !== catalogGeneration.current) return;
        const page = feature.domain.normalizeCatalogResponse(raw);
        setCatalog(function (current) {
          return replace ? page : feature.domain.mergeCatalogPages(current, page);
        });
        setCatalogError(null);
      } catch (_error) {
        if (requestId === catalogGeneration.current) {
          setCatalogError("Session list is temporarily unavailable.");
        }
      } finally {
        if (requestId === catalogGeneration.current) setCatalogLoading(false);
      }
    }

    SDK.hooks.useEffect(function () {
      loadCatalogPage(true);
    }, []);

    function selectSession(summary) {
      setSelection(feature.domain.exactSelection(summary.profileId, summary.sessionId));
      setSelectedStateError(null);
      setHasError(false);
    }

    function returnToLatest() {
      setSelection(feature.domain.latestSelection());
      setResponse({ available: false, state: null });
      setSelectedStateLoading(true);
      setSelectedStateError(null);
      setHasError(false);
    }

    function refreshSessions() {
      return loadCatalogPage(true);
    }

    function loadMoreSessions() {
      return loadCatalogPage(false);
    }

    return {
      response: response,
      hasError: hasError,
      selection: selection,
      sessions: catalog.items,
      catalog: catalog,
      catalogLoading: catalogLoading,
      catalogError: catalogError,
      selectedStateLoading: selectedStateLoading,
      selectedStateError: selectedStateError,
      hasMatchingResponse: responseMatchesSelection(response, selection),
      selectSession: selectSession,
      returnToLatest: returnToLatest,
      refreshSessions: refreshSessions,
      loadMoreSessions: loadMoreSessions,
    };
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

  return {
    useDashboardState: useDashboardState,
    isCurrentRequest: isCurrentRequest,
    responseMatchesSelection: responseMatchesSelection,
    bootstrap: bootstrap,
  };
})();
