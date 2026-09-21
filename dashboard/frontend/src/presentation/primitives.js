feature.presentationPrimitives = (function () {
  const e = SDK.React.createElement;
  const Card = SDK.components.Card;
  const CardContent = SDK.components.CardContent;
  const CardHeader = SDK.components.CardHeader;
  const CardTitle = SDK.components.CardTitle;
  const Badge = SDK.components.Badge;

  function statusBadge(text, tone) {
    return e(Badge, { className: "ha-badge ha-badge--" + tone }, text);
  }

  function sectionCard(title, eyebrow, content, className) {
    return e(
      Card,
      { className: "ha-card " + (className || "") },
      e(
        CardHeader,
        { className: "ha-card__header" },
        eyebrow ? e("div", { className: "ha-eyebrow" }, eyebrow) : null,
        e(CardTitle, { className: "ha-card__title" }, title)
      ),
      e(CardContent, { className: "ha-card__content" }, content)
    );
  }

  function metric(label, value, minimum, maximum, tone) {
    const percentage = feature.domain.percent(value, minimum, maximum);
    return e(
      "div",
      { className: "ha-metric" },
      e(
        "div",
        { className: "ha-metric__heading" },
        e("span", null, label),
        e("strong", null, feature.domain.formatNumber(value))
      ),
      e(
        "div",
        {
          className: "ha-meter",
          role: "meter",
          "aria-valuemin": minimum,
          "aria-valuemax": maximum,
          "aria-valuenow": value,
        },
        e("span", {
          className: "ha-meter__fill ha-meter__fill--" + tone,
          style: { width: percentage + "%" },
        })
      )
    );
  }

  function chips(items, emptyText, tone) {
    if (!items.length) return e("p", { className: "ha-muted" }, emptyText);
    return e(
      "div",
      { className: "ha-chip-row" },
      items.map(function (item) {
        const value = typeof item === "string" ? item : item.id;
        return e("span", { className: "ha-chip ha-chip--" + tone, key: value }, value);
      })
    );
  }

  function emptyState() {
    return e(
      "div",
      { className: "ha-empty" },
      e("div", { className: "ha-empty__icon", "aria-hidden": "true" }, "◇"),
      e("h2", null, "No affect state yet"),
      e(
        "p",
        null,
        "Start a Hermes session with the affect plugin enabled. This page will update after the first state checkpoint."
      )
    );
  }

  function updatedLabel(value) {
    if (!value) return "unknown";
    try {
      return SDK.utils.isoTimeAgo(value);
    } catch (_error) {
      return "unknown";
    }
  }

  return {
    statusBadge: statusBadge,
    sectionCard: sectionCard,
    metric: metric,
    chips: chips,
    emptyState: emptyState,
    updatedLabel: updatedLabel,
  };
})();
