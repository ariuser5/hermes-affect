feature.presentationTuningControls = (function () {
  const e = SDK.React.createElement;
  const MINIMUM = 0;
  const MAXIMUM = 10;
  const STEP = 0.1;

  function parseDraft(value) {
    if (value.trim() === "") return null;
    const number = Number(value);
    return Number.isFinite(number) && number >= MINIMUM && number <= MAXIMUM ? number : null;
  }

  function statusLabel(configuration) {
    return configuration.overrideExpressionGain !== null
      ? "Session override active"
      : "Using configured value";
  }

  function configuredValues(configuration) {
    return e(
      "div",
      { className: "ha-tuning-values", "aria-label": "Expression gain values" },
      e(
        "span",
        null,
        "Configured ",
        e("strong", null, feature.domain.formatNumber(configuration.configuredExpressionGain))
      ),
      e(
        "span",
        null,
        "Effective ",
        e("strong", null, feature.domain.formatNumber(configuration.effectiveExpressionGain))
      )
    );
  }

  function fieldInputs(draft, parsed, effective, saving, setDraft) {
    const rangeValue = parsed === null ? String(effective) : String(parsed);
    return e(
      "div",
      { className: "ha-tuning-field__inputs" },
      e("input", {
        id: "ha-expression-gain-range",
        className: "ha-tuning-field__range",
        type: "range",
        min: String(MINIMUM),
        max: String(MAXIMUM),
        step: String(STEP),
        value: rangeValue,
        onChange: function (event) {
          setDraft(event.target.value);
        },
        disabled: saving,
        "aria-label": "Expression gain slider from zero to ten",
      }),
      e(
        "label",
        { htmlFor: "ha-expression-gain-number", className: "ha-tuning-field__number" },
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
          "aria-label": "Expression gain numeric value",
          "aria-invalid": parsed === null,
        })
      )
    );
  }

  function feedback(model, parsed) {
    if (parsed === null) {
      return e(
        "span",
        { className: "ha-feedback ha-feedback--error", role: "alert" },
        "Enter a value from 0 to 10."
      );
    }
    if (model.tuningStatus === "saving") {
      return e("span", { className: "ha-feedback", role: "status" }, "Saving expression gain…");
    }
    if (model.tuningStatus === "saved") {
      return e("span", { className: "ha-feedback", role: "status" }, "Saved for this session.");
    }
    if (model.tuningStatus === "conflict" || model.tuningStatus === "unavailable" || model.tuningStatus === "error") {
      return e(
        "span",
        { className: "ha-feedback ha-feedback--error", role: "alert" },
        model.tuningError || "Unable to update expression gain."
      );
    }
    return null;
  }

  function TuningControls(props) {
    const model = props.model;
    const state = props.state;
    const configuration = state.tuningConfiguration;
    const effective = configuration ? configuration.effectiveExpressionGain : null;
    const initialValue = effective === null || effective === undefined ? "" : String(effective);
    const draftPair = SDK.hooks.useState(initialValue);
    const draft = draftPair[0];
    const setDraft = draftPair[1];

    SDK.hooks.useEffect(
      function () {
        setDraft(initialValue);
      },
      [state.profileId, state.sessionId, model.tuningResetToken]
    );

    if (!model.controlsEnabled || !configuration || !configuration.available || !model.tuningTarget) {
      return null;
    }

    const parsed = parseDraft(draft);
    const saving = model.tuningStatus === "saving";
    const overrideActive = configuration.overrideExpressionGain !== null;
    const changed = parsed !== null && parsed !== effective;
    return e(
      "section",
      { className: "ha-tuning-controls", "aria-label": "Expression gain tuning" },
      e(
        "div",
        { className: "ha-tuning-field__heading" },
        e("label", { htmlFor: "ha-expression-gain-number" }, "Expression gain"),
        e("span", { className: "ha-tuning-status" }, statusLabel(configuration))
      ),
      configuredValues(configuration),
      fieldInputs(draft, parsed, effective, saving, setDraft),
      e(
        "div",
        { className: "ha-tuning-field__actions" },
        e(
          "button",
          {
            type: "button",
            className: "ha-control-button",
            onClick: function () {
              if (parsed !== null) return model.applyExpressionGain(parsed);
            },
            disabled: saving || parsed === null || !changed,
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
        ),
        e("div", { className: "ha-tuning-field__feedback", "aria-live": "polite" }, feedback(model, parsed))
      )
    );
  }

  return { TuningControls: TuningControls, parseDraft: parseDraft };
})();
