"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const feature = {};
const componentSlots = new Map();
let activeComponent = null;
let currentModel = null;

const SDK = {
  React: {
    createElement(type, props, ...children) {
      return {
        type: type,
        props: props || {},
        children: children.flatMap(function (child) {
          return Array.isArray(child) ? child : [child];
        }),
      };
    },
  },
  components: {
    Card: "Card",
    CardContent: "CardContent",
    CardHeader: "CardHeader",
    CardTitle: "CardTitle",
    Badge: "Badge",
  },
  utils: {
    isoTimeAgo() {
      return "just now";
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

function source(relativePath) {
  return fs.readFileSync(path.join(__dirname, "..", "src", relativePath), "utf8");
}

[
  "domain/state.js",
  "application/tuning_controller.js",
  "presentation/primitives.js",
  "presentation/session_navigator.js",
  "presentation/state_summary.js",
  "presentation/state_view.js",
  "presentation/tuning_controls.js",
  "presentation/manual_state_controls.js",
  "presentation/adjust_view.js",
  "presentation/page.js",
].forEach(function (relativePath) {
  vm.runInNewContext(source(relativePath), { feature: feature, SDK: SDK });
});

feature.application = {
  useDashboardState() {
    return currentModel;
  },
};

const Page = feature.presentation.createPage(null);

function stateFor(sessionId, revision, valence, effectiveGain) {
  return {
    profileId: "bot:one",
    sessionId: sessionId,
    revision: revision,
    updatedAt: "2026-09-24T08:00:00+00:00",
    mood: "warm",
    posture: "warm_engagement",
    modelVersion: 2,
    migrationRequired: false,
    expressionDrive: 0.45,
    atmosphere: 0.2,
    atmosphereSource: 0.2,
    affect: { valence: valence, arousal: 0.3, frustration: 0.1, offended: 0.05 },
    relationships: [
      {
        id: "user:alpha",
        trust: 0.1,
        affinity: 0.2,
        respect: 0.3,
        irritation: 0,
        tension: 0.1,
        unresolvedTension: 0.1,
      },
      {
        id: "user:beta",
        trust: 0.4,
        affinity: 0.5,
        respect: 0.6,
        irritation: 0.1,
        tension: 0.2,
        unresolvedTension: 0.2,
      },
    ],
    sensitivities: ["dismissal"],
    conflicts: [],
    tuning: [["expression_gain", effectiveGain]],
    tuningConfiguration: {
      available: true,
      configuredExpressionGain: 1,
      effectiveExpressionGain: effectiveGain,
      overrideExpressionGain: effectiveGain,
    },
  };
}

function modelFor(state) {
  const selection = feature.domain.exactSelection(state.profileId, state.sessionId);
  const target = { profileId: state.profileId, sessionId: state.sessionId };
  return {
    response: { available: true, state: state, controlsEnabled: true },
    selection: selection,
    sessions: [],
    catalog: { hasMore: false },
    catalogLoading: false,
    catalogError: null,
    selectedStateLoading: false,
    selectedStateError: null,
    hasMatchingResponse: true,
    hasError: false,
    controlsEnabled: true,
    manualTarget: target,
    tuningTarget: target,
    tuningStatus: null,
    tuningError: null,
    tuningResetToken: 0,
    manualPending: false,
    manualResetToken: 0,
    manualStatusFor() {
      return null;
    },
    applyManualState() {},
    applyExpressionGain() {},
    restoreExpressionGain() {},
    refreshSessions() {},
    loadMoreSessions() {},
    returnToLatest() {},
    selectSession() {},
  };
}

function renderNode(value, pathName) {
  if (Array.isArray(value)) return value.map((item, index) => renderNode(item, pathName + "/" + index));
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
    children: (value.children || []).map(function (child, index) {
      const key = child && child.props && child.props.key ? ":" + child.props.key : "";
      return renderNode(child, pathName + "/" + index + key);
    }),
  });
}

function renderPage() {
  return renderNode({ type: Page, props: {} }, "page");
}

function elements(value) {
  if (Array.isArray(value)) return value.flatMap(elements);
  if (!value || typeof value !== "object") return [];
  const children = Array.isArray(value.children) ? value.children : [];
  return [value].concat(children.flatMap(elements));
}

function textContent(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string" || typeof value === "number") return String(value);
  return (value.children || []).map(textContent).join("");
}

function button(tree, label, className) {
  return elements(tree).find(function (item) {
    return (
      item.type === "button" &&
      textContent(item) === label &&
      (!className || item.props.className === className)
    );
  });
}

function valenceInput(tree) {
  return elements(tree).find(function (item) {
    return item.type === "input" && item.props.id === "ha-manual-affect-valence-number";
  });
}

function sessionIdentity(tree) {
  return elements(tree).find((item) => item.props.id === "ha-session-identity");
}

function activateAdjust(tree) {
  const adjust = button(tree, "Adjust");
  assert.ok(adjust, "Adjust tab should be available");
  adjust.props.onClick();
  return renderPage();
}

function testTabsDefaultAndFeatureGate() {
  componentSlots.clear();
  currentModel = modelFor(stateFor("session:one", 4, 0.2, 2));
  let tree = renderPage();
  let tabs = elements(tree).filter((item) => item.props.role === "tab");
  assert.deepEqual(tabs.map(textContent), ["State", "Adjust"]);
  assert.equal(tabs[0].props["aria-selected"], true, "State is the default tab");
  assert.equal(tabs[1].props["aria-selected"], false);

  tabs[1].props.onClick();
  tree = renderPage();
  assert.equal(button(tree, "Adjust").props["aria-selected"], true);

  currentModel.controlsEnabled = false;
  tree = renderPage();
  tabs = elements(tree).filter((item) => item.props.role === "tab");
  assert.deepEqual(tabs.map(textContent), ["State"], "the feature gate hides Adjust");
  assert.equal(tabs[0].props["aria-selected"], true, "the feature gate returns to State");

  currentModel.controlsEnabled = true;
  currentModel.response.state.modelVersion = 1;
  tree = renderPage();
  tabs = elements(tree).filter((item) => item.props.role === "tab");
  assert.deepEqual(tabs.map(textContent), ["State"], "legacy state cannot enter Adjust");
}

function testTargetChangeReturnsToState() {
  componentSlots.clear();
  currentModel = modelFor(stateFor("session:one", 4, 0.2, 2));
  let tree = activateAdjust(renderPage());
  assert.equal(button(tree, "Adjust").props["aria-selected"], true);

  const next = stateFor("session:two", 1, -0.3, 1);
  currentModel = Object.assign(modelFor(next), {
    selection: feature.domain.exactSelection(next.profileId, next.sessionId),
  });
  tree = renderPage();
  assert.equal(button(tree, "State").props["aria-selected"], true);
  assert.equal(button(tree, "Adjust").props["aria-selected"], false);
}

function testLatestShowsOnlyTheCurrentMatchingIdentity() {
  componentSlots.clear();
  currentModel = modelFor(stateFor("session:latest-one", 4, 0.2, 2));
  currentModel.selection = feature.domain.latestSelection();
  let tree = renderPage();
  assert.match(textContent(sessionIdentity(tree)), /Latest session — bot:one \/ session:latest-one/);

  currentModel.hasMatchingResponse = false;
  currentModel.selectedStateLoading = true;
  tree = renderPage();
  assert.equal(textContent(sessionIdentity(tree)), "Selected: Latest session");
  assert.doesNotMatch(textContent(sessionIdentity(tree)), /session:latest-one/);

  const nextState = stateFor("session:latest-two", 1, -0.3, 1);
  currentModel.response.state = nextState;
  currentModel.hasMatchingResponse = true;
  currentModel.selectedStateLoading = false;
  tree = renderPage();
  assert.match(textContent(sessionIdentity(tree)), /Latest session — bot:one \/ session:latest-two/);
  assert.doesNotMatch(textContent(sessionIdentity(tree)), /session:latest-one/);

  currentModel.hasMatchingResponse = false;
  currentModel.selectedStateError = { kind: "unavailable" };
  tree = renderPage();
  assert.equal(textContent(sessionIdentity(tree)), "Selected: Latest session");
  assert.doesNotMatch(textContent(sessionIdentity(tree)), /session:latest-two/);
}

function testDraftsSurviveTabsGroupsAndPolling() {
  componentSlots.clear();
  currentModel = modelFor(stateFor("session:one", 4, 0.2, 2));
  let tree = activateAdjust(renderPage());
  let input = valenceInput(tree);
  assert.equal(input.props.value, "0.2");
  input.props.onChange({ target: { value: "0.72" } });
  tree = renderPage();
  assert.equal(valenceInput(tree).props.value, "0.72");

  button(tree, "State").props.onClick();
  tree = renderPage();
  assert.equal(button(tree, "State").props["aria-selected"], true);
  tree = activateAdjust(tree);
  assert.equal(valenceInput(tree).props.value, "0.72", "tab switches retain unsaved values");

  button(tree, "Atmosphere", "ha-adjust-groups__button").props.onClick();
  tree = renderPage();
  assert.equal(valenceInput(tree).props.value, "0.72", "hidden groups remain mounted");

  const latestPoll = stateFor("session:one", 5, -0.4, 2.8);
  currentModel.response.state = latestPoll;
  currentModel.response.state.tuningConfiguration.effectiveExpressionGain = 2.8;
  currentModel.response.state.tuningConfiguration.overrideExpressionGain = 2.8;
  tree = renderPage();
  assert.equal(valenceInput(tree).props.value, "0.72", "routine polls retain manual drafts");

  button(tree, "Expression", "ha-adjust-groups__button").props.onClick();
  tree = renderPage();
  const number = elements(tree).find(
    (item) => item.type === "input" && item.props.id === "ha-expression-gain-number"
  );
  number.props.onChange({ target: { value: "3.7" } });
  tree = renderPage();
  const range = elements(tree).find(
    (item) => item.type === "input" && item.props.id === "ha-expression-gain-range"
  );
  assert.equal(range.props.value, "3.7", "numeric input synchronizes the slider");

  const nextPoll = stateFor("session:one", 6, 0.1, 3);
  currentModel.response.state = nextPoll;
  tree = renderPage();
  const updatedNumber = elements(tree).find(
    (item) => item.type === "input" && item.props.id === "ha-expression-gain-number"
  );
  assert.equal(updatedNumber.props.value, "3.7", "polls do not discard expression drafts");
}

function testFieldFeedbackAndSingleVisibleGroup() {
  componentSlots.clear();
  currentModel = modelFor(stateFor("session:one", 4, 0.2, 2));
  let fieldStatus = "conflict";
  currentModel.manualStatusFor = function (scope, field) {
    return scope === "affect" && field === "valence" ? { status: fieldStatus } : null;
  };
  let tree = activateAdjust(renderPage());
  let visibleGroups = elements(tree).filter(
    (item) => item.props.className === "ha-adjust-panel" && item.props.hidden !== true
  );
  assert.equal(visibleGroups.length, 1, "only one adjustment group is visible");
  assert.match(textContent(tree), /Revision conflict/);

  const input = valenceInput(tree);
  input.props.onChange({ target: { value: "2" } });
  tree = renderPage();
  assert.match(textContent(tree), /Enter a number from -1 to 1/);
  assert.equal(valenceInput(tree).props["aria-invalid"], true);

  valenceInput(tree).props.onChange({ target: { value: "0.3" } });
  fieldStatus = "saving";
  tree = renderPage();
  assert.match(textContent(tree), /Saving this value/);

  button(tree, "Expression", "ha-adjust-groups__button").props.onClick();
  currentModel.tuningStatus = "unavailable";
  currentModel.tuningError = "The selected session is unavailable.";
  tree = renderPage();
  assert.match(textContent(tree), /selected session is unavailable/i);
}

function testStateRelationshipSelectionTracksParticipants() {
  componentSlots.clear();
  const state = stateFor("session:one", 4, 0.2, 2);
  state.relationships = [];
  currentModel = modelFor(state);
  let tree = renderPage();
  const participantSelect = function (root) {
    return elements(root).find(
      (item) => item.type === "select" && item.props.id === "ha-state-participant-select"
    );
  };
  assert.equal(participantSelect(tree), undefined, "empty relationship state has no selector");

  const first = { id: "user:alpha", trust: 0, affinity: 0, respect: 0, irritation: 0, tension: 0 };
  const second = { id: "user:beta", trust: 0, affinity: 0, respect: 0, irritation: 0, tension: 0 };
  const third = { id: "user:gamma", trust: 0, affinity: 0, respect: 0, irritation: 0, tension: 0 };
  state.relationships = [first];
  tree = renderPage();
  assert.equal(participantSelect(tree).props.value, "user:alpha", "first participant appears selected");

  state.relationships = [first, second];
  tree = renderPage();
  assert.equal(participantSelect(tree).props.value, "user:alpha", "adding another retains selection");
  participantSelect(tree).props.onChange({ target: { value: "user:beta" } });
  tree = renderPage();
  assert.equal(participantSelect(tree).props.value, "user:beta", "user selection is retained");

  state.relationships = [first, second, third];
  tree = renderPage();
  assert.equal(participantSelect(tree).props.value, "user:beta", "routine polls retain selection");
  state.relationships = [first, third];
  tree = renderPage();
  assert.equal(participantSelect(tree).props.value, "user:alpha", "removed selection falls back");
}

function testResponsiveStructure() {
  const root = path.join(__dirname, "..", "src", "presentation");
  const responsive = fs.readFileSync(path.join(root, "responsive.css"), "utf8");
  const layout = fs.readFileSync(path.join(root, "layout.css"), "utf8");
  const controls = fs.readFileSync(path.join(root, "controls.css"), "utf8");
  assert.match(responsive, /max-width:\s*520px/);
  assert.match(controls, /flex-wrap:\s*wrap/);
  assert.match(responsive, /min-width:\s*0/);
  assert.doesNotMatch(layout + controls + responsive, /position:\s*sticky/i);
  assert.doesNotMatch(layout + controls + responsive, /min-height:\s*310px/);
}

testTabsDefaultAndFeatureGate();
testTargetChangeReturnsToState();
testLatestShowsOnlyTheCurrentMatchingIdentity();
testDraftsSurviveTabsGroupsAndPolling();
testFieldFeedbackAndSingleVisibleGroup();
testStateRelationshipSelectionTracksParticipants();
testResponsiveStructure();
console.log("dashboard presentation tests passed");
