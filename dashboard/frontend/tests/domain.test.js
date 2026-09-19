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
  state: {
    profile_id: "bot:one",
    session_id: "session:one",
    revision: 4,
    affect: { valence: 4, arousal: -2, frustration: 0.5, offended: "bad" },
    relationships: { "user:one": { trust: 2, irritation: 0.4 } },
    open_conflicts: { "user:one": { heat: 0.7, status: "open" } },
  },
});

assert.equal(normalized.available, true);
assert.equal(normalized.state.affect.valence, 1);
assert.equal(normalized.state.affect.arousal, 0);
assert.equal(normalized.state.affect.frustration, 0.5);
assert.equal(normalized.state.affect.offended, 0);
assert.equal(normalized.state.relationships[0].trust, 1);
assert.equal(feature.domain.percent(0, -1, 1), 50);
assert.equal(feature.domain.label("counter_attack"), "Counter Attack");
assert.equal(
  JSON.stringify(feature.domain.normalizeResponse({ available: false })),
  JSON.stringify({ available: false, state: null }),
);
assert.equal(
  JSON.stringify(feature.domain.normalizeResponse({ available: "true", state: {} })),
  JSON.stringify({ available: false, state: null }),
);

console.log("dashboard domain tests passed");
