feature.sessionCatalog = (function () {
  const DEFAULT_PAGE_SIZE = 50;

  function useSessionCatalog() {
    const catalogPair = SDK.hooks.useState({
      items: [],
      limit: DEFAULT_PAGE_SIZE,
      offset: 0,
      hasMore: false,
    });
    const catalog = catalogPair[0];
    const setCatalog = catalogPair[1];
    const loadingPair = SDK.hooks.useState(false);
    const catalogLoading = loadingPair[0];
    const setCatalogLoading = loadingPair[1];
    const errorPair = SDK.hooks.useState(null);
    const catalogError = errorPair[0];
    const setCatalogError = errorPair[1];
    const generationRef = SDK.hooks.useRef(0);

    async function loadPage(replace) {
      if (!replace && (!catalog.hasMore || catalogLoading)) return;
      const requestId = generationRef.current + 1;
      generationRef.current = requestId;
      const offset = replace ? 0 : catalog.items.length;
      setCatalogLoading(true);
      if (replace) setCatalogError(null);
      try {
        const raw = await feature.infrastructure.loadSessions(DEFAULT_PAGE_SIZE, offset);
        if (requestId !== generationRef.current) return;
        const page = feature.domain.normalizeCatalogResponse(raw);
        setCatalog(function (current) {
          return replace ? page : feature.domain.mergeCatalogPages(current, page);
        });
        setCatalogError(null);
      } catch (_error) {
        if (requestId === generationRef.current) {
          setCatalogError("Session list is temporarily unavailable.");
        }
      } finally {
        if (requestId === generationRef.current) setCatalogLoading(false);
      }
    }

    SDK.hooks.useEffect(function () {
      loadPage(true);
    }, []);

    return {
      sessions: catalog.items,
      catalog: catalog,
      catalogLoading: catalogLoading,
      catalogError: catalogError,
      refreshSessions: function () {
        return loadPage(true);
      },
      loadMoreSessions: function () {
        return loadPage(false);
      },
    };
  }

  return { useSessionCatalog: useSessionCatalog };
})();
