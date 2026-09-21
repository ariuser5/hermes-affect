"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const feature = {};
const domainSource = fs.readFileSync(path.join(__dirname, "..", "src", "domain", "state.js"), "utf8");
const controllerSource = fs.readFileSync(
  path.join(__dirname, "..", "src", "application", "state_controller.js"),
  "utf8",
);
const apiSource = fs.readFileSync(path.join(__dirname, "..", "src", "infrastructure", "api.js"), "utf8");

vm.runInNewContext(domainSource, { feature });
vm.runInNewContext(controllerSource, { feature });

const latest = feature.domain.latestSelection();
const exact = feature.domain.exactSelection("bot:one", "session:one");
assert.equal(feature.application.isCurrentRequest(3, 3, exact, exact), true);
assert.equal(feature.application.isCurrentRequest(2, 3, exact, exact), false);
assert.equal(
  feature.application.isCurrentRequest(3, 3, exact, feature.domain.exactSelection("bot:two", "session:two")),
  false,
);

const selectedResponse = feature.domain.normalizeResponse({
  available: true,
  state: { profile_id: "bot:one", session_id: "session:one" },
});
assert.equal(feature.application.responseMatchesSelection(selectedResponse, exact), true);
assert.equal(feature.application.responseMatchesSelection(selectedResponse, latest), true);
assert.equal(
  feature.application.responseMatchesSelection(selectedResponse, feature.domain.exactSelection("bot:two", "session:two")),
  false,
);

const calls = [];
const SDK = {
  fetchJSON(url) {
    calls.push(url);
    return Promise.resolve({});
  },
};
vm.runInNewContext(apiSource, { feature, SDK, URLSearchParams });

feature.infrastructure.loadState();
feature.infrastructure.loadState(exact);
feature.infrastructure.loadSessions(50, 100);

assert.equal(calls[0], "/api/plugins/hermes-affect/state");
assert.equal(
  calls[1],
  "/api/plugins/hermes-affect/state?profile_id=bot%3Aone&session_id=session%3Aone",
);
assert.equal(calls[2], "/api/plugins/hermes-affect/sessions?limit=50&offset=100");

console.log("dashboard controller tests passed");
