feature.presentationStateSummary = (function () {
  const e = SDK.React.createElement;

  function meter(state, name, minimum, maximum, tone) {
    const value = state ? state.affect[name] : null;
    const percentage = value === null ? 0 : feature.domain.percent(value, minimum, maximum);
    return e(
      "div",
      { className: "ha-summary-meter", key: name },
      e(
        "div",
        { className: "ha-summary-meter__label" },
        e("span", null, feature.domain.label(name)),
        e("strong", null, value === null ? "—" : feature.domain.formatNumber(value))
      ),
      e(
        "div",
        {
          className: "ha-summary-meter__track",
          role: "meter",
          "aria-label": feature.domain.label(name),
          "aria-valuemin": minimum,
          "aria-valuemax": maximum,
          "aria-valuenow": value === null ? undefined : value,
        },
        e("span", {
          className: "ha-summary-meter__fill ha-summary-meter__fill--" + tone,
          style: { width: percentage + "%" },
        })
      )
    );
  }

  function Summary(props) {
    const state = props.state;
    const posture = state ? feature.domain.label(state.posture) : "—";
    const updated = state ? feature.presentationPrimitives.updatedLabel(state.updatedAt) : "—";
    return e(
      "section",
      { className: "ha-summary", "aria-label": "Current affect summary" },
      e(
        "div",
        { className: "ha-summary__identity" },
        e(
          "div",
          { className: "ha-summary__mood" },
          e("span", null, "Current mood"),
          e("strong", null, state ? feature.domain.label(state.mood) : "No affect state"),
          e(
            "span",
            { className: "ha-summary__posture" },
            "Last response posture: ",
            e("strong", null, posture)
          )
        ),
        e(
          "div",
          { className: "ha-summary__meta" },
          props.hasError && state
            ? e("span", { className: "ha-summary__freshness", role: "status" }, "Stale snapshot")
            : null,
          e("span", null, "Updated ", e("strong", null, updated)),
          e("span", null, "Revision ", e("strong", null, state ? String(state.revision) : "—"))
        )
      ),
      e(
        "div",
        { className: "ha-summary__meters" },
        meter(state, "valence", -1, 1, "positive"),
        meter(state, "arousal", 0, 1, "accent"),
        meter(state, "frustration", 0, 1, "warning"),
        meter(state, "offended", 0, 1, "danger")
      )
    );
  }

  return { Summary: Summary };
})();
