feature.presentation = (function () {
  const e = SDK.React.createElement;
  const primitives = feature.presentationPrimitives;
  const stateView = feature.presentationStateView;
  const navigator = feature.presentationSessionNavigator;

  function selectionPanel(model) {
    if (model.selectedStateLoading) {
      return e(
        "div",
        { className: "ha-selection-panel", role: "status" },
        e("div", { className: "ha-loading-mark", "aria-hidden": "true" }, "…"),
        e("h2", null, "Loading selected session"),
        e("p", null, "The current layout will update when this exact profile/session snapshot arrives.")
      );
    }
    if (model.selection.mode === "latest" && !model.selectedStateError) {
      return primitives.emptyState();
    }
    if (model.selectedStateError) {
      return e(
        "div",
        { className: "ha-selection-panel", role: "alert" },
        e("div", { className: "ha-empty__icon", "aria-hidden": "true" }, "◇"),
        e("h2", null, "Selected session unavailable"),
        e(
          "p",
          null,
          "This retained state may have been collected or cannot be read. Choose Latest session to continue."
        )
      );
    }
    return primitives.emptyState();
  }

  function createPage(initialResponse) {
    return function AffectDashboardPage() {
      const model = feature.application.useDashboardState(initialResponse);
      const stateContent =
        model.hasMatchingResponse && model.response.state
          ? stateView.renderState(model.response.state, model.hasError)
          : selectionPanel(model);
      return e(
        "div",
        { className: "ha-page" },
        navigator.sessionNavigator(model),
        e("main", { className: "ha-state-column" }, stateContent)
      );
    };
  }

  return { createPage: createPage };
})();
