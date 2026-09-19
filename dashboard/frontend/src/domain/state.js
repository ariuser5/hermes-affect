feature.domain = (function () {
  const COLLECTION_LIMIT = 64;
  const TEXT_LIMIT = 200;

  function objectOrEmpty(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function text(value, fallback) {
    if (value === null || value === undefined) return fallback || "";
    return String(value).slice(0, TEXT_LIMIT);
  }

  function finite(value, minimum, maximum, fallback) {
    const number = Number(value);
    if (!Number.isFinite(number)) return fallback;
    return Math.max(minimum, Math.min(maximum, number));
  }

  function entries(value) {
    return Object.entries(objectOrEmpty(value)).slice(-COLLECTION_LIMIT);
  }

  function normalizeRelationship(participantId, raw) {
    const relation = objectOrEmpty(raw);
    return {
      id: text(participantId, "unknown"),
      trust: finite(relation.trust, -1, 1, 0),
      affinity: finite(relation.affinity, -1, 1, 0),
      irritation: finite(relation.irritation, 0, 1, 0),
      respect: finite(relation.respect, -1, 1, 0),
      tension: finite(relation.unresolved_tension, 0, 1, 0),
    };
  }

  function normalizeConflict(participantId, raw) {
    const conflict = objectOrEmpty(raw);
    return {
      id: text(participantId, "unknown"),
      heat: finite(conflict.heat, 0, 1, 0),
      status: text(conflict.status, "open"),
    };
  }

  function normalizeResponse(raw) {
    const response = objectOrEmpty(raw);
    if (
      response.available !== true ||
      !response.state ||
      typeof response.state !== "object" ||
      Array.isArray(response.state)
    ) {
      return { available: false, state: null };
    }

    const state = objectOrEmpty(response.state);
    const affect = objectOrEmpty(state.affect);
    return {
      available: true,
      state: {
        profileId: text(state.profile_id, "unknown"),
        sessionId: text(state.session_id, "unknown"),
        revision: Math.max(0, Math.trunc(finite(state.revision, 0, Number.MAX_SAFE_INTEGER, 0))),
        updatedAt: text(state.updated_at, ""),
        mood: text(state.mood, "neutral"),
        posture: text(state.response_posture, "normal_engagement"),
        modelVersion: Math.max(0, Math.trunc(finite(state.model_version, 0, 999, 0))),
        migrationRequired: Boolean(state.migration_required),
        expressionDrive:
          state.expression_drive === null || state.expression_drive === undefined
            ? null
            : finite(state.expression_drive, 0, 1, 0),
        atmosphere: finite(state.perceived_atmosphere_tension, 0, 1, 0),
        affect: {
          valence: finite(affect.valence, -1, 1, 0),
          arousal: finite(affect.arousal, 0, 1, 0),
          frustration: finite(affect.frustration, 0, 1, 0),
          offended: finite(affect.offended, 0, 1, 0),
        },
        relationships: entries(state.relationships).map(function (entry) {
          return normalizeRelationship(entry[0], entry[1]);
        }),
        sensitivities: Array.isArray(state.active_sensitivities)
          ? state.active_sensitivities.slice(-COLLECTION_LIMIT).map(function (item) {
              return text(item, "unknown");
            })
          : [],
        conflicts: entries(state.open_conflicts).map(function (entry) {
          return normalizeConflict(entry[0], entry[1]);
        }),
        tuning: entries(state.tuning_overrides).map(function (entry) {
          return [text(entry[0], "unknown"), finite(entry[1], 0, 10, 0)];
        }),
      },
    };
  }

  function percent(value, minimum, maximum) {
    const normalized = (finite(value, minimum, maximum, minimum) - minimum) / (maximum - minimum);
    return Math.round(normalized * 1000) / 10;
  }

  function formatNumber(value) {
    return finite(value, -10, 10, 0).toFixed(2);
  }

  function label(value) {
    return text(value, "unknown")
      .replace(/[_-]+/g, " ")
      .replace(/\b\w/g, function (character) {
        return character.toUpperCase();
      });
  }

  return {
    normalizeResponse: normalizeResponse,
    percent: percent,
    formatNumber: formatNumber,
    label: label,
  };
})();
