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
    createElement(type, props) {
      return {
        type: type,
        props: props || {},
        children: Array.prototype.slice.call(arguments, 2).reduce(function (items, child) {
          return items.concat(Array.isArray(child) ? child : [child]);
        }, []),
      };
    },
  },
};

vm.runInNewContext(source("domain/state.js"), { feature });
vm.runInNewContext(source("presentation/session_navigator.js"), { feature, SDK });

function findAll(node, type) {
  if (!node || typeof node !== "object") return [];
  const matches = node.type === type ? [node] : [];
  return matches.concat(
    node.children.reduce(function (items, child) {
      return items.concat(findAll(child, type));
    }, [])
  );
}

function textContent(node) {
  if (node === null || node === undefined) return "";
  if (typeof node === "string") return node;
  return node.children.map(textContent).join("");
}

const sharedSessionOne = {
  profileId: "bot:one",
  sessionId: "shared-session",
  updatedAt: "2026-09-21T10:00:00+00:00",
  revision: 4,
  mood: "guarded",
  posture: "terse",
  modelVersion: 2,
};
const sharedSessionTwo = { ...sharedSessionOne, profileId: "bot:two", revision: 5 };
const longSession = {
  ...sharedSessionOne,
  sessionId: "session-with-a-very-long-retained-identifier-1234567890",
};
let refreshSessionsCalled = 0;
let loadMoreSessionsCalled = 0;
const model = {
  selection: feature.domain.latestSelection(),
  sessions: [sharedSessionOne, longSession, sharedSessionTwo],
  catalog: { hasMore: true },
  catalogLoading: false,
  catalogError: null,
  selectedStateLoading: false,
  selectedStateError: null,
  selected: null,
  returnedToLatest: 0,
  refreshSessions() {
    refreshSessionsCalled += 1;
  },
  loadMoreSessions() {
    loadMoreSessionsCalled += 1;
  },
  selectSession(selection) {
    this.selected = selection;
  },
  returnToLatest() {
    this.returnedToLatest += 1;
  },
};

let tree = feature.presentationSessionNavigator.SessionNavigator({ model });
let select = findAll(tree, "select")[0];
assert.equal(select.props.value, "latest");
assert.equal(select.children[0].type, "option");
assert.equal(textContent(select.children[0]), "Latest session");
assert.equal(select.children[1].type, "optgroup");
assert.equal(select.children[1].props.label, "bot:one");
assert.equal(select.children[2].props.label, "bot:two");
assert.equal(select.children[1].children[0].props.value, JSON.stringify(["bot:one", "shared-session"]));
assert.equal(select.children[2].children[0].props.value, JSON.stringify(["bot:two", "shared-session"]));
assert.equal(textContent(select.children[1].children[1]), "bot:one / session-with…r-1234567890");
assert.equal(
  select.children[1].children[1].props.title,
  "bot:one / session-with-a-very-long-retained-identifier-1234567890"
);

select.props.onChange({
  target: { value: JSON.stringify(["bot:two", "shared-session"]) },
});
assert.equal(
  JSON.stringify(model.selected),
  JSON.stringify({ mode: "exact", profileId: "bot:two", sessionId: "shared-session" })
);

select.props.onChange({ target: { value: "latest" } });
assert.equal(model.returnedToLatest, 1);

const buttons = findAll(tree, "button");
buttons[0].props.onClick();
buttons[1].props.onClick();
assert.equal(refreshSessionsCalled, 1);
assert.equal(loadMoreSessionsCalled, 1);

model.selection = feature.domain.exactSelection("bot:two", "shared-session");
model.selectedStateError = { kind: "unavailable" };
tree = feature.presentationSessionNavigator.SessionNavigator({ model });
select = findAll(tree, "select")[0];
assert.equal(select.props.value, JSON.stringify(["bot:two", "shared-session"]));
assert.equal(
  textContent(findAll(tree, "p").find(function (node) {
    return node.props.className === "ha-session-identity";
  })),
  "Selected: bot:two / shared-session"
);
assert.equal(textContent(findAll(tree, "p").find(function (node) {
  return node.props.className === "ha-session-status";
})), "Selected session unavailable.");

const validMissingModel = {
  ...model,
  sessions: [sharedSessionOne],
  selectedStateError: null,
};
tree = feature.presentationSessionNavigator.SessionNavigator({ model: validMissingModel });
select = findAll(tree, "select")[0];
const validMissingOption = select.children[2].children[0];
assert.equal(validMissingOption.props.value, JSON.stringify(["bot:two", "shared-session"]));
assert.equal(validMissingOption.props.disabled, undefined);
assert.equal(textContent(validMissingOption), "bot:two / shared-session");

const unavailableModel = { ...model, sessions: [sharedSessionOne] };
tree = feature.presentationSessionNavigator.SessionNavigator({ model: unavailableModel });
select = findAll(tree, "select")[0];
const unavailableOption = select.children[2].children[0];
assert.equal(unavailableOption.props.value, JSON.stringify(["bot:two", "shared-session"]));
assert.equal(unavailableOption.props.disabled, true);
assert.equal(textContent(unavailableOption), "bot:two / shared-session (unavailable)");
assert.equal(
  JSON.stringify(feature.presentationSessionNavigator.selectionFromOption("invalid")),
  JSON.stringify(feature.domain.latestSelection())
);

console.log("dashboard session navigator tests passed");
