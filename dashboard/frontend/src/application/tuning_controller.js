feature.tuningController = (function () {
  function targetFor(selection, response) {
    if (selection.mode === "exact") {
      return { profileId: selection.profileId, sessionId: selection.sessionId };
    }
    if (response && response.available && response.state) {
      return {
        profileId: response.state.profileId,
        sessionId: response.state.sessionId,
      };
    }
    return null;
  }

  function errorMessage(error) {
    return error && error.message ? String(error.message) : "Unable to update session tuning.";
  }

  function useTuningControls(selection, response, refreshState) {
    const statusPair = SDK.hooks.useState(null);
    const status = statusPair[0];
    const setStatus = statusPair[1];
    const errorPair = SDK.hooks.useState(null);
    const error = errorPair[0];
    const setError = errorPair[1];
    const target = targetFor(selection, response);

    SDK.hooks.useEffect(
      function () {
        setStatus(null);
        setError(null);
      },
      [selection.mode, selection.profileId, selection.sessionId]
    );

    async function applyExpressionGain(value) {
      if (!target) return;
      setStatus("saving");
      setError(null);
      try {
        await feature.infrastructure.setExpressionGain(target, value);
        setStatus("saved");
        await refreshState();
      } catch (requestError) {
        setStatus("error");
        setError(errorMessage(requestError));
      }
    }

    async function restoreExpressionGain() {
      if (!target) return;
      setStatus("saving");
      setError(null);
      try {
        await feature.infrastructure.restoreExpressionGain(target);
        setStatus("saved");
        await refreshState();
      } catch (requestError) {
        setStatus("error");
        setError(errorMessage(requestError));
      }
    }

    return {
      target: target,
      status: status,
      error: error,
      applyExpressionGain: applyExpressionGain,
      restoreExpressionGain: restoreExpressionGain,
    };
  }

  return { targetFor: targetFor, useTuningControls: useTuningControls };
})();
