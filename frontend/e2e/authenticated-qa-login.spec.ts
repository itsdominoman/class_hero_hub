import { expect, test } from '@playwright/test';

const qaToken = process.env.QA_LOGIN_TOKEN?.trim();
const qaLoginBaseUrl = process.env.QA_LOGIN_API_BASE_URL?.trim() || 'http://127.0.0.1:8000';

if (!qaToken) {
  throw new Error('QA_LOGIN_TOKEN is required for authenticated browser QA');
}

test.describe('Europe dev authenticated QA login', () => {
  test('logs in through the dev-only QA helper and loads the parent dashboard', async ({ page }) => {
    await page.goto('/');

    const loginUrl = new URL('/api/dev/qa-login', qaLoginBaseUrl);

    const loginResponse = await page.request.post(loginUrl.toString(), {
      data: { token: qaToken }
    });

    expect(loginResponse.status()).toBe(200);
    const loginBody = await loginResponse.text();
    expect(loginBody).toContain('"status":"ok"');
    expect(loginBody).toContain('"email":"qa-parent@dev.familyherohub.com"');

    const loginCookies = loginResponse
      .headersArray()
      .filter((header) => header.name.toLowerCase() === 'set-cookie')
      .map((header) => header.value)
      .map((cookieHeader) => cookieHeader.split(';', 1)[0])
      .map((cookiePair) => {
        const separatorIndex = cookiePair.indexOf('=');
        return {
          name: cookiePair.slice(0, separatorIndex),
          value: cookiePair.slice(separatorIndex + 1)
        };
      });

    await page.context().addCookies(
      loginCookies.map((cookie) => ({
        ...cookie,
        url: qaLoginBaseUrl
      }))
    );

    await page.route('**/api/**', async (route) => {
      const requestUrl = new URL(route.request().url());
      const backendUrl = new URL(`${requestUrl.pathname}${requestUrl.search}`, qaLoginBaseUrl);
      const backendResponse = await route.fetch({ url: backendUrl.toString() });
      await route.fulfill({ response: backendResponse });
    });

    await page.goto('/parent', { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: 'My Family' })).toBeVisible();
    await expect(page.getByText('QA Parent', { exact: false })).toBeVisible();
  });
});
