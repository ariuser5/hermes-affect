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

  function errorKind(error) {
    const status = Number(error && (error.statusCode || error.status));
    const message = String(error && error.message ? error.message : "");
    if (status === 409 || /\b409\b|revision conflict|\bconflict\b|changed; refresh and retry/i.test(message)) {
      return "conflict";
    }
    if (status === 404 || /\b404\b|unavailable/i.test(message)) return "unavailable";
    return "error";
  }

  function errorMessage(kind) {
    if (kind === "conflict") return "Revision conflict. Latest values loaded; review and apply again.";
    if (kind === "unavailable") return "The selected session is unavailable.";
    return "Unable to update session tuning. Try again after refreshing.";
  }

  function useTuningControls(selection, response, refreshState) {
    const statusPair = SDK.hooks.useState(null);
    const status = statusPair[0];
    const setStatus = statusPair[1];
    const errorPair = SDK.hooks.useState(null);
    const error = errorPair[0];
    const setError = errorPair[1];
    const resetPair = SDK.hooks.useState(0);
    const resetToken = resetPair[0];
    const setResetToken = resetPair[1];
    const target = targetFor(selection, response);
    const targetKey = target ? target.profileId + "\u0000" + target.sessionId : "";
    const requestGeneration = SDK.hooks.useRef(0);
    const activeTarget = SDK.hooks.useRef(targetKey);
    activeTarget.current = targetKey;

    SDK.hooks.useEffect(
      function () {
        requestGeneration.current += 1;
        setStatus(null);
        setError(null);
        setResetToken(function (current) {
          return current + 1;
        });
      },
      [targetKey]
    );

    function requestIsCurrent(generation, key) {
      return generation === requestGeneration.current && activeTarget.current === key;
    }

    async function save(request, resetDraftAfterSuccess) {
      if (!target || !response || !response.state || status === "saving") return;
      const generation = requestGeneration.current;
      const key = targetKey;
      setStatus("saving");
      setError(null);
      try {
        await request(target, response.state.revision);
        if (!requestIsCurrent(generation, key)) return;
        await refreshState();
        if (!requestIsCurrent(generation, key)) return;
        if (resetDraftAfterSuccess) {
          setResetToken(function (current) {
            return current + 1;
          });
        }
        setStatus("saved");
      } catch (requestError) {
        if (!requestIsCurrent(generation, key)) return;
        const kind = errorKind(requestError);
        setStatus(kind);
        setError(errorMessage(kind));
        if (kind === "conflict") {
          await refreshState();
          if (requestIsCurrent(generation, key)) {
            setResetToken(function (current) {
              return current + 1;
            });
          }
        }
      }
    }

    function applyExpressionGain(value) {
      return save(function (currentTarget, revision) {
        return feature.infrastructure.setExpressionGain(currentTarget, value, revision);
      });
    }

    function restoreExpressionGain() {
      return save(function (currentTarget, revision) {
        return feature.infrastructure.restoreExpressionGain(currentTarget, revision);
      }, true);
    }

    return {
      target: target,
      status: status,
      error: error,
      resetToken: resetToken,
      applyExpressionGain: applyExpressionGain,
      restoreExpressionGain: restoreExpressionGain,
    };
  }

  return { targetFor: targetFor, useTuningControls: useTuningControls };
})();
