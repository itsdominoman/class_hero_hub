#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { chromium } = require('/opt/apps/family-hero-hub/frontend/node_modules/playwright');

const ROOT = '/opt/apps/family-hero-hub';
const DEFAULT_BACKEND = process.env.QA_LOGIN_API_BASE_URL || 'http://127.0.0.1:8000';
const DEFAULT_FRONTEND = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:5173';
const SCREENSHOT_DIR = '/home/administrator/remotion/fhh-video-workspace/assets/screenshots/captured';
const VIEWPORT = { width: 1080, height: 1920 };

function fail(message, extra = {}) {
  const payload = { ok: false, error: message, ...extra };
  console.log(JSON.stringify(payload, null, 2));
  process.exit(1);
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function readToken(kind) {
  if (kind === 'child') {
    return (process.env.QA_CHILD_LOGIN_TOKEN || process.env.QA_LOGIN_TOKEN || '').trim();
  }
  return (process.env.QA_LOGIN_TOKEN || '').trim();
}

function parseSetCookies(headersArray) {
  return headersArray
    .filter((header) => header.name.toLowerCase() === 'set-cookie')
    .map((header) => {
      const parts = header.value.split(';').map((p) => p.trim());
      const [name, ...rest] = parts[0].split('=');
      return { name, value: rest.join('='), url: DEFAULT_BACKEND };
    });
}

function createLocalQaSession(kind) {
  const email = kind === 'child' ? (process.env.QA_CHILD_EMAIL || 'qa-child@dev.familyherohub.com') : 'qa-parent@dev.familyherohub.com';
  const name = kind === 'child' ? (process.env.QA_CHILD_NAME || 'QA Seed Child') : (process.env.QA_LOGIN_NAME || 'QA Parent');
  const py = `
import json
from datetime import datetime, timezone
from app.database import SessionLocal
from app import models, auth

db = SessionLocal()
email = ${JSON.stringify(email)}
name = ${JSON.stringify(name)}
parent = db.query(models.ParentUser).filter(models.ParentUser.email.ilike(email)).first()
if parent is None:
    family = models.Family()
    db.add(family)
    db.flush()
    parent = models.ParentUser(email=email, name=name, google_sub=f'capture:{email}', family_id=family.id, last_login_at=datetime.now(timezone.utc))
    db.add(parent)
    db.commit()
    db.refresh(parent)
elif parent.family_id is None:
    family = models.Family()
    db.add(family)
    db.flush()
    parent.family_id = family.id
    parent.name = name
    parent.google_sub = f'capture:{email}'
    parent.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(parent)
else:
    parent.name = name
    parent.google_sub = f'capture:{email}'
    parent.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(parent)
access_token = auth.create_access_token({'sub': parent.email})
csrf_token = auth.create_csrf_token()
print(json.dumps({'email': parent.email, 'access_token': access_token, 'csrf_token': csrf_token, 'family_id': parent.family_id}))
`;
  const raw = execFileSync('docker', ['exec', '-e', 'PYTHONPATH=/app', 'family-hero-hub-backend', 'python', '-c', py], {
    cwd: ROOT,
    encoding: 'utf8'
  }).trim();
  return JSON.parse(raw);
}

async function loginAndRoute(page, kind) {
  const loginPath = kind === 'child' ? '/api/dev/qa-child-login' : '/api/dev/qa-login';
  let cookies = [];
  let csrfToken = '';

  const token = readToken(kind);
  if (token) {
    const loginRes = await page.request.post(new URL(loginPath, DEFAULT_BACKEND).toString(), {
      data: { token }
    });
    if (loginRes.ok()) {
      cookies = parseSetCookies(loginRes.headersArray());
      const csrfCookie = cookies.find((cookie) => cookie.name === 'csrf_token');
      if (csrfCookie) {
        csrfToken = csrfCookie.value;
      }
    }
  }

  if (cookies.length === 0) {
    const localSession = createLocalQaSession(kind);
    csrfToken = localSession.csrf_token;
    cookies = [
      { name: 'access_token', value: localSession.access_token, url: DEFAULT_BACKEND },
      { name: 'csrf_token', value: localSession.csrf_token, url: DEFAULT_BACKEND }
    ];
  }

  const urls = [DEFAULT_BACKEND, DEFAULT_FRONTEND];
  await page.context().addCookies(
    urls.flatMap((url) => cookies.map((cookie) => ({ ...cookie, url })))
  );

  await page.route('**/api/**', async (route) => {
    const requestUrl = new URL(route.request().url());
    const backendUrl = new URL(`${requestUrl.pathname}${requestUrl.search}`, DEFAULT_BACKEND);
    const headers = {
      ...route.request().headers(),
      ...(csrfToken ? { 'x-csrf-token': csrfToken } : {})
    };
    try {
      const response = await route.fetch({ url: backendUrl.toString(), headers });
      await route.fulfill({ response });
    } catch (error) {
      try { await route.abort(); } catch (_) { /* ignore */ }
    }
  });

  return { csrfToken };
}

async function capture(page, flowName, index, options = {}) {
  const fileName = `${flowName}-${String(index).padStart(2, '0')}.png`;
  const filePath = path.join(SCREENSHOT_DIR, fileName);
  await page.screenshot({ path: filePath, fullPage: false });
  return filePath;
}

async function waitForStableUi(page) {
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(750);
}

async function captureParentDashboard(page, flowName) {
  await loginAndRoute(page, 'parent');
  await page.goto(new URL('/parent', DEFAULT_FRONTEND).toString(), { waitUntil: 'domcontentloaded' });
  await waitForStableUi(page);
  return [await capture(page, flowName, 1)];
}

async function captureAddChildFlow(page, flowName) {
  const { csrfToken } = await loginAndRoute(page, 'parent');
  await page.goto(new URL('/parent', DEFAULT_FRONTEND).toString(), { waitUntil: 'domcontentloaded' });
  await waitForStableUi(page);

  const shots = [];
  shots.push(await capture(page, flowName, 1));

  const addChildButton = page.getByRole('button', { name: /add child/i }).first();
  if (await addChildButton.count().catch(() => 0)) {
    await addChildButton.click().catch(() => {});
    await waitForStableUi(page);
  }

  const childName = `Ari ${new Date().toISOString().slice(0, 19).replace(/[:T-]/g, '')}`;
  const formVisible = await page.getByText(/add child/i).isVisible().catch(() => false);
  if (formVisible) {
    shots.push(await capture(page, flowName, 2));
  }

  const nameField = page.locator('input[name="display_name"], input[name="name"], input[placeholder*="name" i]').first();
  if (await nameField.count().catch(() => 0)) {
    await nameField.fill(childName).catch(() => {});
  }

  const submitButton = page.getByRole('button', { name: /create|save|add/i }).first();
  if (await submitButton.count().catch(() => 0)) {
    await submitButton.click().catch(() => {});
    await waitForStableUi(page);
  }

  const childVisible = await page.getByText(childName, { exact: false }).isVisible().catch(() => false);
  if (!childVisible) {
    await page.request.post(new URL('/api/children/', DEFAULT_BACKEND).toString(), {
      data: { display_name: childName, avatar_name: '1', active: true },
      headers: csrfToken ? { 'x-csrf-token': csrfToken } : {}
    });
    await page.goto(new URL('/parent', DEFAULT_FRONTEND).toString(), { waitUntil: 'domcontentloaded' });
    await waitForStableUi(page);
  }

  shots.push(await capture(page, flowName, 3));
  return shots;
}

async function captureChildDashboard(page, flowName) {
  await loginAndRoute(page, 'child');
  const childRoute = process.env.QA_CHILD_ROUTE || '/child';
  await page.goto(new URL(childRoute, DEFAULT_FRONTEND).toString(), { waitUntil: 'domcontentloaded' });
  await waitForStableUi(page);
  return [await capture(page, flowName, 1)];
}

async function captureGenericParentFlow(page, flowName, route = '/parent') {
  await loginAndRoute(page, 'parent');
  await page.goto(new URL(route, DEFAULT_FRONTEND).toString(), { waitUntil: 'domcontentloaded' });
  await waitForStableUi(page);
  return [await capture(page, flowName, 1)];
}

const FLOW_HANDLERS = {
  'parent-dashboard': captureParentDashboard,
  'add-child-flow': captureAddChildFlow,
  'child-dashboard': captureChildDashboard,
  rewards: async (page, flowName) => captureGenericParentFlow(page, flowName),
  'reward-request': async (page, flowName) => captureGenericParentFlow(page, flowName),
  allowance: async (page, flowName) => captureGenericParentFlow(page, flowName),
  'parent-tools': async (page, flowName) => captureGenericParentFlow(page, flowName, '/parent/settings'),
  'parent-settings': async (page, flowName) => captureGenericParentFlow(page, flowName, '/parent/settings')
};

async function main() {
  const flowName = process.argv[2];
  if (!flowName || !FLOW_HANDLERS[flowName]) {
    fail('Usage: capture_fhh_screenshots.js <flow-name>', { supported_flows: Object.keys(FLOW_HANDLERS) });
  }

  ensureDir(SCREENSHOT_DIR);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: VIEWPORT, deviceScaleFactor: 1, isMobile: true });
  const page = await context.newPage();

  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') {
      errors.push(message.text());
    }
  });

  try {
    const screenshots = await FLOW_HANDLERS[flowName](page, flowName);
    const manifest = { ok: true, flow: flowName, screenshots, errors };
    console.log(JSON.stringify(manifest, null, 2));
    await browser.close();
  } catch (error) {
    await browser.close().catch(() => {});
    fail('Screenshot capture failed', { flow: flowName, error: error.message, errors });
  }
}

main().catch((error) => fail('Unhandled error', { error: error.message }));
