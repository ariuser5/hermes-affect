feature.presentationSessionNavigator = (function () {
  const e = SDK.React.createElement;
  const LATEST_OPTION = "latest";

  function shortId(value) {
    if (value.length <= 28) return value;
    return value.slice(0, 12) + "…" + value.slice(-12);
  }

  function optionValue(profileId, sessionId) {
    return JSON.stringify([profileId, sessionId]);
  }

  function selectionFromOption(value) {
    if (value === LATEST_OPTION) return feature.domain.latestSelection();
    try {
      const pair = JSON.parse(value);
      if (
        Array.isArray(pair) &&
        pair.length === 2 &&
        typeof pair[0] === "string" &&
        typeof pair[1] === "string"
      ) {
        return feature.domain.exactSelection(pair[0], pair[1]);
      }
    } catch (_error) {
      return feature.domain.latestSelection();
    }
    return feature.domain.latestSelection();
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

  function selectedValue(selection) {
    return selection.mode === "exact"
      ? optionValue(selection.profileId, selection.sessionId)
      : LATEST_OPTION;
  }

  function selectedIdentity(selection) {
    return selection.mode === "exact"
      ? selection.profileId + " / " + selection.sessionId
      : "Latest session";
  }

  function groupsWithSelection(groups, selection, selectedStateError) {
    const result = groups.map(function (group) {
      return { profileId: group.profileId, items: group.items.slice() };
    });
    if (selection.mode !== "exact") return result;

    let selectedGroup = result.find(function (group) {
      return group.profileId === selection.profileId;
    });
    if (!selectedGroup) {
      selectedGroup = { profileId: selection.profileId, items: [] };
      result.push(selectedGroup);
    }
    const hasSelectedSession = selectedGroup.items.some(function (session) {
      return session.sessionId === selection.sessionId;
    });
    if (!hasSelectedSession) {
      selectedGroup.items.push({
        profileId: selection.profileId,
        sessionId: selection.sessionId,
        unavailable: Boolean(selectedStateError),
      });
    }
    return result;
  }

  function sessionOption(session) {
    const identity = session.profileId + " / " + session.sessionId;
    const props = {
      key: optionValue(session.profileId, session.sessionId),
      value: optionValue(session.profileId, session.sessionId),
      title: identity,
    };
    if (session.unavailable) props.disabled = true;
    return e(
      "option",
      props,
      session.profileId + " / " + shortId(session.sessionId) + (session.unavailable ? " (unavailable)" : "")
    );
  }

  function sessionOptions(groups) {
    return [
      e("option", { key: LATEST_OPTION, value: LATEST_OPTION }, "Latest session"),
    ].concat(
      groups.map(function (group) {
        return e(
          "optgroup",
          { key: group.profileId, label: group.profileId },
          group.items.map(sessionOption)
        );
      })
    );
  }

  function handleSelectionChange(model, event) {
    const selection = selectionFromOption(event.target.value);
    if (selection.mode === "latest") {
      model.returnToLatest();
    } else {
      model.selectSession(selection);
    }
  }

  function navigatorHeader() {
    return e(
      "div",
      { className: "ha-session-navigator__header" },
      e(
        "div",
        null,
        e("div", { className: "ha-kicker" }, "Session navigator"),
        e("h2", { id: "ha-session-navigator-title" }, "Affect state session"),
        e(
          "p",
          { className: "ha-muted" },
          "Choose Latest session or a retained profile/session snapshot."
        )
      )
    );
  }

  function selectorControls(model, groups) {
    return e(
      "div",
      { className: "ha-session-controls" },
      e(
        "label",
        { className: "ha-session-selector", htmlFor: "ha-session-select" },
        e("span", { className: "ha-session-selector__label" }, "Session"),
        e(
          "select",
          {
            id: "ha-session-select",
            value: selectedValue(model.selection),
            onChange: function (event) {
              handleSelectionChange(model, event);
            },
            "aria-describedby": "ha-session-identity",
          },
          sessionOptions(groups)
        )
      ),
      e(
        "div",
        { className: "ha-session-actions" },
        e(
          "button",
          {
            type: "button",
            className: "ha-control-button",
            onClick: model.refreshSessions,
            disabled: model.catalogLoading,
          },
          model.catalogLoading ? "Refreshing…" : "Refresh"
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
              model.catalogLoading ? "Loading…" : "Load more"
            )
          : null
      )
    );
  }

  function selectedSessionSummary(model) {
    const identity = selectedIdentity(model.selection);
    const selectionStatus = model.selectedStateError
      ? e(
          "p",
          { className: "ha-session-status", role: "alert" },
          "Selected session unavailable."
        )
      : model.selectedStateLoading
        ? e(
            "p",
            { className: "ha-session-status", role: "status" },
            "Loading selected session…"
          )
        : null;
    return e(
      "div",
      { className: "ha-session-selection-meta" },
      e(
        "p",
        { id: "ha-session-identity", className: "ha-session-identity", title: identity },
        e("span", null, "Selected: "),
        e("strong", null, identity)
      ),
      selectionStatus
    );
  }

  function catalogError(model) {
    if (!model.catalogError) return null;
    return e(
      "div",
      { className: "ha-session-error", role: "alert" },
      e("span", null, model.catalogError),
      e(
        "button",
        { type: "button", className: "ha-link-button", onClick: model.refreshSessions },
        "Retry"
      )
    );
  }

  function catalogEmpty(model) {
    return !model.sessions.length
      ? e("p", { className: "ha-muted ha-session-navigator__empty" }, "No retained sessions are available.")
      : null;
  }

  function catalogFeedback(model) {
    const error = catalogError(model);
    const empty = catalogEmpty(model);
    if (!error && !empty) return null;
    return e("div", { className: "ha-session-catalog-feedback" }, error, empty);
  }

  function SessionNavigator(props) {
    const model = props.model;
    const groups = groupsWithSelection(
      groupsFor(model.sessions),
      model.selection,
      model.selectedStateError
    );
    return e(
      "section",
      { className: "ha-session-navigator", "aria-labelledby": "ha-session-navigator-title" },
      navigatorHeader(),
      selectorControls(model, groups),
      selectedSessionSummary(model),
      catalogFeedback(model)
    );
  }

  return {
    SessionNavigator: SessionNavigator,
    optionValue: optionValue,
    selectionFromOption: selectionFromOption,
  };
})();
