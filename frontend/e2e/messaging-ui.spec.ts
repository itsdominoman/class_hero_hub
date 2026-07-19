import { expect, test, type Page, type Route } from '@playwright/test';

const conversationId = '00000000-0000-4000-8000-000000000101';
const existingMessageId = '00000000-0000-4000-8000-000000000102';
const photoId = '00000000-0000-4000-8000-000000000104';
const pixelPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64'
);

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
  staff_context: { relationship: 'homeroom_teacher', subjects: [] },
  participants: ['Aisha Al Balushi', 'Fatma Al Balushi'],
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

async function mockSession(page: Page, accountId = 5) {
  await page.route('**/api/me', async (route) => {
    await route.fulfill({
      json: {
        id: accountId,
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
            { kind: 'chh_guardian', side: 'guardian', display_name: 'Aisha Al Balushi', relationship: 'mother', active: true },
            { kind: 'chh_guardian', side: 'guardian', display_name: 'Fatma Al Balushi', relationship: 'guardian', active: true }
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
          sender_is_self: true,
          body: body.body,
          photos: (body.staged_media_ids || []).map((id: string, index: number) => ({
            id,
            sort_order: index,
            state: 'attached',
            content_type: 'image/jpeg',
            full_bytes: 1200,
            thumbnail_bytes: 200,
            width: 100,
            height: 80,
            thumbnail_width: 100,
            thumbnail_height: 80,
            thumbnail_available: true,
            full_available: true
          })),
          state: 'active',
          urgent: false,
          created_at: '2026-07-17T08:02:00Z',
          duplicate: false
        }
      });
      return;
    }
    if (path.endsWith(`/conversations/${conversationId}/media`) && request.method() === 'POST') {
      expect(request.headers()['x-upload-id']).toBeTruthy();
      await route.fulfill({
        status: 201,
        json: { id: photoId, state: 'ready', duplicate: false }
      });
      return;
    }
    if (path.includes(`/conversations/${conversationId}/media/${photoId}/`)) {
      await route.fulfill({
        contentType: 'image/png',
        headers: { 'Cache-Control': 'private, no-store, max-age=0', 'X-Content-Type-Options': 'nosniff' },
        body: pixelPng
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
    if (path.endsWith('/conversations') && request.method() === 'POST') {
      expect(request.postDataJSON()).toEqual({ kind: 'student_staff', student_id: 91 });
      await route.fulfill({ json: { conversation_id: conversationId, status: 'active' } });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: 'Not found' } });
  });
}

async function mockTeacherAssignment(page: Page) {
  await page.route('**/api/teach/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/teach/assignments/77')) {
      await route.fulfill({
        json: {
          assignment: {
            id: 77,
            role: 'homeroom',
            target_type: 'class_section',
            school: { id: 7, name: 'Al Noor School' },
            class_section: { id: 12, name: 'KG1A' },
            subject_group: null,
            subject: null,
            branch: null,
            academic_year: null,
            grade_level: { id: 2, name: 'KG1' }
          },
          student_count: 1,
          students: [{
            id: 91,
            first_name: 'Mariam',
            last_name: 'Al Harthy',
            display_name: 'Mariam Al Harthy',
            avatar_url_256: null,
            points_total: 4
          }]
        }
      });
      return;
    }
    if (url.pathname.endsWith('/teach/behaviour/quick-actions')) {
      await route.fulfill({
        json: {
          quick_actions: { positive: [], needs_work: [] },
          other_actions: { positive: [], needs_work: [] }
        }
      });
      return;
    }
    if (url.pathname.endsWith('/teach/homework')) {
      await route.fulfill({ json: { items: [] } });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: 'Not found' } });
  });
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('familyHeroHub.language', 'en'));
  await mockSession(page);
});

test('Quick Award opens the existing guardian conversation and returns after send without losing student context', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockTeacherAssignment(page);
  await mockEnabledMessaging(page);
  let createRequests = 0;
  page.on('request', (request) => {
    if (request.method() === 'POST' && new URL(request.url()).pathname.endsWith('/messaging/conversations')) {
      createRequests += 1;
    }
  });

  await page.goto('/teach/assignments/77');
  await page.getByRole('button', { name: 'Award behaviour to Mariam Al Harthy' }).click();
  const shortcut = page.getByTestId('quick-award-message-guardians');
  await expect(shortcut).toBeEnabled();
  await shortcut.click();

  await expect(page).toHaveURL(new RegExp(`/messages\\?.*conversation=${conversationId}.*membership=51.*shortcut=quick-award`));
  expect(createRequests).toBe(1);
  const notice = page.getByTestId('conversation-information-panel');
  if (await notice.isVisible()) await page.getByRole('button', { name: 'I understand' }).click();
  const composer = page.getByRole('textbox', { name: 'Message', exact: true });
  await composer.fill('Quick Award follow-up');
  await page.getByTestId('message-send').click();

  await expect(page).toHaveURL('/teach/assignments/77?quick_award_student=91&quick_award_mode=quick');
  await expect(page.getByRole('dialog').getByRole('heading', { name: 'Mariam Al Harthy' })).toBeVisible();
  await expect(page.getByTestId('quick-award-message-guardians')).toBeVisible();
  expect(createRequests).toBe(1);
});

