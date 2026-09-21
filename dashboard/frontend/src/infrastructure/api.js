feature.infrastructure = (function () {
  const ENDPOINT = "/api/plugins/hermes-affect/state";
  const SESSIONS_ENDPOINT = "/api/plugins/hermes-affect/sessions";

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

  return { loadState: loadState, loadSessions: loadSessions };
})();
