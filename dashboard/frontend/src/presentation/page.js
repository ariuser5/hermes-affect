feature.presentation = (function () {
  const e = SDK.React.createElement;
  const primitives = feature.presentationPrimitives;
  const navigator = feature.presentationSessionNavigator;
  const stateSummary = feature.presentationStateSummary;
  const stateView = feature.presentationStateView;
  const adjustView = feature.presentationAdjustView;

  function selectionPanel(model) {
    if (model.selectedStateLoading) {
      return e(
        "div",
        { className: "ha-selection-panel", role: "status" },
        e("h2", null, "Loading selected session"),
        e("p", null, "Waiting for the selected profile/session snapshot.")
      );
    }
    if (model.selection.mode === "latest" && !model.selectedStateError) {
      return primitives.emptyState();
    }
    if (model.selectedStateError) {
      return e(
        "div",
        { className: "ha-selection-panel", role: "alert" },
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

  function currentTargetKey(model) {
    if (model.selection.mode === "exact") {
      return "exact:" + JSON.stringify([model.selection.profileId, model.selection.sessionId]);
    }
    if (model.hasMatchingResponse && model.response && model.response.state) {
      return "latest:" + JSON.stringify([
        model.response.state.profileId,
        model.response.state.sessionId,
      ]);
    }
    return "latest:pending";
  }

  function supportsAdjust(model, state) {
    return Boolean(model.controlsEnabled && model.manualTarget && state && state.modelVersion === 2);
  }

  function changeTabFromKey(event, activeTab, canEdit, chooseTab) {
    const available = canEdit ? ["state", "adjust"] : ["state"];
    let index = available.indexOf(activeTab);
    if (event.key === "ArrowRight") index = (index + 1) % available.length;
    else if (event.key === "ArrowLeft") index = (index - 1 + available.length) % available.length;
    else if (event.key === "Home") index = 0;
    else if (event.key === "End") index = available.length - 1;
    else return;
    event.preventDefault();
    chooseTab(available[index]);
    const buttons = event.currentTarget.parentNode.querySelectorAll('[role="tab"]');
    if (buttons[index]) buttons[index].focus();
  }

  function tabButton(name, label, activeTab, onSelect, onKeyDown) {
    const active = activeTab === name;
    return e(
      "button",
      {
        type: "button",
        role: "tab",
        id: "ha-tab-" + name,
        "aria-controls": "ha-panel-" + name,
        "aria-selected": active,
        tabIndex: active ? 0 : -1,
        onClick: function () {
          onSelect(name);
        },
        onKeyDown: onKeyDown,
      },
      label
    );
  }

  function createPage(initialResponse) {
    return function AffectDashboardPage() {
      const model = feature.application.useDashboardState(initialResponse);
      const hasState = Boolean(model.hasMatchingResponse && model.response && model.response.state);
      const state = hasState ? model.response.state : null;
      const canEdit = supportsAdjust(model, state);
      const targetKey = currentTargetKey(model);
      const tabPair = SDK.hooks.useState({ targetKey: targetKey, tab: "state" });
      const tabState = tabPair[0];
      const setTabState = tabPair[1];
      const activeTab =
        !canEdit || tabState.targetKey !== targetKey ? "state" : tabState.tab;

      SDK.hooks.useEffect(
        function () {
          if (!canEdit || tabState.targetKey !== targetKey) {
            setTabState({ targetKey: targetKey, tab: "state" });
          }
        },
        [targetKey, canEdit]
      );

      function selectTab(tab) {
        if (tab === "adjust" && !canEdit) return;
        setTabState({ targetKey: targetKey, tab: tab });
      }

      function onTabKeyDown(event) {
        changeTabFromKey(event, activeTab, canEdit, selectTab);
      }

      return e(
        "div",
        { className: "ha-page" },
        e(navigator.SessionNavigator, { model: model }),
        e(stateSummary.Summary, { state: state, hasError: model.hasError }),
        e(
          "div",
          { className: "ha-view-tabs", role: "tablist", "aria-label": "Affect dashboard view" },
          tabButton("state", "State", activeTab, selectTab, onTabKeyDown),
          canEdit ? tabButton("adjust", "Adjust", activeTab, selectTab, onTabKeyDown) : null
        ),
        e(
          "main",
          { className: "ha-view-panels" },
          e(
            "section",
            {
              className: "ha-view-panel",
              id: "ha-panel-state",
              role: "tabpanel",
              "aria-labelledby": "ha-tab-state",
              hidden: activeTab !== "state",
              tabIndex: 0,
            },
            hasState
              ? e(stateView.StateView, { state: state, hasError: model.hasError })
              : selectionPanel(model)
          ),
          canEdit
            ? e(
                "section",
                {
                  className: "ha-view-panel",
                  id: "ha-panel-adjust",
                  role: "tabpanel",
                  "aria-labelledby": "ha-tab-adjust",
                  hidden: activeTab !== "adjust",
                  tabIndex: 0,
                },
                e(adjustView.AdjustView, { model: model, state: state })
              )
            : null
        )
      );
    };
  }

  return { createPage: createPage, supportsAdjust: supportsAdjust };
})();
