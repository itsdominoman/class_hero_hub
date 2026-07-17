import { expect, test, type Page, type Route } from '@playwright/test';

const conversationId = '00000000-0000-4000-8000-000000000101';
const existingMessageId = '00000000-0000-4000-8000-000000000102';

const membership = {
  membership_id: 51,
  school_id: 7,
  school_name: 'Al Noor School',
  role: 'teacher'
};

const conversation = {
  id: conversationId,
  kind: 'student_staff',
  status: 'active',
  read_only: false,
  student: {
    id: 91,
    display_name: 'Mariam Al Harthy',
    name_ar: 'مريم الحارثية',
    class_label: 'KG1A',
    class_label_ar: 'الروضة الأولى أ',
    grade_label: 'KG1',
    grade_label_ar: 'الروضة الأولى'
  },
  context: { label: 'Class 4A', label_ar: 'الصف ٤ أ' },
  participants: ['Aisha Al Balushi'],
  last_message: {
    id: existingMessageId,
    sequence: 1,
    sender_display_name: 'Aisha Al Balushi',
    sender_kind: 'chh_guardian',
    sender_relationship: 'mother',
    body: 'Please review the homework',
    state: 'active',
    created_at: '2026-07-17T08:00:00Z'
  },
  last_message_at: '2026-07-17T08:00:00Z',
  unread_count: 1,
  capabilities: {
    can_send: true,
    can_close: false,
    delivery_receipts_visible: false,
    read_receipts_visible: false
  }
};

async function mockSession(page: Page) {
  await page.route('**/api/me', async (route) => {
    await route.fulfill({
      json: {
        id: 5,
        name: 'Teacher One',
        is_platform_admin: false,
        memberships: [membership]
      }
    });
  });
}

async function mockEnabledMessaging(
  page: Page,
  threadConversation = conversation,
  detailStatus = 200,
  messageProvider?: (url: URL) => Promise<unknown> | unknown
) {
  await page.route('**/api/messaging/**', async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    expect(request.headers()['x-school-id']).toBe('7');
    expect(request.headers()['x-membership-id']).toBe('51');

    if (path.endsWith('/unread-count')) {
      await route.fulfill({ json: { total: 1, conversations: 1 } });
      return;
    }
    if (path.endsWith('/inbox')) {
      await route.fulfill({
        json: {
          items: detailStatus === 200 ? [threadConversation] : [],
          next_cursor: null
        }
      });
      return;
    }
    if (path.endsWith(`/conversations/${conversationId}`)) {
      if (detailStatus !== 200) {
        await route.fulfill({
          status: detailStatus,
          json: { detail: 'Conversation not found' }
        });
        return;
      }
      await route.fulfill({
        json: {
          ...threadConversation,
          participant_details: [
            { kind: 'staff', side: 'staff', display_name: 'Teacher One', active: true },
            { kind: 'chh_guardian', side: 'guardian', display_name: 'Aisha Al Balushi', relationship: 'mother', active: true }
          ],
          shared_guardian_visibility: true,
          safeguarding_disclosure: true
        }
      });
      return;
    }
    if (path.endsWith(`/conversations/${conversationId}/messages`) && request.method() === 'GET') {
      if (messageProvider) {
        await route.fulfill({ json: await messageProvider(url) });
        return;
      }
      await route.fulfill({
        json: {
          items: [
            {
              id: existingMessageId,
              sequence: 1,
              sender_display_name: 'Aisha Al Balushi',
              sender_kind: 'chh_guardian',
              sender_relationship: 'mother',
              sender_is_self: false,
              body: 'Please review the homework',
              state: 'active',
              urgent: false,
              created_at: '2026-07-17T08:00:00Z'
            }
          ],
          next_cursor: null,
          latest_sequence: 1
        }
      });
      return;
    }
    if (path.endsWith(`/conversations/${conversationId}/acknowledgements`)) {
      await route.fulfill({
        json: {
          event_type: 'read',
          through_sequence: 1,
          recorded_at: '2026-07-17T08:01:00Z',
          duplicate: false
        }
      });
      return;
    }
    if (path.endsWith(`/conversations/${conversationId}/messages`) && request.method() === 'POST') {
      const body = request.postDataJSON();
      await route.fulfill({
        json: {
          id: '00000000-0000-4000-8000-000000000103',
          sequence: 2,
          sender_display_name: 'Teacher One',
          body: body.body,
          state: 'active',
          urgent: false,
          created_at: '2026-07-17T08:02:00Z',
          duplicate: false
        }
      });
      return;
    }
    if (path.endsWith('/recipients')) {
      await route.fulfill({
        json: {
          students: [
            {
              student_id: 91,
              display_name: 'Mariam Al Harthy',
              name_ar: 'مريم الحارثية',
              guardian_names: ['Aisha Al Balushi']
              ,guardian_details: [{ display_name: 'Aisha Al Balushi', relationship: 'mother' }]
              ,class_label: 'KG1A'
              ,class_label_ar: 'الروضة الأولى أ'
            }
          ],
          staff: []
        }
      });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: 'Not found' } });
  });
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('familyHeroHub.language', 'en'));
  await mockSession(page);
});

