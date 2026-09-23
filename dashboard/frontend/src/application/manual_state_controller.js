feature.manualStateController = (function () {
  function targetFor(selection, response) {
    if (selection.mode === "exact") {
      return { profileId: selection.profileId, sessionId: selection.sessionId };
    }
    if (response && response.available && response.state) {
      return { profileId: response.state.profileId, sessionId: response.state.sessionId };
    }
    return null;
  }

  function targetKey(target) {
    return target ? target.profileId + "\u0000" + target.sessionId : "";
  }

  function errorKind(error) {
    const status = Number(error && (error.statusCode || error.status));
    const message = String(error && error.message ? error.message : "");
    if (status === 409 || /\b409\b|changed; refresh and retry/i.test(message)) return "conflict";
    if (status === 404 || /\b404\b|unavailable/i.test(message)) return "unavailable";
    return "error";
  }

  function safeErrorMessage(kind) {
    if (kind === "conflict") return "The session changed; refreshed values need review.";
    if (kind === "unavailable") return "The selected session or participant is unavailable.";
    return "Unable to save this value. Try again after refreshing the session.";
  }

  function replaceStatus(current, key, value) {
    const next = Object.assign({}, current, { [key]: value });
    const keys = Object.keys(next);
    keys.slice(0, Math.max(0, keys.length - 64)).forEach(function (oldKey) {
      delete next[oldKey];
    });
    return next;
  }

  function useManualStateControls(selection, response, refreshState) {
    const target = targetFor(selection, response);
    const currentKey = targetKey(target);
    const statusPair = SDK.hooks.useState({});
    const statusByField = statusPair[0];
    const setStatusByField = statusPair[1];
    const pendingPair = SDK.hooks.useState(false);
    const pending = pendingPair[0];
    const setPending = pendingPair[1];
    const resetPair = SDK.hooks.useState(0);
    const resetToken = resetPair[0];
    const setResetToken = resetPair[1];
    const requestGeneration = SDK.hooks.useRef(0);
    const activeKey = SDK.hooks.useRef(currentKey);
    activeKey.current = currentKey;

    SDK.hooks.useEffect(
      function () {
        requestGeneration.current += 1;
        setPending(false);
      },
      [currentKey]
    );

    function statusKey(scope, field, participantId) {
      return [currentKey, scope, field, participantId || ""].join("\u0000");
    }

    function statusFor(scope, field, participantId) {
      return statusByField[statusKey(scope, field, participantId)] || null;
    }

    async function apply(scope, field, value, participantId) {
      if (!target || !response || !response.state || pending) return;
      const key = statusKey(scope, field, participantId);
      const generation = requestGeneration.current;
      const payload = {
        profile_id: target.profileId,
        session_id: target.sessionId,
        scope: scope,
        field: field,
        value: value,
        expected_revision: response.state.revision,
      };
      if (scope === "relationship") payload.participant_id = participantId;
      setPending(true);
      setStatusByField(replaceStatus(statusByField, key, { status: "saving" }));
      try {
        await feature.infrastructure.applyManualState(payload);
        if (generation !== requestGeneration.current || activeKey.current !== currentKey) return;
        await refreshState();
        if (generation !== requestGeneration.current || activeKey.current !== currentKey) return;
        setStatusByField(replaceStatus(statusByField, key, { status: "saved" }));
      } catch (error) {
        if (generation !== requestGeneration.current || activeKey.current !== currentKey) return;
        const kind = errorKind(error);
        setStatusByField(
          replaceStatus(statusByField, key, {
            status: kind,
            message: safeErrorMessage(kind),
          })
        );
        if (kind === "conflict") {
          await refreshState();
          if (generation === requestGeneration.current && activeKey.current === currentKey) {
            setResetToken(resetToken + 1);
          }
        }
      } finally {
        if (generation === requestGeneration.current && activeKey.current === currentKey) {
          setPending(false);
        }
      }
    }

    return {
      target: target,
      pending: pending,
      resetToken: resetToken,
      statusFor: statusFor,
      apply: apply,
    };
  }

  return { targetFor: targetFor, useManualStateControls: useManualStateControls };
})();
