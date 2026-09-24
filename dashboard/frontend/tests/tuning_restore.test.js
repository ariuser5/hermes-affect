"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const feature = {};
const componentSlots = new Map();
let activeComponent = null;
const SDK = {
  React: {
    createElement(type, props, ...children) {
      return { type, props: props || {}, children };
    },
  },
  hooks: {
    useState(initial) {
      const component = activeComponent;
      const index = component.index++;
      if (!(index in component.slots)) component.slots[index] = initial;
      return [
        component.slots[index],
        function (next) {
          component.slots[index] =
            typeof next === "function" ? next(component.slots[index]) : next;
        },
      ];
    },
    useRef(initial) {
      const component = activeComponent;
      const index = component.index++;
      if (!(index in component.slots)) component.slots[index] = { current: initial };
      return component.slots[index];
    },
    useEffect(effect, dependencies) {
      const component = activeComponent;
      const index = component.index++;
      const previous = component.slots[index];
      const changed =
        !previous ||
        dependencies.some(function (dependency, offset) {
          return dependency !== previous[offset];
        });
      if (changed) {
        component.slots[index] = dependencies.slice();
        effect();
      }
    },
  },
};

function load(relativePath) {
  const file = path.join(__dirname, "..", "src", relativePath);
  vm.runInNewContext(fs.readFileSync(file, "utf8"), { feature: feature, SDK: SDK });
}

load("domain/state.js");
load("application/tuning_controller.js");
load("presentation/tuning_controls.js");

function renderNode(value, pathName) {
  if (Array.isArray(value)) return value.map((item, index) => renderNode(item, pathName + "/" + index));
  if (!value || typeof value !== "object") return value;
  if (typeof value.type === "function") {
    const componentKey = pathName;
    if (!componentSlots.has(componentKey)) componentSlots.set(componentKey, []);
    const previous = activeComponent;
    activeComponent = { slots: componentSlots.get(componentKey), index: 0 };
    const output = value.type(value.props);
    activeComponent = previous;
    return renderNode(output, componentKey + "/output");
  }
  return Object.assign({}, value, {
    children: (value.children || []).map(function (child, index) {
      return renderNode(child, pathName + "/" + index);
    }),
  });
}

function elements(value) {
  if (!value || typeof value !== "object") return [];
  const children = Array.isArray(value.children) ? value.children : [];
  return [value].concat(children.flatMap(elements));
}

function textContent(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string" || typeof value === "number") return String(value);
  return (value.children || []).map(textContent).join("");
}

function findInput(tree, id) {
  return elements(tree).find(function (item) {
    return item.type === "input" && item.props.id === id;
  });
}

function findButton(tree, label) {
  return elements(tree).find(function (item) {
    return item.type === "button" && textContent(item) === label;
  });
}

async function testRestoreResetsDraftToRefreshedConfiguredValue() {
  const selection = feature.domain.exactSelection("bot:one", "session:restore");
  let response = {
    available: true,
    controlsEnabled: true,
    state: {
      profileId: "bot:one",
      sessionId: "session:restore",
      revision: 8,
      tuningConfiguration: {
        available: true,
        configuredExpressionGain: 1.25,
        effectiveExpressionGain: 4.5,
        overrideExpressionGain: 4.5,
      },
    },
  };
  const restoreCalls = [];
  feature.infrastructure = {
    restoreExpressionGain: async function (target, revision) {
      restoreCalls.push({ target: target, revision: revision });
    },
  };

  async function refreshState() {
    response = {
      available: true,
      controlsEnabled: true,
      state: {
        profileId: "bot:one",
        sessionId: "session:restore",
        revision: 9,
        tuningConfiguration: {
          available: true,
          configuredExpressionGain: 1.25,
          effectiveExpressionGain: 1.25,
          overrideExpressionGain: null,
        },
      },
    };
  }

  function App() {
    const tuning = feature.tuningController.useTuningControls(selection, response, refreshState);
    const model = {
      controlsEnabled: true,
      tuningTarget: tuning.target,
      tuningStatus: tuning.status,
      tuningError: tuning.error,
      tuningResetToken: tuning.resetToken,
      applyExpressionGain: tuning.applyExpressionGain,
      restoreExpressionGain: tuning.restoreExpressionGain,
    };
    return SDK.React.createElement(feature.presentationTuningControls.TuningControls, {
      model: model,
      state: response.state,
    });
  }

  function render() {
    return renderNode({ type: App, props: {} }, "app");
  }

  let tree = render();
  tree = render();
  assert.equal(findInput(tree, "ha-expression-gain-number").props.value, "4.5");
  assert.equal(findInput(tree, "ha-expression-gain-range").props.value, "4.5");
  assert.equal(findButton(tree, "Apply").props.disabled, true);

  await findButton(tree, "Restore configured value").props.onClick();
  assert.equal(restoreCalls.length, 1);
  assert.equal(restoreCalls[0].target.profileId, "bot:one");
  assert.equal(restoreCalls[0].target.sessionId, "session:restore");
  assert.equal(restoreCalls[0].revision, 8);

  tree = render();
  tree = render();
  assert.equal(findInput(tree, "ha-expression-gain-number").props.value, "1.25");
  assert.equal(findInput(tree, "ha-expression-gain-range").props.value, "1.25");
  assert.equal(findButton(tree, "Apply").props.disabled, true);
  assert.equal(findButton(tree, "Restore configured value").props.disabled, true);
  assert.match(textContent(tree), /Saved for this session/);
}

testRestoreResetsDraftToRefreshedConfiguredValue().then(function () {
  console.log("dashboard tuning restore interaction test passed");
}).catch(function (error) {
  console.error(error);
  process.exitCode = 1;
});
