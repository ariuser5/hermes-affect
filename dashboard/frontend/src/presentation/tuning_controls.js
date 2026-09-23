feature.presentationTuningControls = (function () {
  const e = SDK.React.createElement;
  const MINIMUM = 0;
  const MAXIMUM = 10;
  const STEP = 0.1;

  function displayValue(value) {
    return feature.domain.formatNumber(value);
  }

  function parseDraft(value) {
    if (value.trim() === "") return null;
    const number = Number(value);
    return Number.isFinite(number) && number >= MINIMUM && number <= MAXIMUM ? number : null;
  }

  function tuningHeader(configuration) {
    return e(
      "div",
      { className: "ha-tuning-controls__header" },
      e(
        "div",
        null,
        e("div", { className: "ha-kicker" }, "Session tuning"),
        e("h2", { id: "ha-tuning-title" }, "Expression gain"),
        e(
          "p",
          { className: "ha-muted" },
          "Adjust expression strength for this retained session only."
        )
      ),
      configuration.overrideExpressionGain !== null
        ? e(
            "span",
            { className: "ha-tuning-status ha-tuning-status--active" },
            "Session override active"
          )
        : e("span", { className: "ha-tuning-status" }, "Using configured value")
    );
  }

  function tuningValues(configuration) {
    return e(
      "div",
      { className: "ha-tuning-values" },
      e(
        "span",
        null,
        "Configured ",
        e("strong", null, displayValue(configuration.configuredExpressionGain))
      ),
      e(
        "span",
        null,
        "Effective ",
        e("strong", null, displayValue(configuration.effectiveExpressionGain))
      )
    );
  }

  function tuningInputs(draft, value, effective, saving, setDraft) {
    return e(
      "div",
      { className: "ha-tuning-inputs" },
      e(
        "label",
        { className: "ha-tuning-slider", htmlFor: "ha-expression-gain-range" },
        e("span", null, "Expression gain"),
        e("input", {
          id: "ha-expression-gain-range",
          type: "range",
          min: String(MINIMUM),
          max: String(MAXIMUM),
          step: String(STEP),
          value: value === null ? String(effective) : String(value),
          onChange: function (event) {
            setDraft(event.target.value);
          },
          disabled: saving,
          "aria-label": "Expression gain from zero to ten",
        })
      ),
      e(
        "label",
        { className: "ha-tuning-number", htmlFor: "ha-expression-gain-number" },
        e("span", null, "Value"),
        e("input", {
          id: "ha-expression-gain-number",
          type: "number",
          min: String(MINIMUM),
          max: String(MAXIMUM),
          step: String(STEP),
          value: draft,
          onChange: function (event) {
            setDraft(event.target.value);
          },
          disabled: saving,
          "aria-label": "Expression gain value",
        })
      )
    );
  }

  function tuningActions(model, value, changed, saving, overrideActive) {
    return e(
      "div",
      { className: "ha-tuning-actions" },
      e(
        "button",
        {
          type: "button",
          className: "ha-control-button",
          onClick: function () {
            model.applyExpressionGain(value);
          },
          disabled: saving || value === null || !changed,
        },
        saving ? "Saving…" : "Apply"
      ),
      e(
        "button",
        {
          type: "button",
          className: "ha-link-button",
          onClick: model.restoreExpressionGain,
          disabled: saving || !overrideActive,
        },
        "Restore configured value"
      )
    );
  }

  function tuningFeedback(model) {
    return [
      model.tuningStatus === "saved"
        ? e(
            "p",
            { className: "ha-tuning-feedback", role: "status", key: "saved" },
            "Saved for this session."
          )
        : null,
      model.tuningError
        ? e(
            "p",
            {
              className: "ha-tuning-feedback ha-tuning-feedback--error",
              role: "alert",
              key: "error",
            },
            model.tuningError
          )
        : null,
    ];
  }

  function TuningControls(props) {
    const model = props.model;
    const state = props.state;
    const configuration = state.tuningConfiguration;
    const initialValue = configuration ? configuration.effectiveExpressionGain : null;
    const draftPair = SDK.hooks.useState(
      initialValue === null || initialValue === undefined ? "" : String(initialValue)
    );
    const draft = draftPair[0];
    const setDraft = draftPair[1];

    SDK.hooks.useEffect(
      function () {
        setDraft(initialValue === null || initialValue === undefined ? "" : String(initialValue));
      },
      [
        state.profileId,
        state.sessionId,
        configuration ? configuration.effectiveExpressionGain : null,
      ]
    );

    if (!model.controlsEnabled || !configuration || !configuration.available || !model.tuningTarget) {
      return null;
    }

    const value = parseDraft(draft);
    const saving = model.tuningStatus === "saving";
    const overrideActive = configuration.overrideExpressionGain !== null;
    const changed = value !== null && value !== configuration.effectiveExpressionGain;
    return e(
      "section",
      { className: "ha-tuning-controls", "aria-labelledby": "ha-tuning-title" },
      tuningHeader(configuration),
      tuningValues(configuration),
      tuningInputs(draft, value, configuration.effectiveExpressionGain, saving, setDraft),
      tuningActions(model, value, changed, saving, overrideActive),
      tuningFeedback(model)
    );
  }

  return { TuningControls: TuningControls };
})();
