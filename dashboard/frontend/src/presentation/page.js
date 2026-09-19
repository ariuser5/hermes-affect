feature.presentation = (function () {
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
        { className: "ha-meter", role: "meter", "aria-valuemin": minimum, "aria-valuemax": maximum, "aria-valuenow": value },
        e("span", {
          className: "ha-meter__fill ha-meter__fill--" + tone,
          style: { width: percentage + "%" },
        })
      )
    );
  }

  function moodCore(state) {
    const valence = feature.domain.percent(state.affect.valence, -1, 1);
    const arousal = feature.domain.percent(state.affect.arousal, 0, 1);
    const frustration = feature.domain.percent(state.affect.frustration, 0, 1);
    return e(
      "div",
      {
        className: "ha-core",
        style: {
          "--ha-valence": valence + "%",
          "--ha-arousal": arousal + "%",
          "--ha-frustration": frustration + "%",
        },
      },
      e("div", { className: "ha-core__halo" }),
      e(
        "div",
        { className: "ha-core__body" },
        e("span", { className: "ha-core__label" }, "Current mood"),
        e("strong", null, feature.domain.label(state.mood)),
        e("span", { className: "ha-core__posture" }, feature.domain.label(state.posture))
      )
    );
  }

  function relationshipCard(relation) {
    return e(
      "article",
      { className: "ha-relationship", key: relation.id },
      e(
        "div",
        { className: "ha-relationship__top" },
        e("strong", { title: relation.id }, relation.id),
        relation.tension >= 0.5 ? statusBadge("Tense", "warning") : statusBadge("Observed", "muted")
      ),
      e(
        "div",
        { className: "ha-mini-grid" },
        metric("Trust", relation.trust, -1, 1, "positive"),
        metric("Affinity", relation.affinity, -1, 1, "positive"),
        metric("Respect", relation.respect, -1, 1, "accent"),
        metric("Irritation", relation.irritation, 0, 1, "danger"),
        metric("Tension", relation.tension, 0, 1, "warning")
      )
    );
  }

  function emptyState() {
    return e(
      "div",
      { className: "ha-empty" },
      e("div", { className: "ha-empty__icon", "aria-hidden": "true" }, "◇"),
      e("h2", null, "No affect state yet"),
      e("p", null, "Start a Hermes session with the affect plugin enabled. This page will update after the first state checkpoint.")
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

  function updatedLabel(value) {
    if (!value) return "unknown";
    try {
      return SDK.utils.isoTimeAgo(value);
    } catch (_error) {
      return "unknown";
    }
  }

  function renderState(state, hasError) {
    const updated = updatedLabel(state.updatedAt);
    const expression = state.expressionDrive === null ? "—" : feature.domain.formatNumber(state.expressionDrive);

    return e(
      "div",
      { className: "ha-page" },
      hasError
        ? e("div", { className: "ha-notice", role: "status" }, "Live refresh is temporarily unavailable. Showing the last valid snapshot.")
        : null,
      e(
        "header",
        { className: "ha-hero" },
        e(
          "div",
          { className: "ha-hero__copy" },
          e("div", { className: "ha-kicker" }, "Hermes Affect / live state"),
          e("h1", null, state.profileId),
          e("p", null, "A local, session-scoped view of emotional posture and relationship dynamics."),
          e(
            "div",
            { className: "ha-hero__meta" },
            statusBadge(hasError ? "Stale" : "Live", hasError ? "warning" : "success"),
            e("span", null, "Updated " + updated),
            e("span", null, "Revision " + state.revision),
            e("span", { title: state.sessionId }, "Session " + state.sessionId)
          )
        ),
        moodCore(state)
      ),
      e(
        "section",
        { className: "ha-grid ha-grid--overview" },
        sectionCard(
          "Affect balance",
          "Internal signal",
          e(
            "div",
            { className: "ha-metrics" },
            metric("Valence", state.affect.valence, -1, 1, "positive"),
            metric("Arousal", state.affect.arousal, 0, 1, "accent"),
            metric("Frustration", state.affect.frustration, 0, 1, "warning"),
            metric("Offended", state.affect.offended, 0, 1, "danger")
          )
        ),
        sectionCard(
          "Expression",
          "Behavioral projection",
          e(
            "div",
            { className: "ha-stat-grid" },
            e("div", { className: "ha-stat" }, e("span", null, "Drive"), e("strong", null, expression)),
            e("div", { className: "ha-stat" }, e("span", null, "Atmosphere"), e("strong", null, feature.domain.formatNumber(state.atmosphere))),
            e("div", { className: "ha-stat" }, e("span", null, "Model"), e("strong", null, "v" + state.modelVersion)),
            e("div", { className: "ha-stat" }, e("span", null, "Migration"), e("strong", null, state.migrationRequired ? "Required" : "Current"))
          )
        )
      ),
      e(
        "section",
        { className: "ha-grid ha-grid--context" },
        sectionCard("Active sensitivities", "Current turn", chips(state.sensitivities, "No active sensitivities.", "accent")),
        sectionCard("Open conflicts", "Relationship heat", chips(state.conflicts, "No open conflicts.", "warning"))
      ),
      sectionCard(
        "Relationships",
        state.relationships.length + " current participant" + (state.relationships.length === 1 ? "" : "s"),
        state.relationships.length
          ? e("div", { className: "ha-relationships" }, state.relationships.map(relationshipCard))
          : e("p", { className: "ha-muted" }, "No participant relationships have been recorded in this session."),
        "ha-card--relationships"
      ),
      state.tuning.length
        ? sectionCard(
            "Session tuning",
            "Temporary overrides",
            e(
              "div",
              { className: "ha-chip-row" },
              state.tuning.map(function (entry) {
                return e("span", { className: "ha-chip ha-chip--muted", key: entry[0] }, feature.domain.label(entry[0]) + " " + entry[1].toFixed(2));
              })
            )
          )
        : null
    );
  }

  function createPage(initialResponse) {
    return function AffectDashboardPage() {
      const model = feature.application.useDashboardState(initialResponse);
      if (!model.response.available || !model.response.state) return emptyState();
      return renderState(model.response.state, model.hasError);
    };
  }

  return { createPage: createPage };
})();
