import assert from "node:assert/strict";
import test from "node:test";

import { allocateSlug, validateSignalDefinition } from "./signal-definitions.ts";

test("a title becomes a url slug that avoids built-in and saved signals", () => {
  assert.equal(allocateSlug("Refund promised late", []), "refund-promised-late");
  assert.equal(allocateSlug("User Frustration", ["user-frustration"]), "user-frustration-2");
  assert.equal(allocateSlug("Task Failure", []), "task-failure-2");
});

test("title and prompt are required", () => {
  assert.deepEqual(validateSignalDefinition({ title: "  ", prompt: "look for refunds" }), {
    ok: false,
    error: "Title is required.",
  });
  assert.deepEqual(validateSignalDefinition({ title: "Late refund", prompt: "  " }), {
    ok: false,
    error: "Prompt is required.",
  });
  assert.deepEqual(validateSignalDefinition({ title: "Late refund", prompt: "The agent promised a refund and never sent it." }), {
    ok: true,
    title: "Late refund",
    prompt: "The agent promised a refund and never sent it.",
  });
});
