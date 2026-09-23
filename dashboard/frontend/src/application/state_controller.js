feature.application = (function () {
  function useDashboardState(initialResponse) {
    const selectionPair = SDK.hooks.useState(feature.domain.latestSelection());
    const selection = selectionPair[0];
    const setSelection = selectionPair[1];
    const state = feature.statePolling.useSelectedState(initialResponse, selection);
    const catalog = feature.sessionCatalog.useSessionCatalog();
    const tuning = feature.tuningController.useTuningControls(
      selection,
      state.response,
      state.refreshNow
    );
    const manual = feature.manualStateController.useManualStateControls(
      selection,
      state.response,
      state.refreshNow
    );

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
      tuningConfiguration:
        state.response && state.response.state ? state.response.state.tuningConfiguration : null,
      tuningTarget: tuning.target,
      controlsEnabled: Boolean(state.response && state.response.controlsEnabled),
      tuningStatus: tuning.status,
      tuningError: tuning.error,
      applyExpressionGain: tuning.applyExpressionGain,
      restoreExpressionGain: tuning.restoreExpressionGain,
      manualTarget: manual.target,
      manualPending: manual.pending,
      manualResetToken: manual.resetToken,
      manualStatusFor: manual.statusFor,
      applyManualState: manual.apply,
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
