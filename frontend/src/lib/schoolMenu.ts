import type { CapabilityKey } from '$lib/entitlements';

export type SchoolMenuTab = {
  type: 'tab';
  key: string;
  label: string;
  capability?: CapabilityKey;
};

export type SchoolMenuLink = {
  type: 'link' | 'shortcut';
  href: string;
  label: string;
  capability?: CapabilityKey;
};

export type SchoolMenuItem = SchoolMenuTab | SchoolMenuLink;

export type SchoolMenuGroup = {
  key: string;
  label: string;
  items: SchoolMenuItem[];
};

export const SCHOOL_MENU_GROUPS: SchoolMenuGroup[] = [
  {
    key: 'structure',
    label: 'school.menu.groups.structure',
    items: [
      { type: 'tab', key: 'checklist', label: 'school.tabs.checklist' },
      { type: 'tab', key: 'settings', label: 'school.tabs.settings' },
      { type: 'tab', key: 'branches', label: 'school.tabs.branches' },
      { type: 'tab', key: 'years', label: 'school.tabs.years' },
      { type: 'tab', key: 'stages', label: 'school.tabs.stages' },
      { type: 'tab', key: 'levels', label: 'school.tabs.levels' },
      { type: 'tab', key: 'sections', label: 'school.tabs.sections' }
    ]
  },
  {
    key: 'teaching',
    label: 'school.menu.groups.teaching',
    items: [
      { type: 'link', href: '/school/staff', label: 'staffManagement.title' },
      { type: 'tab', key: 'rosters', label: 'school.tabs.rosters' },
      { type: 'tab', key: 'teachers', label: 'school.tabs.teachers' },
      { type: 'tab', key: 'subjects', label: 'school.tabs.subjects' },
      { type: 'tab', key: 'defaults', label: 'school.tabs.defaults' },
      { type: 'tab', key: 'groups', label: 'school.tabs.groups' }
    ]
  },
  {
    key: 'students',
    label: 'school.menu.groups.students',
    items: [
      { type: 'link', href: '/school/students', label: 'school.tabs.students' },
      { type: 'link', href: '/school/students/data', label: 'school.studentData.title', capability: 'student_staff_import_export' }
    ]
  },
  {
    key: 'communication',
    label: 'school.menu.groups.communication',
    items: [
      { type: 'tab', key: 'announcements', label: 'school.tabs.announcements', capability: 'notices_calendar' },
      { type: 'tab', key: 'calendar', label: 'school.tabs.calendar', capability: 'notices_calendar' }
    ]
  },
  {
    key: 'behaviour',
    label: 'school.menu.groups.behaviour',
    items: [
      { type: 'tab', key: 'behaviour', label: 'school.tabs.behaviour', capability: 'behaviour_points' },
      { type: 'shortcut', href: '/school/reports', label: 'nav.reports', capability: 'reports_insights' },
      { type: 'shortcut', href: '/school/recognition', label: 'school.menu.positiveRecognition', capability: 'positive_recognition' }
    ]
  },
  {
    key: 'system',
    label: 'school.menu.groups.system',
    items: [
      { type: 'shortcut', href: '/school/administration', label: 'nav.administration' }
    ]
  }
];

export const SCHOOL_TABS = SCHOOL_MENU_GROUPS.flatMap((group) =>
  group.items.filter((item): item is SchoolMenuTab => item.type === 'tab')
);

export function visibleSchoolMenuGroups(capabilities: string[]): SchoolMenuGroup[] {
  return SCHOOL_MENU_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.capability || capabilities.includes(item.capability))
  })).filter((group) => group.items.length > 0);
}
