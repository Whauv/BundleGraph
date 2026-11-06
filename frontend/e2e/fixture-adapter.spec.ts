import { expect, test } from '@playwright/test';
import { createFixtureAdapter, FixtureContractError } from '../src/api/fixtureAdapter';

test.beforeEach(async ({}, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('fixture-'), 'fixture-only contract');
});

test('invalid fixture confirmation fails instead of substituting a sample', async () => {
  const fixture = createFixtureAdapter();
  const interpretation = await fixture.interpret('Unsupported studio request', 'req-invalid');
  await expect(fixture.confirm('req-invalid', interpretation.version || 1)).rejects.toMatchObject({
    reason_code: 'CLARIFICATION_REQUIRED', status: 422,
  } satisfies Partial<FixtureContractError>);
});

test('fixture persistence and recovery validate selected current-plan offers', async () => {
  const fixture = createFixtureAdapter();
  await fixture.interpret('I want to start a two-person podcast with my USB-C laptop. My equipment budget is $600, and I need microphones, headphones, and all required cables.', 'req-standard');
  const saved = await fixture.saveGuided({ request_reference: 'req-standard', use_case: 'two-person podcast', participants: 2, budget_minor: 60000, currency: 'USD', laptop_connectors: ['usb-c'], monitoring: 'independent' });
  const confirmed = await fixture.confirm('req-standard', saved.version);
  const generated = await fixture.generate(confirmed);
  const selected = generated.result.proposals[1];
  const plan = await fixture.persist(confirmed, selected.proposal_key);
  expect(plan.plan_id).toBe(selected.proposal_key);
  await expect(fixture.replan(plan, 'offer-not-in-plan')).rejects.toMatchObject({ reason_code: 'INVALID_RECOVERY_TARGET' });
});
