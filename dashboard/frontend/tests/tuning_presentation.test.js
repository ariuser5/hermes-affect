"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const feature = {};
const source = function (relativePath) {
  return fs.readFileSync(path.join(__dirname, "..", "src", relativePath), "utf8");
};
const SDK = {
  React: {
    createElement(type, props, ...children) {
      return { type, props: props || {}, children };
    },
  },
  hooks: {
    useState(initial) {
      return [initial, function () {}];
    },
    useEffect(effect) {
      effect();
    },
  },
};

vm.runInNewContext(source("domain/state.js"), { feature });
vm.runInNewContext(source("presentation/tuning_controls.js"), { feature, SDK });

const tree = feature.presentationTuningControls.TuningControls({
  model: {
    controlsEnabled: true,
    tuningTarget: { profileId: "bot:one", sessionId: "session:one" },
    tuningStatus: null,
    tuningError: null,
    applyExpressionGain: function () {},
    restoreExpressionGain: function () {},
  },
  state: {
    profileId: "bot:one",
    sessionId: "session:one",
    tuningConfiguration: {
      available: true,
      configuredExpressionGain: 1,
      effectiveExpressionGain: 2.5,
      overrideExpressionGain: 2.5,
    },
  },
});

function elements(value) {
  if (!value || typeof value !== "object") return [];
  const children = Array.isArray(value.children) ? value.children : [];
  return [value].concat(children.flatMap(elements));
}

const all = elements(tree);
const inputs = all.filter(function (item) {
  return item.type === "input";
});
const buttons = all.filter(function (item) {
  return item.type === "button";
});

assert.equal(
  JSON.stringify(
    inputs.map(function (input) {
      return input.props.type;
    })
  ),
  JSON.stringify(["range", "number"]),
);
assert.equal(buttons.length, 2);
assert.equal(all.some((item) => item.children.includes("Session override active")), true);
assert.equal(all.some((item) => item.children.includes("Configured ")), true);
assert.equal(all.some((item) => item.children.includes("Effective ")), true);

console.log("dashboard tuning presentation tests passed");
