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

  function selectedParticipant(relationships, selectedId) {
    if (
      relationships.some(function (item) {
        return item.id === selectedId;
      })
    ) {
      return selectedId;
    }
    return relationships.length ? relationships[0].id : "";
  }

  function fieldLabel(field) {
    return field === "unresolved_tension" ? "Unresolved tension" : feature.domain.label(field);
  }

  function fieldControl(props) {
    const inputId = "ha-manual-" + props.scope + "-" + props.field;
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
      { className: "ha-manual-field" },
      e(
        "div",
        { className: "ha-manual-field__heading" },
        e("label", { htmlFor: inputId + "-number" }, fieldLabel(props.field)),
        e(
          "span",
          { className: "ha-manual-field__current" },
          "Current ",
          e("strong", null, feature.domain.formatNumber(props.value))
        )
      ),
      e("input", {
        id: inputId + "-range",
        className: "ha-manual-field__range",
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
          "aria-invalid": parsed === null,
        })
      ),
      e(
        "button",
        {
          type: "button",
          className: "ha-control-button ha-manual-field__apply",
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
      e(
        "div",
        { className: "ha-manual-field__feedback", "aria-live": "polite" },
        feedback && feedback.status === "saving"
          ? e("span", { className: "ha-feedback", role: "status" }, "Saving this value…")
          : null,
        parsed === null
          ? e(
              "span",
              { className: "ha-feedback ha-feedback--error", role: "alert" },
              "Enter a number from " + props.minimum + " to " + props.maximum + "."
            )
          : null,
        feedback && feedback.status === "saved"
          ? e("span", { className: "ha-feedback", role: "status" }, "Saved for this session.")
          : null,
        feedback && feedback.status === "conflict"
          ? e(
              "span",
              { className: "ha-feedback ha-feedback--error", role: "alert" },
              "Revision conflict. Latest values loaded; review and apply again."
            )
          : null,
        feedback && feedback.status === "unavailable"
          ? e(
              "span",
              { className: "ha-feedback ha-feedback--error", role: "alert" },
              "The selected session or participant is unavailable."
            )
          : null,
        feedback && feedback.status === "error"
          ? e(
              "span",
              { className: "ha-feedback ha-feedback--error", role: "alert" },
              feedback.message || "Unable to save this value."
            )
          : null
      )
    );
  }

  function fieldGroup(title, scope, entries, model, target, participantId) {
    const identity = controlIdentity(target, participantId);
    return e(
      "section",
      { className: "ha-manual-group", "aria-label": title },
      e("h3", null, title),
      entries.map(function (entry) {
        return e(fieldControl, {
          key: scope + "-" + entry[0] + "-" + (participantId || ""),
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

  function RelationshipControls(props) {
    const state = props.state;
    const model = props.model;
    const target = props.target;
    const targetKey = target.profileId + "\u0000" + target.sessionId;
    const relationshipKey = JSON.stringify(
      state.relationships.map(function (item) {
        return item.id;
      })
    );
    const firstId = state.relationships.length ? state.relationships[0].id : "";
    const pair = SDK.hooks.useState({ targetKey: targetKey, participantId: firstId });
    const selection = pair[0];
    const setSelection = pair[1];
    const storedId = selection.targetKey === targetKey ? selection.participantId : firstId;
    const selectedId = selectedParticipant(state.relationships, storedId);
    const relation = state.relationships.find(function (item) {
      return item.id === selectedId;
    });

    SDK.hooks.useEffect(
      function () {
        setSelection({ targetKey: targetKey, participantId: selectedId });
      },
      [targetKey, relationshipKey]
    );

    if (!state.relationships.length) {
      return e(
        "section",
        { className: "ha-manual-group", "aria-label": "Relationship controls" },
        e("h3", null, "Existing participant relationship"),
        e("p", { className: "ha-muted" }, "No participant relationships exist in this session yet.")
      );
    }
    return e(
      "section",
      { className: "ha-manual-group", "aria-label": "Relationship controls" },
      e("h3", null, "Existing participant relationship"),
      e(
        "label",
        { className: "ha-manual-participant", htmlFor: "ha-manual-participant-select" },
        e("span", null, "Participant"),
        e(
          "select",
          {
            id: "ha-manual-participant-select",
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
            target,
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

    if (props.group === "affect") {
      return fieldGroup(
        "Affect",
        "affect",
        AFFECT_FIELDS.map(function (entry) {
          return [entry[0], entry[1], entry[2], state.affect[entry[0]]];
        }),
        model,
        target,
        null
      );
    }
    if (props.group === "atmosphere") {
      return fieldGroup(
        "Atmosphere",
        "atmosphere",
        [["atmosphere_tension", 0, 1, state.atmosphereSource]],
        model,
        target,
        null
      );
    }
    if (props.group === "relationship") {
      return e(RelationshipControls, { state: state, model: model, target: target });
    }
    return null;
  }

  return { ManualStateControls: ManualStateControls };
})();
