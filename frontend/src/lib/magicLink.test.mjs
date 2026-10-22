import test from "node:test";
import assert from "node:assert/strict";

import { magicDestination } from "./magicLink.js";

test("the message link opens the thread it names", () => {
  assert.equal(magicDestination("/messages/64f0c0ffee"), "/messages/64f0c0ffee");
});

test("no next, or an unsafe one, opens the inbox", () => {
  assert.equal(magicDestination(null), "/messages");
  assert.equal(magicDestination(""), "/messages");
  assert.equal(magicDestination("https://evil.example/messages"), "/messages");
  assert.equal(magicDestination("//evil.example"), "/messages");
});
