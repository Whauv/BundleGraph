import assert from 'node:assert/strict';
import { access, readFile } from 'node:fs/promises';
import test from 'node:test';

const root = new URL('../', import.meta.url);
const indexSource = await readFile(new URL('index.html', root), 'utf8');
const packageJson = JSON.parse(await readFile(new URL('package.json', root), 'utf8'));
const clientSource = await readFile(new URL('src/api/client.ts', root), 'utf8');

test('Vite React is the only frontend entry point', async () => {
  assert.match(indexSource, /src="\/src\/main\.tsx"/);
  assert.doesNotMatch(indexSource, /app\.js|styles\.css/);
  await assert.rejects(() => access(new URL('app.js', root)));
  await assert.rejects(() => access(new URL('modules/api-client.js', root)));
});

test('package scripts validate and build the canonical frontend', () => {
  assert.match(packageJson.scripts.check, /lint/);
  assert.match(packageJson.scripts.check, /tsc -b/);
  assert.match(packageJson.scripts.check, /node --test/);
  assert.match(packageJson.scripts.check, /build/);
  assert.equal(packageJson.dependencies.react.startsWith('^19'), true);
});

test('configured demo backend errors cannot silently fall back to fixtures', () => {
  assert.match(clientSource, /if \(!DEMO_API_BASE\) return cloneFixture\(fixture\)/);
  assert.match(clientSource, /Fixture data was not substituted/);
  assert.doesNotMatch(clientSource, /http:\/\/localhost:8000/);
});

test('all browser mutations stay behind the explicit demo API namespace', () => {
  for (const route of [
    '/api/requirements/interpret',
    '/api/requirements/confirm',
    '/api/bundle-plans/generate',
    '/api/bundle-plans/replan',
    '/api/approvals/create',
    '/api/executions/simulate',
  ]) {
    assert.match(clientSource, new RegExp(route.replaceAll('/', '\\/')));
  }
});
