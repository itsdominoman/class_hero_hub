import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(
  new URL("../src/routes/school/surveys/[id]/+page.svelte", import.meta.url),
  "utf8",
);

test("free-text search stays bounded and stacks on narrow screens", () => {
  assert.match(
    source,
    /class="flex w-full min-w-0 flex-col gap-2 sm:w-auto sm:flex-row"/,
  );
  assert.match(
    source,
    /class="min-w-0 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm sm:w-56"/,
  );
  assert.match(
    source,
    /class="w-full shrink-0 rounded-xl bg-slate-900 px-4 py-2 text-xs font-black text-white sm:w-auto"/,
  );
});
