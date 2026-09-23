"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const feature = {};
const source = function (relativePath) {
  return fs.readFileSync(path.join(__dirname, "..", "src", relativePath), "utf8");
};
let hookIndex = 0;
const hookSlots = [];
const timers = new Map();
let nextTimerId = 1;
const SDK = {
  hooks: {
    useState(initial) {
      const index = hookIndex++;
      if (!(index in hookSlots)) hookSlots[index] = initial;
      return [hookSlots[index], function (value) {
        hookSlots[index] = typeof value === "function" ? value(hookSlots[index]) : value;
      }];
    },
    useRef(initial) {
      const index = hookIndex++;
      if (!(index in hookSlots)) hookSlots[index] = { current: initial };
      return hookSlots[index];
    },
    useEffect(effect, dependencies) {
      const index = hookIndex++;
      const previous = hookSlots[index];
      const changed =
        !previous ||
        dependencies.some(function (dependency, offset) {
          return dependency !== previous.dependencies[offset];
        });
      if (changed) {
        hookSlots[index] = { dependencies: dependencies.slice(), cleanup: effect() };
      }
    },
  },
};
const fakeWindow = {
  setTimeout(callback) {
    const id = nextTimerId++;
    timers.set(id, callback);
    return id;
  },
  clearTimeout(id) {
    timers.delete(id);
  },
};
vm.runInNewContext(source("domain/state.js"), { feature });
vm.runInNewContext(source("application/state_polling.js"), {
  feature,
  SDK,
  window: fakeWindow,
});

const deferred = [];
const calls = [];
feature.infrastructure = {
  loadState(selection) {
    calls.push(selection);
    return new Promise(function (resolve) {
      deferred.push(resolve);
    });
  },
};
const latest = feature.domain.latestSelection();
const preflight = feature.domain.normalizeResponse({
  available: true,
  state: { profile_id: "profile:one", session_id: "session:one", revision: 3 },
});

function render() {
  hookIndex = 0;
  return feature.statePolling.useSelectedState(preflight, latest);
}

function settle() {
  return new Promise(function (resolve) {
    setImmediate(resolve);
  });
}

(async function () {
  let model = render();
  const [timerId, runPoll] = timers.entries().next().value;
  timers.delete(timerId);
  runPoll();
  assert.equal(calls.length, 1);

  const queuedRefresh = model.refreshNow();
  assert.equal(calls.length, 1);
  deferred[0]({
    available: true,
    state: { profile_id: "profile:one", session_id: "session:one", revision: 4 },
  });
  await settle();
  assert.equal(calls.length, 2, "a refresh requested during polling must run immediately afterward");

  deferred[1]({
    available: true,
    state: { profile_id: "profile:one", session_id: "session:one", revision: 5 },
  });
  await settle();
  await queuedRefresh;
  model = render();
  assert.equal(model.response.state.revision, 5);
  console.log("dashboard queued-refresh controller tests passed");
})().catch(function (error) {
  console.error(error);
  process.exitCode = 1;
});
