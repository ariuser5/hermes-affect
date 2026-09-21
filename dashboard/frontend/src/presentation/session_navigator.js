feature.presentationSessionNavigator = (function () {
  const e = SDK.React.createElement;
  const primitives = feature.presentationPrimitives;

  function shortId(value) {
    if (value.length <= 28) return value;
    return value.slice(0, 12) + "…" + value.slice(-12);
  }

  function groupsFor(sessions) {
    const groups = [];
    const byProfile = Object.create(null);
    sessions.forEach(function (session) {
      let group = byProfile[session.profileId];
      if (!group) {
        group = { profileId: session.profileId, items: [] };
        byProfile[session.profileId] = group;
        groups.push(group);
      }
      group.items.push(session);
    });
    return groups;
  }

  function sessionIsSelected(selection, session) {
    return (
      selection.mode === "exact" &&
      selection.profileId === session.profileId &&
      selection.sessionId === session.sessionId
    );
  }

  function sessionRow(session, selected, onSelect) {
    return e(
      "button",
      {
        type: "button",
        className: "ha-session-row" + (selected ? " ha-session-row--selected" : ""),
        "aria-pressed": selected,
        title: session.profileId + " / " + session.sessionId,
        onClick: function () {
          onSelect(session);
        },
      },
      e("span", { className: "ha-session-row__marker", "aria-hidden": "true" }, selected ? "●" : "○"),
      e(
        "span",
        { className: "ha-session-row__body" },
        e("strong", null, shortId(session.sessionId)),
        e(
          "span",
          { className: "ha-session-row__meta" },
          "Updated " + primitives.updatedLabel(session.updatedAt) + " · Rev " + session.revision
        ),
        e(
          "span",
          { className: "ha-session-row__meta" },
          feature.domain.label(session.mood) + " · " + feature.domain.label(session.posture) + " · v" + session.modelVersion
        )
      )
    );
  }

  function latestRow(model) {
    const selected = model.selection.mode === "latest";
    return e(
      "button",
      {
        type: "button",
        className: "ha-session-latest" + (selected ? " ha-session-latest--selected" : ""),
        "aria-pressed": selected,
        onClick: model.returnToLatest,
      },
      e("span", { className: "ha-session-latest__marker", "aria-hidden": "true" }, selected ? "●" : "○"),
      e(
        "span",
        { className: "ha-session-row__body" },
        e("strong", null, "Latest session"),
        e("span", { className: "ha-session-row__meta" }, "Newest valid snapshot in this container")
      )
    );
  }

  function sessionNavigator(model) {
    const queryPair = SDK.hooks.useState("");
    const query = queryPair[0];
    const setQuery = queryPair[1];
    const normalizedQuery = query.trim().toLowerCase();
    const filtered = model.sessions.filter(function (session) {
      if (!normalizedQuery) return true;
      return (
        session.profileId.toLowerCase().includes(normalizedQuery) ||
        session.sessionId.toLowerCase().includes(normalizedQuery)
      );
    });
    const groups = groupsFor(filtered);
    const selectedTarget =
      model.selection.mode === "exact"
        ? model.selection.profileId + " / " + model.selection.sessionId
        : null;

    return e(
      "aside",
      { className: "ha-session-navigator", "aria-label": "Affect session navigation" },
      e(
        "div",
        { className: "ha-session-navigator__header" },
        e(
          "div",
          null,
          e("div", { className: "ha-kicker" }, "Session navigator"),
          e("h2", null, "Retained snapshots"),
          e("p", { className: "ha-muted" }, "Loaded sessions only; refresh to check for new entries.")
        ),
        e(
          "button",
          {
            type: "button",
            className: "ha-control-button",
            onClick: model.refreshSessions,
            disabled: model.catalogLoading,
          },
          model.catalogLoading ? "Refreshing…" : "Refresh"
        )
      ),
      e("div", { className: "ha-session-navigator__latest" }, latestRow(model)),
      e(
        "label",
        { className: "ha-session-search" },
        e("span", null, "Filter loaded sessions"),
        e("input", {
          type: "search",
          value: query,
          placeholder: "Profile or session ID",
          onChange: function (event) {
            setQuery(event.target.value);
          },
        })
      ),
      selectedTarget
        ? e(
            "div",
            { className: "ha-session-selection", role: "status" },
            e("span", null, "Selected: " + shortId(selectedTarget)),
            model.selectedStateLoading ? e("span", null, "Loading…") : null,
            model.selectedStateError
              ? e("span", { className: "ha-session-selection__error" }, "Unavailable")
              : null,
            e(
              "button",
              { type: "button", className: "ha-link-button", onClick: model.returnToLatest },
              "Return to Latest session"
            )
          )
        : null,
      model.catalogError
        ? e(
            "div",
            { className: "ha-session-error", role: "alert" },
            e("span", null, model.catalogError),
            e("button", { type: "button", className: "ha-link-button", onClick: model.refreshSessions }, "Retry")
          )
        : null,
      groups.length
        ? e(
            "div",
            { className: "ha-session-groups" },
            groups.map(function (group) {
              return e(
                "section",
                { className: "ha-session-group", key: group.profileId },
                e("h3", { title: group.profileId }, group.profileId),
                group.items.map(function (session) {
                  return sessionRow(
                    session,
                    sessionIsSelected(model.selection, session),
                    model.selectSession
                  );
                })
              );
            })
          )
        : e(
            "p",
            { className: "ha-muted ha-session-navigator__empty" },
            normalizedQuery ? "No loaded sessions match this filter." : "No retained sessions are available."
          ),
      model.catalog.hasMore
        ? e(
            "button",
            {
              type: "button",
              className: "ha-load-more",
              onClick: model.loadMoreSessions,
              disabled: model.catalogLoading,
            },
            model.catalogLoading ? "Loading…" : "Load more sessions"
          )
        : null
    );
  }

  return { sessionNavigator: sessionNavigator };
})();
