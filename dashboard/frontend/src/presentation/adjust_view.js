feature.presentationAdjustView = (function () {
  const e = SDK.React.createElement;
  const manualControls = feature.presentationManualStateControls;
  const tuningControls = feature.presentationTuningControls;
  const GROUPS = [
    ["affect", "Affect"],
    ["atmosphere", "Atmosphere"],
    ["relationship", "Relationship"],
    ["expression", "Expression"],
  ];

  function expressionContent(model, state) {
    const configuration = state.tuningConfiguration;
    if (!configuration || !configuration.available || !model.tuningTarget) {
      return e("p", { className: "ha-muted", role: "status" }, "Expression tuning is unavailable for this state.");
    }
    return e(tuningControls.TuningControls, { model: model, state: state });
  }

  function groupContent(group, model, state) {
    if (group === "expression") return expressionContent(model, state);
    return e(manualControls.ManualStateControls, {
      key: group,
      group: group,
      model: model,
      state: state,
    });
  }

  function AdjustView(props) {
    const model = props.model;
    const state = props.state;
    const targetKey = state.profileId + "\u0000" + state.sessionId;
    const groupPair = SDK.hooks.useState({ targetKey: targetKey, group: "affect" });
    const savedGroup = groupPair[0];
    const setSavedGroup = groupPair[1];
    const activeGroup = savedGroup.targetKey === targetKey ? savedGroup.group : "affect";

    SDK.hooks.useEffect(
      function () {
        setSavedGroup({ targetKey: targetKey, group: activeGroup });
      },
      [targetKey]
    );

    return e(
      "section",
      { className: "ha-adjust-view", "aria-label": "Adjust selected session" },
      e(
        "div",
        { className: "ha-adjust-groups", role: "group", "aria-label": "Adjustment group" },
        GROUPS.map(function (group) {
          return e(
            "button",
            {
              type: "button",
              key: group[0],
              className: "ha-adjust-groups__button",
              "aria-pressed": activeGroup === group[0],
              onClick: function () {
                setSavedGroup({ targetKey: targetKey, group: group[0] });
              },
            },
            group[1]
          );
        })
      ),
      e(
        "div",
        { className: "ha-adjust-panels" },
        GROUPS.map(function (group) {
          return e(
            "section",
            {
              key: group[0],
              className: "ha-adjust-panel",
              hidden: activeGroup !== group[0],
              "aria-label": group[1] + " controls",
            },
            groupContent(group[0], model, state)
          );
        })
      )
    );
  }

  return { AdjustView: AdjustView };
})();
