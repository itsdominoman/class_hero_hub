import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  accessSummaryKey,
  conversationKindLabelKey,
  isMeaningfulJustification,
  permissionDescriptionKey,
  permissionLabelKey,
  roleLabelKey,
  SAFEGUARDING_PERMISSIONS,
} from "../src/lib/safeguarding/presentation.ts";

const searchSource = readFileSync(
  new URL(
    "../src/routes/school/safeguarding/message-reviews/+page.svelte",
    import.meta.url,
  ),
  "utf8",
);
const reviewSource = readFileSync(
  new URL(
    "../src/routes/school/safeguarding/message-reviews/[sessionId]/+page.svelte",
    import.meta.url,
  ),
  "utf8",
);
const permissionsSource = readFileSync(
  new URL(
    "../src/routes/school/safeguarding/permissions/+page.svelte",
    import.meta.url,
  ),
  "utf8",
);

test("review justification rejects trivial and punctuation-only content in English and Arabic", () => {
  assert.equal(isMeaningfulJustification("blah"), false);
  assert.equal(isMeaningfulJustification("!!!!!!!!!!!!!!!!!!!!"), false);
  assert.equal(isMeaningfulJustification("                 "), false);
  assert.equal(isMeaningfulJustification("aaaaaaaaaaaaaaaaaaaa"), false);
  assert.equal(isMeaningfulJustification("Reported concern for review"), true);
  assert.equal(
    isMeaningfulJustification("مراجعة بلاغ حماية محدد للطالب"),
    true,
  );
});

test("presentation mappings provide friendly translation keys for every protected value", () => {
  for (const permission of SAFEGUARDING_PERMISSIONS) {
    assert.match(
      permissionLabelKey(permission),
      /^safeguarding\.permissionLabels\./,
    );
    assert.match(
      permissionDescriptionKey(permission),
      /^safeguarding\.permissionDescriptions\./,
    );
  }
  assert.equal(roleLabelKey("school_admin"), "safeguarding.roles.schoolAdmin");
  assert.equal(roleLabelKey("fhh_parent"), "safeguarding.roles.guardian");
  assert.equal(
    conversationKindLabelKey("staff_direct"),
    "safeguarding.conversationKinds.staffConversation",
  );
  assert.equal(
    accessSummaryKey(SAFEGUARDING_PERMISSIONS),
    "safeguarding.accessLevels.full",
  );
});

test("safeguarding routes remain separated and the review projection has no composer or receipt endpoint", () => {
  assert.doesNotMatch(
    searchSource,
    /loadPermissions|permission-checklist-form|grantPermission/,
  );
  assert.match(searchSource, /advanced-filters-toggle/);
  assert.match(searchSource, /start-review-dialog/);
  assert.match(permissionsSource, /permission-checklist-form/);
  assert.match(permissionsSource, /permissionLabelKey\(permission\)/);
  assert.doesNotMatch(permissionsSource, />\{permission\}</);
  assert.doesNotMatch(
    reviewSource,
    /ComposeDialog|MessageComposer|sendMessage|acknowledgeDelivery|acknowledgeRead|\/acknowledgements/,
  );
  assert.match(reviewSource, /safeguarding-review-workspace/);
});
