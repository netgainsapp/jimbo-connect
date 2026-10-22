import test from "node:test";
import assert from "node:assert/strict";

import { safeNext } from "./nextPath.js";

test("a same site path is honoured, query and all", () => {
  assert.equal(safeNext("/messages/64f0c0ffee"), "/messages/64f0c0ffee");
  assert.equal(safeNext("/messages?tab=new"), "/messages?tab=new");
});

test("an absolute URL on another site falls back", () => {
  assert.equal(safeNext("https://evil.example/messages", "/"), "/");
  assert.equal(safeNext("http://evil.example", "/"), "/");
});

test("a protocol relative or backslash path falls back", () => {
  assert.equal(safeNext("//evil.example", "/"), "/");
  assert.equal(safeNext("/\\evil.example", "/"), "/");
  assert.equal(safeNext("/messages\\..\\x", "/"), "/");
});

test("a scheme falls back", () => {
  assert.equal(safeNext("javascript:alert(1)", "/"), "/");
  assert.equal(safeNext("data:text/html,hi", "/"), "/");
});

test("nothing, a relative path or a non string falls back", () => {
  assert.equal(safeNext(null, "/"), "/");
  assert.equal(safeNext("", "/"), "/");
  assert.equal(safeNext("messages", "/"), "/");
  assert.equal(safeNext(42, "/"), "/");
});

test("the default destination is the events page", () => {
  assert.equal(safeNext(undefined), "/events");
});
