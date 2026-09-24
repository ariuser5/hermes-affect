feature.presentationStateView = (function () {
  const e = SDK.React.createElement;
  const primitives = feature.presentationPrimitives;

  function panel(title, content, className) {
    return e(
      "section",
      { className: "ha-panel " + (className || "") },
      e("h2", null, title),
      content
    );
  }

  function stateFacts(state) {
    const facts = [
      ["Atmosphere", feature.domain.formatNumber(state.atmosphere)],
      [
        "Expression drive",
        state.expressionDrive === null ? "—" : feature.domain.formatNumber(state.expressionDrive),
      ],
      ["Model", "v" + state.modelVersion],
      ["Migration", state.migrationRequired ? "Required" : "Current"],
    ];
    return e(
      "dl",
      { className: "ha-fact-list" },
      facts.map(function (fact) {
        return e(
          "div",
          { className: "ha-fact", key: fact[0] },
          e("dt", null, fact[0]),
          e("dd", null, fact[1])
        );
      })
    );
  }

  function conflictList(conflicts) {
    if (!conflicts.length) return e("p", { className: "ha-muted" }, "No open conflicts.");
    return e(
      "ul",
      { className: "ha-compact-list" },
      conflicts.map(function (conflict) {
        return e(
          "li",
          { key: conflict.id },
          e("strong", { title: conflict.id }, conflict.id),
          e("span", null, feature.domain.label(conflict.status)),
          e("span", null, "Heat " + feature.domain.formatNumber(conflict.heat))
        );
      })
    );
  }

  function relationIds(state) {
    return state.relationships.map(function (relation) {
      return relation.id;
    });
  }

  function relationshipDetail(relation) {
    if (!relation) return e("p", { className: "ha-muted" }, "No participant relationships have been recorded.");
    return e(
      "div",
      { className: "ha-relationship-detail" },
      e(
        "div",
        { className: "ha-relationship-detail__heading" },
        e("strong", { title: relation.id }, relation.id),
        primitives.statusBadge(
          relation.tension >= 0.5 ? "Tense" : "Observed",
          relation.tension >= 0.5 ? "warning" : "muted"
        )
      ),
      e(
        "div",
        { className: "ha-relationship-metrics" },
        primitives.metric("Trust", relation.trust, -1, 1, "positive"),
        primitives.metric("Affinity", relation.affinity, -1, 1, "positive"),
        primitives.metric("Respect", relation.respect, -1, 1, "accent"),
        primitives.metric("Irritation", relation.irritation, 0, 1, "danger"),
        primitives.metric("Tension", relation.tension, 0, 1, "warning")
      )
    );
  }

  function RelationshipsSummary(props) {
    const state = props.state;
    const ids = relationIds(state);
    const targetKey = state.profileId + "\u0000" + state.sessionId;
    const relationshipKey = JSON.stringify(ids);
    const initialId = ids.length ? ids[0] : "";
    const selectionPair = SDK.hooks.useState({ targetKey: targetKey, participantId: initialId });
    const selection = selectionPair[0];
    const setSelection = selectionPair[1];
    const storedId = selection.targetKey === targetKey ? selection.participantId : initialId;
    const selectedId = ids.indexOf(storedId) >= 0 ? storedId : initialId;
    const relation = state.relationships.find(function (item) {
      return item.id === selectedId;
    });

    SDK.hooks.useEffect(
      function () {
        setSelection({ targetKey: targetKey, participantId: selectedId });
      },
      [targetKey, relationshipKey]
    );

    return panel(
      "Relationships",
      ids.length
        ? e(
            "div",
            { className: "ha-relationships-summary" },
            e(
              "label",
              { className: "ha-relationship-picker", htmlFor: "ha-state-participant-select" },
              e("span", null, ids.length + " participant" + (ids.length === 1 ? "" : "s")),
              e(
                "select",
                {
                  id: "ha-state-participant-select",
                  value: selectedId,
                  onChange: function (event) {
                    setSelection({ targetKey: targetKey, participantId: event.target.value });
                  },
                },
                state.relationships.map(function (item) {
                  return e("option", { value: item.id, key: item.id }, item.id);
                })
              )
            ),
            relationshipDetail(relation)
          )
        : relationshipDetail(null),
      "ha-panel--relationships"
    );
  }

  function tuningSummary(state) {
    if (!state.tuning.length) return e("p", { className: "ha-muted" }, "No session overrides are active.");
    return e(
      "div",
      { className: "ha-tuning-list" },
      state.tuning.map(function (entry) {
        return e(
          "span",
          { className: "ha-chip ha-chip--muted", key: entry[0] },
          feature.domain.label(entry[0]) + " " + feature.domain.formatNumber(entry[1])
        );
      })
    );
  }

  function StateView(props) {
    const state = props.state;
    return e(
      "div",
      { className: "ha-state-view" },
      props.hasError
        ? e(
            "div",
            { className: "ha-notice", role: "status" },
            "Live refresh is temporarily unavailable. Showing the last valid snapshot."
          )
        : null,
      panel("Session context", stateFacts(state), "ha-panel--facts"),
      e(
        "div",
        { className: "ha-state-grid" },
        panel(
          "Active sensitivities",
          primitives.chips(state.sensitivities, "No active sensitivities.", "accent")
        ),
        panel("Open conflicts", conflictList(state.conflicts))
      ),
      e(
        "div",
        { className: "ha-state-grid ha-state-grid--lower" },
        e(RelationshipsSummary, { state: state }),
        panel("Active tuning", tuningSummary(state))
      )
    );
  }

  return { StateView: StateView, RelationshipsSummary: RelationshipsSummary };
})();