test('deep link loads the staff thread and reconciles a stable optimistic send', async ({ page }) => {
  await mockEnabledMessaging(page);
  await page.goto(`/messages?conversation=${conversationId}`);

  await expect(page.getByRole('heading', { name: 'Mariam Al Harthy · KG1A' })).toBeVisible();
  const thread = page.locator('section[aria-label*="Mariam Al Harthy"]');
  await expect(thread.getByText('Aisha Al Balushi', { exact: true })).toBeVisible();
  await expect(thread.getByText('Aisha Al Balushi · Mother')).toBeVisible();
  await expect(thread.getByText('Please review the homework')).toBeVisible();

  const composer = page.getByRole('textbox', { name: 'Message', exact: true });
  await composer.fill('Thank you — I will follow up.');
  await composer.press('Control+Enter');
  await expect(thread.getByText('Thank you — I will follow up.')).toBeVisible();
  await expect(thread.getByText('Failed')).toHaveCount(0);
});

test('resume refresh appends messages without disturbing draft focus, selection, or scroll intent', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const initialItems = Array.from({ length: 18 }, (_, index) => ({
    id: `00000000-0000-4000-8000-${String(index + 200).padStart(12, '0')}`,
    sequence: index + 1,
    sender_display_name: 'Aisha Al Balushi',
    sender_kind: 'chh_guardian',
    sender_relationship: 'mother',
    sender_is_self: false,
    body: `Historical message ${index + 1} ${'content '.repeat(8)}`,
    state: 'active',
    urgent: false,
    created_at: `2026-07-17T08:${String(index).padStart(2, '0')}:00Z`
  }));
  let incrementalRequests = 0;
  await mockEnabledMessaging(page, conversation, 200, async (url) => {
    if (url.searchParams.has('after_sequence')) {
      incrementalRequests += 1;
      await new Promise((resolve) => setTimeout(resolve, 150));
      return {
        items: [{
          id: '00000000-0000-4000-8000-000000000999',
          sequence: 19,
          sender_display_name: 'Dom Brown',
          sender_kind: 'chh_guardian',
          sender_relationship: 'father',
          sender_is_self: false,
          body: 'A newly arrived message',
          state: 'active',
          urgent: false,
          created_at: '2026-07-17T09:00:00Z'
        }],
        next_cursor: null,
        latest_sequence: 19
      };
    }
    return { items: initialItems, next_cursor: null, latest_sequence: 18 };
  });
  await page.goto(`/messages?conversation=${conversationId}`);

  const composer = page.getByRole('textbox', { name: 'Message', exact: true });
  await composer.fill('Draft stays exactly here');
  await composer.focus();
  await composer.evaluate((element: HTMLTextAreaElement) => element.setSelectionRange(6, 11));
  const timeline = page.getByTestId('message-timeline');
  await timeline.evaluate((element) => {
    element.scrollTop = 0;
    element.dispatchEvent(new Event('scroll'));
  });

  await page.evaluate(() => {
    window.dispatchEvent(new Event('chh:app-resume'));
    window.dispatchEvent(new Event('chh:app-resume'));
  });
  await expect(page.getByText('A newly arrived message')).toBeVisible();
  await expect(page.getByText('Dom Brown · Father')).toBeVisible();
  await expect(page.getByRole('button', { name: '1 new messages' })).toBeVisible();
  await expect(composer).toHaveValue('Draft stays exactly here');
  expect(await composer.evaluate((element: HTMLTextAreaElement) => ({
    focused: document.activeElement === element,
    start: element.selectionStart,
    end: element.selectionEnd
  }))).toEqual({ focused: true, start: 6, end: 11 });
  expect(incrementalRequests).toBe(1);
});

test('mobile Arabic layout preserves RTL chrome, mixed content, and safe back navigation', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => localStorage.setItem('familyHeroHub.language', 'ar'));
  await mockEnabledMessaging(page);
  await page.goto(`/messages?conversation=${conversationId}`);

  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByRole('heading', { name: 'Mariam Al Harthy' })).toBeVisible();
  const thread = page.locator('section[aria-label*="Mariam Al Harthy"]');
  await expect(thread.getByText('Please review the homework')).toHaveAttribute('dir', 'auto');
  await page.getByRole('button', { name: 'العودة إلى صندوق الوارد' }).click();
  await expect(page.getByRole('heading', { name: 'الرسائل' })).toBeVisible();
});

test('global or school feature disablement fails closed', async ({ page }) => {
  await page.route('**/api/messaging/**', async (route) => {
    await route.fulfill({ status: 404, json: { detail: 'Messaging is unavailable' } });
  });
  await page.goto('/messages');
  await expect(page.getByRole('heading', { name: 'Messages are not available' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Messages' })).toHaveCount(0);
});

test('closed, offline, and revoked thread states remain explicit and content-safe', async ({ page }) => {
  const closedConversation = {
    ...conversation,
    status: 'closed_assignment_ended',
    read_only: true,
    capabilities: {
      ...conversation.capabilities,
      can_send: false
    }
  };
  await mockEnabledMessaging(page, closedConversation);
  await page.goto(`/messages?conversation=${conversationId}`);
  await expect(page.getByText('Read only', { exact: true })).toBeVisible();
  await expect(
    page.getByText('This conversation is read only because current access or assignment has ended.')
  ).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Message', exact: true })).toBeDisabled();

  await page.evaluate(() => window.dispatchEvent(new Event('offline')));
  await expect(page.getByText('Offline — showing the latest loaded messages')).toBeVisible();

  await page.unroute('**/api/messaging/**');
  await mockEnabledMessaging(page, conversation, 404);
  await page.goto(`/messages?conversation=${conversationId}`);
  await expect(
    page.getByText('Your access to this conversation has changed. The inbox has been refreshed.')
  ).toBeVisible();
  await expect(page.getByText('Please review the homework')).toHaveCount(0);
});
