import assert from 'node:assert/strict';
import test from 'node:test';

import {
  capabilityDependents,
  entitlementRelationshipBlock
} from '../src/lib/entitlements.ts';

function entitlement(capability, dependencies = [], overrides = {}) {
  return {
    capability,
    dependencies,
    enabled: true,
    effective_enabled: true,
    source: 'pilot',
    effective_from: '2026-08-01',
    expires_on: null,
    entitlement_version: 1,
    ...overrides
  };
}

test('capability cards can show both what they require and what uses them', () => {
  const rows = [
    entitlement('behaviour_points'),
    entitlement('positive_recognition', ['behaviour_points'])
  ];

  assert.deepEqual(capabilityDependents(rows, 'behaviour_points'), ['positive_recognition']);
  assert.deepEqual(capabilityDependents(rows, 'positive_recognition'), []);
});

test('turning off a feature is blocked while an enabled feature uses it', () => {
  const behaviour = entitlement('behaviour_points', [], { enabled: false });
  const rows = [behaviour, entitlement('positive_recognition', ['behaviour_points'])];

  assert.deepEqual(entitlementRelationshipBlock(rows, behaviour), {
    reason: 'enabled_dependents',
    capability: 'behaviour_points',
    related: ['positive_recognition']
  });
});

test('turning on a feature is blocked until its required feature is on', () => {
  const recognition = entitlement('positive_recognition', ['behaviour_points']);
  const rows = [
    entitlement('behaviour_points', [], { enabled: false, effective_enabled: false }),
    recognition
  ];

  assert.deepEqual(entitlementRelationshipBlock(rows, recognition), {
    reason: 'missing_dependencies',
    capability: 'positive_recognition',
    related: ['behaviour_points']
  });
});

test('availability dates cannot extend beyond a required feature', () => {
  const recognition = entitlement('positive_recognition', ['behaviour_points'], {
    effective_from: '2026-08-01',
    expires_on: '2026-12-31'
  });
  const rows = [
    entitlement('behaviour_points', [], { expires_on: '2026-11-30' }),
    recognition
  ];

  assert.deepEqual(entitlementRelationshipBlock(rows, recognition), {
    reason: 'dependency_window',
    capability: 'positive_recognition',
    related: ['behaviour_points']
  });
});

test('shortening a required feature is blocked when a feature using it runs longer', () => {
  const behaviour = entitlement('behaviour_points', [], { expires_on: '2026-11-30' });
  const rows = [
    behaviour,
    entitlement('positive_recognition', ['behaviour_points'], { expires_on: '2026-12-31' })
  ];

  assert.deepEqual(entitlementRelationshipBlock(rows, behaviour), {
    reason: 'dependency_window',
    capability: 'positive_recognition',
    related: ['behaviour_points']
  });
});
