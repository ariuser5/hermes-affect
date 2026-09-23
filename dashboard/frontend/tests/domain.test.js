"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const feature = {};
const source = fs.readFileSync(path.join(__dirname, "..", "src", "domain", "state.js"), "utf8");
vm.runInNewContext(source, { feature });

const normalized = feature.domain.normalizeResponse({
  available: true,
  controls_enabled: true,
  state: {
    profile_id: "bot:one",
    session_id: "session:one",
    revision: 4,
    tuning_configuration: {
      available: true,
      configured: { expression_gain: 1 },
      effective: { expression_gain: 2.5 },
      overrides: { expression_gain: 2.5 },
    },
    affect: { valence: 4, arousal: -2, frustration: 0.5, offended: "bad" },
    perceived_atmosphere_tension: 0.25,
    relationships: { "user:one": { trust: 2, irritation: 0.4, unresolved_tension: 0.6 } },
    open_conflicts: { "user:one": { heat: 0.7, status: "open" } },
  },
});

assert.equal(normalized.available, true);
assert.equal(normalized.controlsEnabled, true);
assert.equal(normalized.state.affect.valence, 1);
assert.equal(normalized.state.affect.arousal, 0);
assert.equal(normalized.state.affect.frustration, 0.5);
assert.equal(normalized.state.affect.offended, 0);
assert.equal(normalized.state.tuningConfiguration.available, true);
assert.equal(normalized.state.tuningConfiguration.configuredExpressionGain, 1);
assert.equal(normalized.state.tuningConfiguration.effectiveExpressionGain, 2.5);
assert.equal(normalized.state.tuningConfiguration.overrideExpressionGain, 2.5);
assert.equal(normalized.state.relationships[0].trust, 1);
assert.equal(normalized.state.relationships[0].unresolvedTension, 0.6);
assert.equal(normalized.state.atmosphereSource, 0.25);
assert.equal(feature.domain.percent(0, -1, 1), 50);
assert.equal(feature.domain.label("counter_attack"), "Counter Attack");
assert.equal(
  JSON.stringify(feature.domain.normalizeResponse({ available: false })),
  JSON.stringify({ available: false, state: null, controlsEnabled: false }),
);
assert.equal(
  JSON.stringify(feature.domain.normalizeResponse({ available: "true", state: {} })),
  JSON.stringify({ available: false, state: null, controlsEnabled: false }),
);

assert.equal(JSON.stringify(feature.domain.latestSelection()), JSON.stringify({ mode: "latest" }));
assert.equal(
  JSON.stringify(feature.domain.exactSelection("bot:one", "session:one")),
  JSON.stringify({ mode: "exact", profileId: "bot:one", sessionId: "session:one" }),
);
assert.equal(
  JSON.stringify(feature.domain.exactSelection("", "session:one")),
  JSON.stringify({ mode: "latest" }),
);
assert.equal(
  feature.domain.sameSelection(
    feature.domain.exactSelection("bot:one", "session:one"),
    feature.domain.exactSelection("bot:one", "session:one"),
  ),
  true,
);

const catalog = feature.domain.normalizeCatalogResponse({
  items: [
    {
      profile_id: "bot:one",
      session_id: "session:one",
      updated_at: "2026-09-21T10:00:00+00:00",
      revision: 4,
      mood: "guarded",
      response_posture: "terse",
      model_version: 2,
    },
    { profile_id: "", session_id: "missing" },
  ],
  limit: 2,
  offset: 0,
  has_more: true,
});
assert.equal(catalog.items.length, 1);
assert.equal(catalog.items[0].profileId, "bot:one");
assert.equal(catalog.items[0].posture, "terse");
assert.equal(catalog.hasMore, true);

const merged = feature.domain.mergeCatalogPages(catalog, {
  items: [
    catalog.items[0],
    {
      profileId: "bot:two",
      sessionId: "session:two",
      updatedAt: "2026-09-21T09:00:00+00:00",
      revision: 1,
      mood: "neutral",
      posture: "normal_engagement",
      modelVersion: 2,
    },
  ],
  limit: 2,
  offset: 1,
  hasMore: false,
});
assert.equal(merged.items.length, 2);
assert.equal(merged.items[1].profileId, "bot:two");

console.log("dashboard domain tests passed");
