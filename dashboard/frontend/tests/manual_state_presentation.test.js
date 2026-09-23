"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const feature = {};
const source = function (relativePath) {
  return fs.readFileSync(path.join(__dirname, "..", "src", relativePath), "utf8");
};
const componentSlots = new Map();
let activeComponent = null;
const SDK = {
  React: {
    createElement(type, props, ...children) {
      return { type: type, props: props || {}, children: children };
    },
  },
  hooks: {
    useState(initial) {
      const component = activeComponent;
      const index = component.index++;
      if (!(index in component.slots)) component.slots[index] = initial;
      return [component.slots[index], function (next) {
        component.slots[index] = typeof next === "function" ? next(component.slots[index]) : next;
      }];
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
vm.runInNewContext(source("domain/state.js"), { feature });
const applied = [];
let refreshes = 0;
feature.infrastructure = {
  applyManualState(payload) {
    applied.push(payload);
    return Promise.resolve({ available: true });
  },
};
vm.runInNewContext(source("application/manual_state_controller.js"), { feature, SDK });
vm.runInNewContext(source("presentation/manual_state_controls.js"), { feature, SDK });

const state = {
  modelVersion: 2,
  profileId: "profile:latest",
  sessionId: "session:full-id",
  revision: 14,
  affect: { valence: 0.1, arousal: 0.2, frustration: 0.3, offended: 0.4 },
  atmosphereSource: 0.5,
  relationships: [
    {
      id: "user:complete-identifier",
      trust: 0.1,
      affinity: 0.2,
      respect: 0.3,
      irritation: 0.4,
      unresolvedTension: 0.5,
    },
  ],
};

function DashboardControls(props) {
  const response = { available: true, state: props.state };
  const selection = feature.domain.exactSelection(props.state.profileId, props.state.sessionId);
  const manual = feature.manualStateController.useManualStateControls(
    selection,
    response,
    async function () {
      refreshes += 1;
    }
  );
  const model = {
    controlsEnabled: true,
    manualTarget: manual.target,
    manualPending: manual.pending,
    manualResetToken:
      props.manualResetToken === undefined ? manual.resetToken : props.manualResetToken,
    manualStatusFor: manual.statusFor,
    applyManualState: manual.apply,
  };
  return SDK.React.createElement(feature.presentationManualStateControls.ManualStateControls, {
    model: model,
    state: props.state,
  });
}
function renderNode(value, pathName) {
  if (Array.isArray(value)) {
    return value.map(function (item, index) {
      return renderNode(item, pathName + "/" + index);
    });
  }
  if (!value || typeof value !== "object") return value;
  if (typeof value.type === "function") {
    const key = value.props && value.props.key ? ":" + value.props.key : "";
    const componentKey = pathName + key;
    if (!componentSlots.has(componentKey)) componentSlots.set(componentKey, []);
    const previous = activeComponent;
    activeComponent = { slots: componentSlots.get(componentKey), index: 0 };
    const output = value.type(value.props);
    activeComponent = previous;
    return renderNode(output, componentKey + "/output");
  }
  return Object.assign({}, value, {
    children: (value.children || []).map(function (item, index) {
      const key = item && item.props && item.props.key ? ":" + item.props.key : "";
      return renderNode(item, pathName + "/" + index + key);
    }),
  });
}

function manualTree(currentState, manualResetToken) {
  return renderNode(
    {
      type: DashboardControls,
      props: { state: currentState, manualResetToken: manualResetToken },
    },
    "root"
  );
}

function elements(value) {
  if (Array.isArray(value)) return value.flatMap(elements);
  if (!value || typeof value !== "object") return [];
  const children = Array.isArray(value.children) ? value.children : [];
  return [value].concat(children.flatMap(elements));
}

function isValenceNumber(item) {
  return (
    item.type === "input" &&
    item.props.id.includes("manual-affect-valence-") &&
    item.props.id.endsWith("-number")
  );
}

function participantSelect(tree) {
  return elements(tree).find(function (item) {
    return item.type === "select" && item.props.id === "ha-manual-participant-select";
  });
}

async function testApplyUsesTheDashboardModelAndExactTarget() {
  componentSlots.clear();
  let tree = manualTree(state);
  let all = elements(tree);
  const inputs = all.filter(function (item) {
    return item.type === "input";
  });
  let buttons = all.filter(function (item) {
    return item.type === "button";
  });
  assert.equal(inputs.length, 20);
  assert.equal(buttons.length, 10);
  assert.equal(all.some((item) => item.children.includes("user:complete-identifier")), true);
  assert.equal(all.some((item) => item.children.includes("Manual state controls")), true);
  assert.equal(all.some((item) => item.children.includes("Calm")), false);
  assert.equal(all.some((item) => item.children.includes("Reset")), false);
  assert.equal(all.some((item) => item.children.includes("Revision 14")), true);
  assert.equal(applied.length, 0);

  const valenceInput = all.find(isValenceNumber);
  valenceInput.props.onChange({ target: { value: "0.75" } });
  assert.equal(applied.length, 0, "editing a draft must not autosave");
  tree = manualTree(
    Object.assign({}, state, { affect: Object.assign({}, state.affect, { valence: -0.2 }) })
  );
  let updatedInputs = elements(tree).filter(isValenceNumber);
  assert.equal(updatedInputs[0].props.value, "0.75", "routine state polling must preserve a draft");

  const resetState = Object.assign({}, state, {
    affect: Object.assign({}, state.affect, { valence: 0.35 }),
  });
  tree = manualTree(resetState, 1);
  tree = manualTree(resetState, 1);
  updatedInputs = elements(tree).filter(isValenceNumber);
  assert.equal(updatedInputs[0].props.value, "0.35", "a conflict reset must use the refreshed value");

  updatedInputs[0].props.onChange({ target: { value: "0.75" } });
  tree = manualTree(resetState, 1);
  buttons = elements(tree).filter(function (item) {
    return item.type === "button";
  });
  await buttons[0].props.onClick();
  assert.equal(applied.length, 1, "Apply must make exactly one request");
  assert.deepEqual(JSON.parse(JSON.stringify(applied[0])), {
    profile_id: "profile:latest",
    session_id: "session:full-id",
    scope: "affect",
    field: "valence",
    value: 0.75,
    expected_revision: 14,
  });

  const trustInput = elements(tree).find(function (item) {
    return (
      item.type === "input" &&
      item.props.id.includes("manual-relationship-trust-") &&
      item.props.id.endsWith("-number")
    );
  });
  trustInput.props.onChange({ target: { value: "0.8" } });
  tree = manualTree(resetState, 1);
  buttons = elements(tree).filter(function (item) {
    return item.type === "button";
  });
  await buttons[5].props.onClick();
  assert.equal(applied.length, 2, "each Apply submits one source field");
  assert.deepEqual(JSON.parse(JSON.stringify(applied[1])), {
    profile_id: "profile:latest",
    session_id: "session:full-id",
    scope: "relationship",
    field: "trust",
    value: 0.8,
    expected_revision: 14,
    participant_id: "user:complete-identifier",
  });
  assert.equal(refreshes, 2);
}

function relationship(id) {
  return {
    id: id,
    trust: 0,
    affinity: 0,
    respect: 0,
    irritation: 0,
    unresolvedTension: 0,
  };
}

function testRelationshipSelectionTracksAvailableParticipants() {
  componentSlots.clear();
  const participantA = relationship("user:a");
  const participantB = relationship("user:b");
  const participantC = relationship("user:c");
  let relationshipState = Object.assign({}, state, { relationships: [] });
  let tree = manualTree(relationshipState);
  assert.equal(
    participantSelect(tree),
    undefined,
    "no selector is shown for an empty relationship list"
  );

  relationshipState = Object.assign({}, relationshipState, { relationships: [participantA] });
  tree = manualTree(relationshipState);
  assert.equal(participantSelect(tree).props.value, "user:a", "the first new participant is selected");

  relationshipState = Object.assign({}, relationshipState, { relationships: [participantA, participantB] });
  tree = manualTree(relationshipState);
  assert.equal(
    participantSelect(tree).props.value,
    "user:a",
    "adding a participant preserves selection"
  );
  participantSelect(tree).props.onChange({ target: { value: "user:b" } });
  tree = manualTree(Object.assign({}, relationshipState, { revision: 15 }));
  assert.equal(participantSelect(tree).props.value, "user:b", "polling retains a valid user selection");

  relationshipState = Object.assign({}, relationshipState, {
    relationships: [participantA, participantB, participantC],
  });
  tree = manualTree(relationshipState);
  assert.equal(
    participantSelect(tree).props.value,
    "user:b",
    "adding another participant retains selection"
  );
  relationshipState = Object.assign({}, relationshipState, { relationships: [participantA, participantC] });
  tree = manualTree(relationshipState);
  assert.equal(participantSelect(tree).props.value, "user:a", "removing the selection falls back to the first");
  tree = manualTree(relationshipState);
  assert.equal(participantSelect(tree).props.value, "user:a", "the fallback remains selected on later polls");
}

function testEditingControlsStayHiddenWhenDisabled() {
  const hidden = feature.presentationManualStateControls.ManualStateControls({
    model: { controlsEnabled: false },
    state,
  });
  assert.equal(hidden, null);
}

(async function () {
  await testApplyUsesTheDashboardModelAndExactTarget();
  testRelationshipSelectionTracksAvailableParticipants();
  testEditingControlsStayHiddenWhenDisabled();
  console.log("dashboard manual-state presentation tests passed");
})().catch(function (error) {
  console.error(error);
  process.exitCode = 1;
});
