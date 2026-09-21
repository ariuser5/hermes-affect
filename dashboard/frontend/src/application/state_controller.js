feature.application = (function () {
  function useDashboardState(initialResponse) {
    const selectionPair = SDK.hooks.useState(feature.domain.latestSelection());
    const selection = selectionPair[0];
    const setSelection = selectionPair[1];
    const state = feature.statePolling.useSelectedState(initialResponse, selection);
    const catalog = feature.sessionCatalog.useSessionCatalog();

    function selectSession(summary) {
      setSelection(feature.domain.exactSelection(summary.profileId, summary.sessionId));
    }

    function returnToLatest() {
      setSelection(feature.domain.latestSelection());
    }

    return {
      response: state.response,
      hasError: state.hasError,
      selection: selection,
      sessions: catalog.sessions,
      catalog: catalog.catalog,
      catalogLoading: catalog.catalogLoading,
      catalogError: catalog.catalogError,
      selectedStateLoading: state.selectedStateLoading,
      selectedStateError: state.selectedStateError,
      hasMatchingResponse: state.hasMatchingResponse,
      selectSession: selectSession,
      returnToLatest: returnToLatest,
      refreshSessions: catalog.refreshSessions,
      loadMoreSessions: catalog.loadMoreSessions,
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

  return { useDashboardState: useDashboardState, bootstrap: bootstrap };
})();
