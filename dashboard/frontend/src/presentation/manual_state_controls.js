feature.presentationManualStateControls = (function () {
  const e = SDK.React.createElement;
  const AFFECT_FIELDS = [
    ["valence", -1, 1],
    ["arousal", 0, 1],
    ["frustration", 0, 1],
    ["offended", 0, 1],
  ];
  const RELATIONSHIP_FIELDS = [
    ["trust", -1, 1],
    ["affinity", -1, 1],
    ["respect", -1, 1],
    ["irritation", 0, 1],
    ["unresolved_tension", 0, 1],
  ];

  function parseDraft(draft, minimum, maximum) {
    if (draft.trim() === "") return null;
    const number = Number(draft);
    return Number.isFinite(number) && number >= minimum && number <= maximum ? number : null;
  }

  function controlIdentity(target, participantId) {
    return [target.profileId, target.sessionId, participantId || ""].join("\u0000");
  }

  function availableParticipant(relationships, selectedId) {
    const exists = relationships.some(function (item) {
      return item.id === selectedId;
    });
    if (exists) return selectedId;
    return relationships.length ? relationships[0].id : "";
  }

  function fieldLabel(field) {
    return field === "unresolved_tension" ? "Unresolved tension" : feature.domain.label(field);
  }

  function fieldControl(props) {
    const inputId = "ha-manual-" + props.scope + "-" + props.field + "-" + props.index;
    const initial = String(props.value);
    const draftPair = SDK.hooks.useState(initial);
    const draft = draftPair[0];
    const setDraft = draftPair[1];
    const feedback = props.model.manualStatusFor(
      props.scope,
      props.field,
      props.participantId
    );
    const parsed = parseDraft(draft, props.minimum, props.maximum);
    const changed = parsed !== null && parsed !== props.value;
    const saving = props.model.manualPending;

    SDK.hooks.useEffect(
      function () {
        setDraft(String(props.value));
      },
      [props.identity, props.model.manualResetToken]
    );

    return e(
      "div",
      { className: "ha-manual-field", key: props.field },
      e(
        "div",
        { className: "ha-manual-field__heading" },
        e("label", { htmlFor: inputId + "-range" }, fieldLabel(props.field)),
        e("span", { className: "ha-muted" }, "Current " + feature.domain.formatNumber(props.value))
      ),
      e(
        "div",
        { className: "ha-manual-field__inputs" },
        e("input", {
          id: inputId + "-range",
          type: "range",
          min: String(props.minimum),
          max: String(props.maximum),
          step: "0.01",
          value: String(parsed === null ? props.value : parsed),
          onChange: function (event) {
            setDraft(event.target.value);
          },
          disabled: saving,
          "aria-label": fieldLabel(props.field) + " slider",
        }),
        e(
          "label",
          { htmlFor: inputId + "-number", className: "ha-manual-field__number-label" },
          e("span", null, "Value"),
          e("input", {
            id: inputId + "-number",
            type: "number",
            min: String(props.minimum),
            max: String(props.maximum),
            step: "0.01",
            value: draft,
            onChange: function (event) {
              setDraft(event.target.value);
            },
            disabled: saving,
            "aria-label": fieldLabel(props.field) + " numeric value",
          })
        )
      ),
      e(
        "div",
        { className: "ha-manual-field__actions" },
        e(
          "button",
          {
            type: "button",
            className: "ha-control-button",
            onClick: function () {
              if (parsed !== null) {
                return props.model.applyManualState(
                  props.scope,
                  props.field,
                  parsed,
                  props.participantId
                );
              }
            },
            disabled: saving || parsed === null || !changed,
          },
          feedback && feedback.status === "saving" ? "Saving…" : "Apply"
        ),
        parsed === null
          ? e("span", { className: "ha-manual-feedback ha-manual-feedback--error", role: "alert" },
              "Enter a number from " + props.minimum + " to " + props.maximum + ".")
          : null,
        feedback && feedback.status === "saved"
          ? e("span", { className: "ha-manual-feedback", role: "status" },
              "Saved for this session.")
          : null,
        feedback && feedback.status === "conflict"
          ? e("span", { className: "ha-manual-feedback ha-manual-feedback--error", role: "alert" },
              "This session changed. The latest values were refreshed; review and apply again.")
          : null,
        feedback && feedback.status === "unavailable"
          ? e("span", { className: "ha-manual-feedback ha-manual-feedback--error", role: "alert" },
              "The selected session or participant is unavailable.")
          : null,
        feedback && feedback.status === "error"
          ? e("span", { className: "ha-manual-feedback ha-manual-feedback--error", role: "alert" },
              feedback.message || "Unable to save this value.")
          : null
      )
    );
  }

  function fieldGroup(title, scope, entries, model, identity, participantId) {
    return e(
      "section",
      { className: "ha-manual-group", key: scope + (participantId || "") },
      e("h3", null, title),
      entries.map(function (entry, index) {
        return e(fieldControl, {
          key: scope + "-" + entry[0] + "-" + (participantId || ""),
          index: scope + "-" + index + "-" + (participantId || "global"),
          scope: scope,
          field: entry[0],
          minimum: entry[1],
          maximum: entry[2],
          value: entry[3],
          participantId: participantId,
          identity: identity,
          model: model,
        });
      })
    );
  }

  function targetHeader(target, state) {
    return e(
      "header",
      { className: "ha-manual-controls__header" },
      e(
        "div",
        null,
        e("div", { className: "ha-kicker" }, "Manual state controls"),
        e("h2", { id: "ha-manual-controls-title" }, "Adjust selected session"),
        e(
          "p",
          { className: "ha-muted" },
          "Each Apply updates one source value after passive decay and affects this session only."
        ),
        e(
          "p",
          { className: "ha-manual-controls__identity" },
          "Profile ",
          e("strong", null, target.profileId),
          " · Session ",
          e("strong", null, target.sessionId)
        )
      ),
      e("span", { className: "ha-tuning-status" }, "Revision " + state.revision)
    );
  }

  function RelationshipControls(props) {
    const state = props.state;
    const model = props.model;
    const target = props.target;
    const pair = SDK.hooks.useState(state.relationships.length ? state.relationships[0].id : "");
    const selectedId = availableParticipant(state.relationships, pair[0]);
    const setSelectedId = pair[1];
    const relationshipKey = JSON.stringify(
      state.relationships.map(function (item) {
        return item.id;
      })
    );
    const identity = controlIdentity(target, selectedId);
    const relation = state.relationships.find(function (item) {
      return item.id === selectedId;
    });

    SDK.hooks.useEffect(
      function () {
        setSelectedId(function (current) {
          return availableParticipant(state.relationships, current);
        });
      },
      [target.profileId, target.sessionId, relationshipKey]
    );

    if (!state.relationships.length) {
      return e(
        "section",
        { className: "ha-manual-group" },
        e("h3", null, "Existing participant relationship"),
        e("p", { className: "ha-muted" }, "No participant relationships exist in this session yet.")
      );
    }
    return e(
      "section",
      { className: "ha-manual-group" },
      e("h3", null, "Existing participant relationship"),
      e(
        "label",
        { className: "ha-manual-participant", htmlFor: "ha-manual-participant-select" },
        e("span", null, "Participant ID"),
        e(
          "select",
          {
            id: "ha-manual-participant-select",
            value: selectedId,
            onChange: function (event) {
              setSelectedId(event.target.value);
            },
          },
          state.relationships.map(function (item) {
            return e("option", { value: item.id, key: item.id }, item.id);
          })
        )
      ),
      e(
        "p",
        { className: "ha-manual-controls__identity" },
        "Exact participant ",
        e("strong", null, selectedId)
      ),
      relation
        ? fieldGroup(
            "Values for " + relation.id,
            "relationship",
            RELATIONSHIP_FIELDS.map(function (entry) {
              return [
                entry[0],
                entry[1],
                entry[2],
                entry[0] === "unresolved_tension" ? relation.unresolvedTension : relation[entry[0]],
              ];
            }),
            model,
            identity,
            selectedId
          )
        : null
    );
  }

  function ManualStateControls(props) {
    const model = props.model;
    const state = props.state;
    const target = model.manualTarget;
    if (!model.controlsEnabled || !target || state.modelVersion !== 2) return null;
    const identity = controlIdentity(target, "");
    const affect = AFFECT_FIELDS.map(function (entry) {
      return [entry[0], entry[1], entry[2], state.affect[entry[0]]];
    });

    return e(
      "section",
      { className: "ha-manual-controls", "aria-labelledby": "ha-manual-controls-title" },
      targetHeader(target, state),
      fieldGroup("Affect", "affect", affect, model, identity, null),
      fieldGroup(
        "Atmosphere",
        "atmosphere",
        [["atmosphere_tension", 0, 1, state.atmosphereSource]],
        model,
        identity,
        null
      ),
      e(RelationshipControls, { state: state, model: model, target: target })
    );
  }

  return { ManualStateControls: ManualStateControls };
})();
