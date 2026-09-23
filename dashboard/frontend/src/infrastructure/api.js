feature.infrastructure = (function () {
  const ENDPOINT = "/api/plugins/hermes-affect/state";
  const SESSIONS_ENDPOINT = "/api/plugins/hermes-affect/sessions";
  const TUNING_ENDPOINT = "/api/plugins/hermes-affect/tuning";
  const CONTROLS_ENDPOINT = "/api/plugins/hermes-affect/controls";

  function loadState(selection) {
    const params = new URLSearchParams();
    if (selection && selection.mode === "exact") {
      params.set("profile_id", selection.profileId);
      params.set("session_id", selection.sessionId);
    }
    const query = params.toString();
    return SDK.fetchJSON(query ? ENDPOINT + "?" + query : ENDPOINT);
  }

  function loadSessions(limit, offset) {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    return SDK.fetchJSON(SESSIONS_ENDPOINT + "?" + params.toString());
  }

  function tuningQuery(target, revision) {
    const params = new URLSearchParams();
    params.set("profile_id", target.profileId);
    params.set("session_id", target.sessionId);
    params.set("expected_revision", String(revision));
    return params;
  }

  function setExpressionGain(target, value, revision) {
    const params = tuningQuery(target, revision);
    params.set("expression_gain", String(value));
    return SDK.fetchJSON(TUNING_ENDPOINT + "?" + params.toString(), { method: "POST" });
  }

  function restoreExpressionGain(target, revision) {
    const params = tuningQuery(target, revision);
    return SDK.fetchJSON(TUNING_ENDPOINT + "?" + params.toString(), { method: "DELETE" });
  }

  function applyManualState(payload) {
    return SDK.fetchJSON(CONTROLS_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  return {
    loadState: loadState,
    loadSessions: loadSessions,
    setExpressionGain: setExpressionGain,
    restoreExpressionGain: restoreExpressionGain,
    applyManualState: applyManualState,
  };
})();
