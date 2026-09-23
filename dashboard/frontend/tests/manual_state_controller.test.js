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

const state = {
  profileId: "profile:latest",
  sessionId: "session:latest",
  revision: 12,
};
const response = { available: true, state: state };
const latest = feature.domain.latestSelection();
const exact = feature.domain.exactSelection("profile:exact", "session:exact");

let hookIndex = 0;
const hookSlots = [];
const SDK = {
  hooks: {
    useState(initial) {
      const index = hookIndex++;
      if (!(index in hookSlots)) hookSlots[index] = initial;
      return [hookSlots[index], (next) => (hookSlots[index] = next)];
    },
    useRef(initial) {
      const index = hookIndex++;
      if (!(index in hookSlots)) hookSlots[index] = { current: initial };
      return hookSlots[index];
    },
    useEffect(effect) {
      hookIndex++;
      effect();
    },
  },
};
const calls = [];
let refreshes = 0;
let requestHandler = function () {
  return Promise.resolve({ available: true });
};
feature.infrastructure = {
  applyManualState(payload) {
    calls.push(payload);
    return requestHandler(payload);
  },
};
vm.runInNewContext(source("application/manual_state_controller.js"), { feature, SDK });
assert.deepEqual(
  JSON.parse(JSON.stringify(feature.manualStateController.targetFor(latest, response))),
  { profileId: "profile:latest", sessionId: "session:latest" },
);
assert.deepEqual(
  JSON.parse(JSON.stringify(feature.manualStateController.targetFor(exact, response))),
  { profileId: "profile:exact", sessionId: "session:exact" },
);

function render(selection, selectedResponse) {
  hookIndex = 0;
  return feature.manualStateController.useManualStateControls(
    selection,
    selectedResponse,
    async function () {
      refreshes += 1;
    },
  );
}

(async function () {
  let model = render(latest, response);
  await model.apply("affect", "valence", -0.25, null);
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0])), {
    profile_id: "profile:latest",
    session_id: "session:latest",
    scope: "affect",
    field: "valence",
    value: -0.25,
    expected_revision: 12,
  });
  assert.equal(refreshes, 1);

  model = render(exact, { available: true, state: { revision: 4 } });
  await model.apply("relationship", "trust", 0.5, "user:one");
  assert.equal(calls[1].profile_id, "profile:exact");
  assert.equal(calls[1].session_id, "session:exact");
  assert.equal(calls[1].participant_id, "user:one");
  assert.equal(calls[1].expected_revision, 4);

  let finishOldRequest;
  requestHandler = function () {
    return new Promise(function (resolve) {
      finishOldRequest = resolve;
    });
  };
  const oldSubmission = model.apply("affect", "valence", 0.1, null);
  model = render(latest, response);
  model = render(exact, { available: true, state: { revision: 8 } });
  finishOldRequest({ available: true });
  await oldSubmission;
  assert.equal(refreshes, 2);

  requestHandler = function () {
    const error = new Error("conflict");
    error.statusCode = 409;
    return Promise.reject(error);
  };
  model = render(exact, { available: true, state: { revision: 8 } });
  const beforeConflictRefresh = refreshes;
  await model.apply("affect", "arousal", 0.4, null);
  model = render(exact, { available: true, state: { revision: 9 } });
  assert.equal(model.resetToken, 1);
  assert.equal(refreshes, beforeConflictRefresh + 1);
  assert.equal(model.statusFor("affect", "arousal", null).status, "conflict");
  console.log("dashboard manual-state controller tests passed");
})().catch(function (error) {
  console.error(error);
  process.exitCode = 1;
});