test('deep link loads the staff thread and reconciles a stable optimistic send', async ({ page }) => {
  await mockEnabledMessaging(page);
  await page.goto(`/messages?conversation=${conversationId}`);

  await expect(page.getByRole('heading', { name: 'Mariam Al Harthy · KG1A' })).toBeVisible();
  await expect(page.getByText('Homeroom · 2 guardians', { exact: true })).toBeVisible();
  const thread = page.locator('section[aria-label*="Mariam Al Harthy"]');
  const notice = page.getByTestId('conversation-information-panel');
  await expect(notice.getByRole('heading', { name: 'Conversation visibility and safeguarding' })).toBeVisible();
  await expect(notice.getByText('All currently authorized guardians for this student share this conversation.')).toBeVisible();
  await expect(notice.getByText(/School administrators may review school communications/)).toBeVisible();
  await expect(notice.getByText('Aisha Al Balushi · Mother', { exact: true })).toBeVisible();
  await expect(notice.getByText('Fatma Al Balushi · Guardian', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'I understand' }).click();
  await expect(notice).toHaveCount(0);
  const informationButton = page.getByRole('button', { name: 'Conversation information' });
  await expect(informationButton).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('chh.messaging.conversation-notice.s25j.user.5'))).toBe('acknowledged');
  await expect(thread.getByText('Aisha Al Balushi · Mother')).toBeVisible();
  await expect(thread.getByText('Please review the homework')).toBeVisible();

  const composer = page.getByRole('textbox', { name: 'Message', exact: true });
  await composer.fill('Thank you — I will follow up.');
  await composer.press('Control+Enter');
  await expect(thread.getByText('Thank you — I will follow up.')).toBeVisible();
  await expect(thread.getByText('Failed')).toHaveCount(0);

  await page.reload();
  await expect(page.getByTestId('conversation-information-panel')).toHaveCount(0);
  await page.getByRole('button', { name: 'Conversation information' }).click();
  await expect(page.getByTestId('conversation-information-panel').getByText('Fatma Al Balushi · Guardian', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Close', exact: true }).click();

  await page.unroute('**/api/me');
  await mockSession(page, 6);
  await page.reload();
  await expect(page.getByRole('button', { name: 'I understand' })).toBeVisible();
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

test('photo-only browser flow stages, sends, loads a thumbnail, and closes the protected viewer with Back', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let thumbnailRequests = 0;
  let fullRequests = 0;
  await page.on('request', (request) => {
    if (request.url().endsWith(`/${photoId}/thumbnail`)) thumbnailRequests += 1;
    if (request.url().endsWith(`/${photoId}/full`)) fullRequests += 1;
  });
  await mockEnabledMessaging(page);
  await page.goto(`/messages?conversation=${conversationId}`);

  const gallery = page.getByLabel('Choose photos').locator('input[type="file"]');
  await gallery.setInputFiles({ name: 'camera-spoof.txt', mimeType: 'text/plain', buffer: pixelPng });
  await expect(page.getByText('Ready', { exact: true })).toBeVisible();

  const sendRequest = page.waitForRequest((request) =>
    request.method() === 'POST' && request.url().endsWith(`/conversations/${conversationId}/messages`)
  );
  await page.getByTestId('message-send').click();
  const sent = await sendRequest;
  expect(sent.postDataJSON()).toMatchObject({ body: null, staged_media_ids: [photoId] });

  const photo = page.getByRole('button', { name: 'Message photo 1' });
  await expect(photo).toBeVisible();
  expect(thumbnailRequests).toBe(1);
  expect(fullRequests).toBe(0);
  await photo.click();
  await expect(page.getByRole('dialog', { name: 'Protected photo viewer' })).toBeVisible();
  await expect.poll(() => fullRequests).toBe(1);
  const handled = await page.evaluate(() =>
    !window.dispatchEvent(new CustomEvent('chh:native-back', { cancelable: true }))
  );
  expect(handled).toBe(true);
  await expect(page.getByRole('dialog', { name: 'Protected photo viewer' })).toHaveCount(0);
});

test('Android-sized composer honors bottom insets, keyboard resize, and ordered native Back', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockEnabledMessaging(page);
  await page.goto(`/messages?conversation=${conversationId}`);
  await page.addStyleTag({ content: ':root { --safe-bottom: 24px !important; }' });

  const form = page.getByTestId('message-composer');
  const composer = page.getByRole('textbox', { name: 'Message', exact: true });
  const send = page.getByTestId('message-send');
  const initialLayout = await form.evaluate((element) => {
    const formRect = element.getBoundingClientRect();
    const inputRect = element.querySelector('textarea')!.getBoundingClientRect();
    const style = getComputedStyle(element);
    return {
      formBottom: formRect.bottom,
      inputBottom: inputRect.bottom,
      viewportHeight: window.innerHeight,
      paddingBottom: Number.parseFloat(style.paddingBottom),
      position: style.position
    };
  });
  expect(initialLayout.position).toBe('sticky');
  expect(initialLayout.paddingBottom).toBeGreaterThanOrEqual(36);
  expect(initialLayout.formBottom).toBeLessThanOrEqual(initialLayout.viewportHeight + 1);
  expect(initialLayout.viewportHeight - initialLayout.inputBottom).toBeGreaterThanOrEqual(24);
  const sendBox = await send.boundingBox();
  expect(sendBox?.width).toBeGreaterThanOrEqual(48);
  expect(sendBox?.height).toBeGreaterThanOrEqual(48);

  await composer.fill('Draft survives resize and Back');
  await composer.focus();
  await composer.evaluate((element: HTMLTextAreaElement) => element.setSelectionRange(6, 14));
  await page.setViewportSize({ width: 390, height: 560 });
  const resized = await page.getByTestId('messaging-workspace').evaluate((element) => ({
    bottom: element.getBoundingClientRect().bottom,
    viewportHeight: window.innerHeight
  }));
  expect(resized.bottom).toBeLessThanOrEqual(resized.viewportHeight + 1);
  await expect(composer).toHaveValue('Draft survives resize and Back');
  expect(await composer.evaluate((element: HTMLTextAreaElement) => ({
    focused: document.activeElement === element,
    start: element.selectionStart,
    end: element.selectionEnd
  }))).toEqual({ focused: true, start: 6, end: 14 });

  const keyboardBackHandled = await page.evaluate(() =>
    !window.dispatchEvent(new CustomEvent('chh:native-back', { cancelable: true }))
  );
  expect(keyboardBackHandled).toBe(true);
  await expect(composer).toHaveValue('Draft survives resize and Back');
  expect(await composer.evaluate((element) => document.activeElement === element)).toBe(false);
  await expect(page.locator('section[aria-label*="Mariam Al Harthy"]')).toBeVisible();

  const threadBackHandled = await page.evaluate(() =>
    !window.dispatchEvent(new CustomEvent('chh:native-back', { cancelable: true }))
  );
  expect(threadBackHandled).toBe(true);
  await expect(page.getByRole('heading', { name: 'Messages' })).toBeVisible();
  await page.getByRole('list', { name: 'Conversation list' }).getByRole('button').first().click();
  await expect(page.getByRole('textbox', { name: 'Message', exact: true }))
    .toHaveValue('Draft survives resize and Back');

  await page.getByRole('button', { name: 'Open menu' }).click();
  await expect(page.getByRole('dialog', { name: 'Menu' })).toBeVisible();
  const menuBackHandled = await page.evaluate(() =>
    !window.dispatchEvent(new CustomEvent('chh:native-back', { cancelable: true }))
  );
  expect(menuBackHandled).toBe(true);
  await expect(page.getByRole('dialog', { name: 'Menu' })).toHaveCount(0);
  await expect(page.getByRole('textbox', { name: 'Message', exact: true }))
    .toHaveValue('Draft survives resize and Back');
});

test('mobile Arabic layout preserves RTL chrome, mixed content, and safe back navigation', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => localStorage.setItem('familyHeroHub.language', 'ar'));
  await mockEnabledMessaging(page);
  await page.goto(`/messages?conversation=${conversationId}`);

  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByRole('heading', { name: 'Mariam Al Harthy' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'رؤية المحادثة وحماية الطلبة' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'فهمت' })).toBeVisible();
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
