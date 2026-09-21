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
vm.runInNewContext(source("application/state_polling.js"), { feature });
vm.runInNewContext(source("application/state_controller.js"), { feature });

function rawState(profileId, sessionId) {
  return {
    available: true,
    state: { profile_id: profileId, session_id: sessionId },
  };
}

const latest = feature.domain.latestSelection();
const exactOne = feature.domain.exactSelection("bot:one", "session:one");
const exactTwo = feature.domain.exactSelection("bot:two", "session:two");

assert.equal(feature.statePolling.shouldPollImmediately(latest, false), false);
assert.equal(feature.statePolling.shouldPollImmediately(latest, true), true);
assert.equal(feature.statePolling.shouldPollImmediately(exactOne, false), true);

const availablePreflight = {
  response: feature.domain.normalizeResponse(rawState("bot:latest", "session:latest")),
  responseSelection: latest,
  selectedStateError: null,
  errorSelection: null,
  hasError: false,
};
let view = feature.statePolling.deriveStateView(availablePreflight, latest, false);
assert.equal(view.hasMatchingResponse, true);
assert.equal(view.selectedStateLoading, false);

const unavailablePreflight = {
  response: feature.domain.normalizeResponse({ available: false, state: null }),
  responseSelection: latest,
  selectedStateError: null,
  errorSelection: null,
  hasError: false,
};
view = feature.statePolling.deriveStateView(unavailablePreflight, latest, false);
assert.equal(view.hasMatchingResponse, false);
assert.equal(view.selectedStateLoading, false);
assert.equal(view.selectedStateError, null);

const activeOne = { generation: 1, selection: exactOne };
let current = {
  response: feature.domain.normalizeResponse(rawState("bot:latest", "session:latest")),
  responseSelection: latest,
  selectedStateError: null,
  errorSelection: null,
  hasError: false,
};

assert.equal(
  feature.statePolling.isCurrentRequest(1, 1, exactOne, exactOne),
  true,
);
assert.equal(
  feature.statePolling.isCurrentRequest(1, 2, exactOne, exactOne),
  false,
);

current = feature.statePolling.acceptStateSuccess(current, activeOne, activeOne, rawState("bot:one", "session:one"));
view = feature.statePolling.deriveStateView(current, exactOne, false);
assert.equal(view.hasMatchingResponse, true);
assert.equal(view.selectedStateError, null);
assert.equal(view.selectedStateLoading, false);

const unavailable = feature.statePolling.acceptStateFailure(current, activeOne, activeOne);
view = feature.statePolling.deriveStateView(unavailable, exactOne, false);
assert.equal(view.hasMatchingResponse, false);
assert.equal(view.selectedStateError.kind, "unavailable");
assert.equal(view.selectedStateLoading, false);
assert.equal(unavailable.response.state.sessionId, "session:one");

const recovered = feature.statePolling.acceptStateSuccess(
  unavailable,
  activeOne,
  activeOne,
  rawState("bot:one", "session:one"),
);
view = feature.statePolling.deriveStateView(recovered, exactOne, false);
assert.equal(view.hasMatchingResponse, true);
assert.equal(view.selectedStateError, null);

const activeTwo = { generation: 2, selection: exactTwo };
const staleResponse = feature.statePolling.acceptStateSuccess(
  recovered,
  activeOne,
  activeTwo,
  rawState("bot:one", "session:one"),
);
assert.equal(staleResponse, recovered);
view = feature.statePolling.deriveStateView(recovered, exactTwo, false);
assert.equal(view.hasMatchingResponse, false);
assert.equal(view.selectedStateError, null);
assert.equal(view.selectedStateLoading, true);

const selectedTwo = feature.statePolling.acceptStateSuccess(
  recovered,
  activeTwo,
  activeTwo,
  rawState("bot:two", "session:two"),
);
view = feature.statePolling.deriveStateView(selectedTwo, exactTwo, false);
assert.equal(view.hasMatchingResponse, true);
assert.equal(view.selectedStateLoading, false);

view = feature.statePolling.deriveStateView(selectedTwo, latest, true);
assert.equal(view.selectedStateLoading, true);

view = feature.statePolling.deriveStateView(selectedTwo, exactTwo, true);
assert.equal(view.selectedStateLoading, true);

const unavailablePayload = feature.statePolling.acceptStateSuccess(
  selectedTwo,
  activeTwo,
  activeTwo,
  { available: false, state: null },
);
view = feature.statePolling.deriveStateView(unavailablePayload, exactTwo, false);
assert.equal(view.hasMatchingResponse, false);
assert.equal(view.selectedStateError.kind, "unavailable");

view = feature.statePolling.deriveStateView(recovered, exactOne, false);
assert.equal(view.hasMatchingResponse, true);
view = feature.statePolling.deriveStateView(recovered, exactTwo, false);
assert.equal(view.selectedStateLoading, true);

const calls = [];
const SDK = {
  fetchJSON(url) {
    calls.push(url);
    return Promise.resolve({});
  },
};
vm.runInNewContext(source("infrastructure/api.js"), { feature, SDK, URLSearchParams });

feature.infrastructure.loadState();
feature.infrastructure.loadState(exactOne);
feature.infrastructure.loadSessions(50, 100);

assert.equal(calls[0], "/api/plugins/hermes-affect/state");
assert.equal(
  calls[1],
  "/api/plugins/hermes-affect/state?profile_id=bot%3Aone&session_id=session%3Aone",
);
assert.equal(calls[2], "/api/plugins/hermes-affect/sessions?limit=50&offset=100");

console.log("dashboard controller tests passed");
