"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const feature = {};
const source = function (relativePath) {
  return fs.readFileSync(path.join(__dirname, "..", "src", relativePath), "utf8");
};

vm.runInNewContext(source("domain/state.js"), { feature });
vm.runInNewContext(source("application/tuning_controller.js"), { feature, SDK: {} });

const exact = feature.domain.exactSelection("bot:one", "session:one");
const latest = feature.domain.latestSelection();
const response = feature.domain.normalizeResponse({
  available: true,
  state: { profile_id: "bot:latest", session_id: "session:latest" },
});

assert.equal(
  JSON.stringify(feature.tuningController.targetFor(exact, response)),
  JSON.stringify({ profileId: "bot:one", sessionId: "session:one" }),
);
assert.equal(
  JSON.stringify(feature.tuningController.targetFor(latest, response)),
  JSON.stringify({ profileId: "bot:latest", sessionId: "session:latest" }),
);
assert.equal(
  feature.tuningController.targetFor(latest, { available: false, state: null }),
  null,
);

const calls = [];
const SDK = {
  fetchJSON(url, options) {
    calls.push({ url, options });
    return Promise.resolve({});
  },
};
vm.runInNewContext(source("infrastructure/api.js"), { feature, SDK, URLSearchParams });
const target = { profileId: "bot:one", sessionId: "session:one" };
feature.infrastructure.setExpressionGain(target, 2.5);
feature.infrastructure.restoreExpressionGain(target);

assert.equal(JSON.stringify(calls), JSON.stringify([
  {
    url: "/api/plugins/hermes-affect/tuning?profile_id=bot%3Aone&session_id=session%3Aone&expression_gain=2.5",
    options: { method: "POST" },
  },
  {
    url: "/api/plugins/hermes-affect/tuning?profile_id=bot%3Aone&session_id=session%3Aone",
    options: { method: "DELETE" },
  },
]));

console.log("dashboard tuning tests passed");
