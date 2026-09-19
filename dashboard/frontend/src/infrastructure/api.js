feature.infrastructure = (function () {
  const ENDPOINT = "/api/plugins/hermes-affect/state";

  function loadState() {
    return SDK.fetchJSON(ENDPOINT);
  }

  return { loadState: loadState };
})();

