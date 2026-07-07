export const en = {
  app: {
    name: 'Class Hero Hub',
    classHero: 'Class Hero',
    hub: 'Hub'
  },
  language: {
    label: 'Language',
    english: 'English',
    arabic: 'Arabic',
    help: 'Arabic uses right-to-left layout. Names and school-entered content stay exactly as entered.'
  },
  nav: {
    home: 'Home',
    login: 'Login',
    logout: 'Logout',
    dashboard: 'Dashboard',
    admin: 'Admin',
    product: 'Product',
    support: 'Support',
    legal: 'Legal',
    howItWorks: 'How it works',
    faq: 'FAQ',
    contact: 'Contact',
    safetyPrivacy: 'Safety & Privacy',
    privacyPolicy: 'Privacy Policy',
    terms: 'Terms of Service'
  },
  footer: {
    description: 'Class Hero Hub is a school communication hub for notices, updates, and role-based access between schools and families.',
    tagline: 'Built for school communication. Prepared for role-based access.'
  },
  common: {
    loading: 'Loading',
    copyTodo: 'Copy TODO'
  },
  home: {
    title: 'Class Hero Hub | School communication hub',
    metaDescription: 'A school communication hub for notices, updates, and role-based access.',
    eyebrow: 'School communication hub',
    heading: 'Clear school updates in one trusted place.',
    intro: 'Class Hero Hub helps schools share notices, updates, and essential information with the right people through a focused communication shell.',
    dashboardCta: 'Go to dashboard',
    loginCta: 'Log in',
    howItWorksCta: 'See how it works',
    strapline: 'School notices · Family communication · Role-based access',
    schoolView: 'School view',
    schoolViewTitle: 'Send the right update.',
    schoolViewText: 'A focused shell for school-led communication and administration.',
    familyView: 'Family view',
    familyViewTitle: 'See what matters.',
    familyViewText: 'Families can access school updates when their role is assigned.',
    privateByDesign: 'Access controlled',
    privateByDesignText: 'Identity and tenancy are handled by the backend. The frontend now waits for school roles before showing role-specific tools.',
    whatItDoesEyebrow: 'What it does',
    whatItDoesHeading: 'A cleaner foundation for school communication',
    whatItDoesIntro: 'This frontend shell is being reworked around schools, families, and role-based access.',
    featureCommunicationTitle: 'Communication',
    featureCommunicationText: 'Prepare a central place for school notices and updates.',
    featureCalendarTitle: 'Coordination',
    featureCalendarText: 'Keep future school coordination features anchored in one hub.',
    featureAdminTitle: 'Administration',
    featureAdminText: 'Preserve admin surfaces while school roles are introduced.',
    howItWorksEyebrow: 'How it works',
    howItWorksHeading: 'Sign in first. Roles come next.',
    howItWorksIntro: 'The current shell authenticates users and leaves school-specific experiences empty until a school role is assigned.',
    step1Title: 'Sign in',
    step1Text: 'Users authenticate through the existing identity flow.',
    step2Title: 'Read identity',
    step2Text: 'The frontend reads /api/me to learn who is signed in.',
    step3Title: 'Wait for a role',
    step3Text: 'Role-specific tools stay hidden until the backend assigns school access.',
    signal1: 'Notices and updates will live here.',
    signal2: 'Families and school teams will use role-based access.',
    signal3: 'Private school communication remains the focus.',
    statusEyebrow: 'Current status',
    statusHeading: 'School shell in progress',
    statusText: 'Copy and feature details are TODO while the previous frontend surface is removed.'
  },
  admin: {
    title: 'Admin | Class Hero Hub',
    eyebrow: 'Admin',
    heading: 'Admin shell',
    intro: 'Admin tools are intentionally empty while school roles are introduced.'
  },
  platform: {
    title: 'Platform Admin | Class Hero Hub',
    eyebrow: 'Platform admin',
    heading: 'Schools',
    intro: 'Create schools, issue first admin invites, and manage school account status.',
    accessDeniedTitle: 'Platform access required',
    accessDenied: 'This account is not a platform administrator.',
    loadError: 'Failed to load platform admin data',
    createError: 'Failed to create school',
    inviteError: 'Failed to send invite',
    revokeError: 'Failed to revoke invite',
    actionError: 'Failed to update school status',
    createSchool: 'Create school',
    createHelp: 'This creates a pending school and sends the first school admin invite.',
    emptySchools: 'No schools have been created yet.',
    schoolName: 'School name',
    schoolNameAr: 'Arabic school name',
    timezone: 'Timezone',
    localeDefault: 'Default language',
    adminEmail: 'Admin email',
    status: 'Status',
    admins: 'Admins',
    students: 'Students',
    created: 'Created',
    open: 'Open',
    close: 'Close',
    cancel: 'Cancel',
    saving: 'Saving',
    backToSchools: 'Back to schools',
    schoolDetail: 'School detail',
    invites: 'Invites',
    sendInvite: 'Send invite',
    noInvites: 'No invites yet.',
    resend: 'Resend',
    revoke: 'Revoke',
    accountStatus: 'Account status',
    reason: 'Reason',
    suspend: 'Suspend school',
    reactivate: 'Reactivate school',
    statuses: {
      pending_setup: 'Pending setup',
      active: 'Active',
      suspended: 'Suspended'
    },
    inviteStatuses: {
      pending: 'Pending',
      accepted: 'Accepted',
      revoked: 'Revoked',
      expired: 'Expired'
    }
  },
  invite: {
    title: 'Accept invite | Class Hero Hub',
    accepting: 'Accepting invite',
    errorTitle: 'Invite unavailable',
    loadError: 'Failed to check your session',
    exchangeError: 'This invite is invalid, expired, revoked, or already used.'
  },
  school: {
    title: 'School | Class Hero Hub',
    eyebrow: 'School workspace',
    heading: 'School setup',
    intro: 'Configure the school structure used by branches, years, levels, sections, subjects, and optional teaching groups.',
    accessDeniedTitle: 'School admin access required',
    accessDenied: 'This account is not a school administrator.',
    loadError: 'Failed to load school setup',
    saveError: 'Failed to save school setup',
    setupComplete: 'Basic setup complete',
    setupInProgress: 'Basic setup in progress',
    records: 'records',
    optional: 'Optional',
    custom: 'Custom',
    save: 'Save',
    add: 'Add',
    edit: 'Edit',
    cancel: 'Cancel',
    archive: 'Archive',
    restored: 'This archived record was restored.',
    empty: 'No records yet.',
    code: 'Code',
    nameEn: 'English name',
    nameAr: 'Arabic name',
    sortOrder: 'Sort order',
    status: 'Status',
    active: 'Active',
    inactive: 'Inactive',
    archived: 'Archived',
    context: 'Context',
    select: 'Select',
    none: 'None',
    sectionLabel: 'Section label',
    quickLabels: 'Quick section labels',
    quickCreate: 'Quick create',
    tabs: {
      checklist: 'Checklist',
      settings: 'Settings',
      branches: 'Branches',
      stages: 'Stages',
      years: 'Academic years',
      levels: 'Levels',
      sections: 'Sections',
      subjects: 'Subjects',
      groups: 'Subject groups'
    },
    settings: {
      levelLabel: 'Level label',
      customLabel: 'Custom label'
    },
    branches: {
      title: 'Branches and campuses',
      single: 'Branch/campus'
    },
    stages: {
      title: 'Education stages',
      single: 'Education stage'
    },
    years: {
      title: 'Academic years',
      single: 'Academic year',
      current: 'Current',
      startDate: 'Start date',
      endDate: 'End date'
    },
    levels: {
      title: 'levels'
    },
    sections: {
      title: 'Class sections and homerooms',
      single: 'Class section'
    },
    subjects: {
      title: 'Subjects',
      single: 'Subject'
    },
    groups: {
      title: 'Subject groups'
    }
  },
  faq: {
    pageTitle: 'FAQ | Class Hero Hub',
    heading: 'FAQ',
    intro: 'TODO: Replace previous FAQ copy with school communication questions.',
    placeholderHeading: 'School FAQ copy TODO',
    placeholderText: 'This page is intentionally retained while the product copy is rewritten for Class Hero Hub.'
  },
  safetyPrivacy: {
    pageTitle: 'Safety & Privacy | Class Hero Hub',
    heading: 'Safety & Privacy',
    intro: 'TODO: Replace previous safety and privacy copy with school communication copy.',
    placeholderHeading: 'Safety copy TODO',
    placeholderText: 'This page is intentionally retained while the school-facing privacy copy is drafted.'
  },
  privacyPolicy: {
    pageTitle: 'Privacy Policy | Class Hero Hub',
    heading: 'Privacy Policy',
    intro: 'TODO: Replace previous privacy policy copy with school communication copy.',
    placeholderHeading: 'Privacy policy copy TODO',
    placeholderText: 'This page is intentionally retained as a placeholder for the Class Hero Hub policy rewrite.'
  },
  terms: {
    pageTitle: 'Terms of Service | Class Hero Hub',
    heading: 'Terms of Service',
    intro: 'TODO: Replace previous terms copy with school communication copy.',
    placeholderHeading: 'Terms copy TODO',
    placeholderText: 'This page is intentionally retained as a placeholder for updated Class Hero Hub terms.'
  },
  contact: {
    pageTitle: 'Contact Class Hero Hub',
    heading: 'Contact Class Hero Hub',
    intro: 'TODO: Replace previous contact copy with school communication support copy.',
    emailSupport: 'Email Support',
    emailAddress: 'support@familyherohub.com'
  },
  login: {
    title: 'Welcome to Class Hero Hub',
    intro: 'Sign in to access your school communication dashboard when a school role has been assigned.',
    continueGoogle: 'Continue with Google',
    emailLabel: 'Email address',
    emailPlaceholder: 'you@example.com',
    emailMagicLink: 'Email me a sign-in link',
    magicSent: 'Check your email for a one-time sign-in link.',
    magicError: 'Failed to send sign-in link',
    accountHelp: 'Use the Google account associated with your Class Hero Hub access.',
    sessionHelp: 'Sessions stay signed in for convenience. Always log out on shared devices.',
    accessHelp: 'Access is currently assigned by the school or administrator.'
  },
  parent: {
    title: 'Dashboard | Class Hero Hub',
    loginRequired: 'Sign-in required',
    goToLogin: 'Go to Login',
    failedLoad: 'Failed to load identity',
    eyebrow: 'Dashboard',
    noRoleHeading: 'No school role assigned yet',
    noRoleText: 'You are signed in, but this account does not have a school role yet.',
    signedInAs: 'Signed in as'
  }
};

export const ar = {
  app: {
    name: 'كلاس هيرو هب',
    classHero: 'كلاس هيرو',
    hub: 'هب'
  },
  language: {
    label: 'اللغة',
    english: 'English',
    arabic: 'العربية',
    help: 'تستخدم العربية تخطيطا من اليمين إلى اليسار. تبقى الأسماء والمحتوى المدرسي المدخل كما هو.'
  },
  nav: {
    home: 'الرئيسية',
    login: 'تسجيل الدخول',
    logout: 'تسجيل الخروج',
    dashboard: 'لوحة التحكم',
    admin: 'الإدارة',
    product: 'المنتج',
    support: 'الدعم',
    legal: 'قانوني',
    howItWorks: 'كيف يعمل',
    faq: 'الأسئلة الشائعة',
    contact: 'تواصل معنا',
    safetyPrivacy: 'السلامة والخصوصية',
    privacyPolicy: 'سياسة الخصوصية',
    terms: 'شروط الخدمة'
  },
  footer: {
    description: 'كلاس هيرو هب مركز تواصل مدرسي للإشعارات والتحديثات والوصول حسب الدور بين المدارس والعائلات.',
    tagline: 'مصمم للتواصل المدرسي. جاهز للوصول حسب الدور.'
  },
  common: {
    loading: 'جار التحميل',
    copyTodo: 'نسخة TODO'
  },
  home: {
    title: 'كلاس هيرو هب | مركز تواصل مدرسي',
    metaDescription: 'مركز تواصل مدرسي للإشعارات والتحديثات والوصول حسب الدور.',
    eyebrow: 'مركز تواصل مدرسي',
    heading: 'تحديثات مدرسية واضحة في مكان موثوق واحد.',
    intro: 'يساعد كلاس هيرو هب المدارس على مشاركة الإشعارات والتحديثات والمعلومات الأساسية مع الأشخاص المناسبين من خلال واجهة تواصل مركزة.',
    dashboardCta: 'اذهب إلى اللوحة',
    loginCta: 'تسجيل الدخول',
    howItWorksCta: 'شاهد كيف يعمل',
    strapline: 'إشعارات مدرسية · تواصل مع العائلات · وصول حسب الدور',
    schoolView: 'عرض المدرسة',
    schoolViewTitle: 'أرسل التحديث المناسب.',
    schoolViewText: 'واجهة مركزة للتواصل والإدارة بقيادة المدرسة.',
    familyView: 'عرض العائلة',
    familyViewTitle: 'اطلع على ما يهم.',
    familyViewText: 'يمكن للعائلات الوصول إلى تحديثات المدرسة عند تعيين الدور المناسب.',
    privateByDesign: 'وصول مضبوط',
    privateByDesignText: 'تتعامل الواجهة الخلفية مع الهوية وتعدد الجهات. تنتظر الواجهة الأمامية الآن أدوار المدرسة قبل عرض الأدوات الخاصة بالدور.',
    whatItDoesEyebrow: 'ما الذي يفعله',
    whatItDoesHeading: 'أساس أوضح للتواصل المدرسي',
    whatItDoesIntro: 'تتم إعادة بناء واجهة الواجهة الأمامية حول المدارس والعائلات والوصول حسب الدور.',
    featureCommunicationTitle: 'التواصل',
    featureCommunicationText: 'تحضير مكان مركزي لإشعارات المدرسة وتحديثاتها.',
    featureCalendarTitle: 'التنسيق',
    featureCalendarText: 'إبقاء ميزات التنسيق المدرسي المستقبلية داخل مركز واحد.',
    featureAdminTitle: 'الإدارة',
    featureAdminText: 'الحفاظ على صفحات الإدارة أثناء إدخال أدوار المدرسة.',
    howItWorksEyebrow: 'كيف يعمل',
    howItWorksHeading: 'سجل الدخول أولا. تأتي الأدوار لاحقا.',
    howItWorksIntro: 'تتحقق الواجهة الحالية من هوية المستخدم وتترك التجارب المدرسية فارغة حتى يتم تعيين دور مدرسي.',
    step1Title: 'سجل الدخول',
    step1Text: 'يسجل المستخدمون الدخول من خلال تدفق الهوية الحالي.',
    step2Title: 'قراءة الهوية',
    step2Text: 'تقرأ الواجهة الأمامية /api/me لمعرفة المستخدم المسجل.',
    step3Title: 'انتظار الدور',
    step3Text: 'تبقى الأدوات الخاصة بالدور مخفية حتى تمنح الواجهة الخلفية وصولا مدرسيا.',
    signal1: 'ستظهر الإشعارات والتحديثات هنا.',
    signal2: 'ستستخدم العائلات وفرق المدرسة وصولا حسب الدور.',
    signal3: 'يبقى التواصل المدرسي الخاص هو التركيز.',
    statusEyebrow: 'الحالة الحالية',
    statusHeading: 'واجهة المدرسة قيد العمل',
    statusText: 'تفاصيل النسخة والميزات TODO أثناء إزالة الواجهة السابقة.'
  },
  admin: {
    title: 'الإدارة | كلاس هيرو هب',
    eyebrow: 'الإدارة',
    heading: 'واجهة الإدارة',
    intro: 'أدوات الإدارة فارغة عمدا أثناء إدخال أدوار المدرسة.'
  },
  platform: {
    title: 'إدارة المنصة | كلاس هيرو هب',
    eyebrow: 'إدارة المنصة',
    heading: 'المدارس',
    intro: 'أنشئ المدارس وأرسل دعوات المسؤولين الأوائل وأدر حالة حساب المدرسة.',
    accessDeniedTitle: 'وصول المنصة مطلوب',
    accessDenied: 'هذا الحساب ليس مسؤول منصة.',
    loadError: 'تعذر تحميل بيانات إدارة المنصة',
    createError: 'تعذر إنشاء المدرسة',
    inviteError: 'تعذر إرسال الدعوة',
    revokeError: 'تعذر إلغاء الدعوة',
    actionError: 'تعذر تحديث حالة المدرسة',
    createSchool: 'إنشاء مدرسة',
    createHelp: 'ينشئ هذا مدرسة بانتظار الإعداد ويرسل دعوة مسؤول المدرسة الأولى.',
    emptySchools: 'لم يتم إنشاء أي مدارس بعد.',
    schoolName: 'اسم المدرسة',
    schoolNameAr: 'اسم المدرسة بالعربية',
    timezone: 'المنطقة الزمنية',
    localeDefault: 'اللغة الافتراضية',
    adminEmail: 'بريد المسؤول الإلكتروني',
    status: 'الحالة',
    admins: 'المسؤولون',
    students: 'الطلاب',
    created: 'تاريخ الإنشاء',
    open: 'فتح',
    close: 'إغلاق',
    cancel: 'إلغاء',
    saving: 'جار الحفظ',
    backToSchools: 'العودة إلى المدارس',
    schoolDetail: 'تفاصيل المدرسة',
    invites: 'الدعوات',
    sendInvite: 'إرسال دعوة',
    noInvites: 'لا توجد دعوات بعد.',
    resend: 'إعادة إرسال',
    revoke: 'إلغاء',
    accountStatus: 'حالة الحساب',
    reason: 'السبب',
    suspend: 'تعليق المدرسة',
    reactivate: 'إعادة تفعيل المدرسة',
    statuses: {
      pending_setup: 'بانتظار الإعداد',
      active: 'نشطة',
      suspended: 'معلقة'
    },
    inviteStatuses: {
      pending: 'قيد الانتظار',
      accepted: 'مقبولة',
      revoked: 'ملغاة',
      expired: 'منتهية'
    }
  },
  invite: {
    title: 'قبول الدعوة | كلاس هيرو هب',
    accepting: 'جار قبول الدعوة',
    errorTitle: 'الدعوة غير متاحة',
    loadError: 'تعذر التحقق من جلستك',
    exchangeError: 'هذه الدعوة غير صالحة أو منتهية أو ملغاة أو مستخدمة من قبل.'
  },
  school: {
    title: 'المدرسة | كلاس هيرو هب',
    eyebrow: 'مساحة المدرسة',
    heading: 'إعداد المدرسة',
    intro: 'اضبط هيكل المدرسة المستخدم للفروع والسنوات والمستويات والشعب والمواد ومجموعات التدريس الاختيارية.',
    accessDeniedTitle: 'وصول مسؤول المدرسة مطلوب',
    accessDenied: 'هذا الحساب ليس مسؤول مدرسة.',
    loadError: 'تعذر تحميل إعداد المدرسة',
    saveError: 'تعذر حفظ إعداد المدرسة',
    setupComplete: 'اكتمل الإعداد الأساسي',
    setupInProgress: 'الإعداد الأساسي قيد التنفيذ',
    records: 'سجلات',
    optional: 'اختياري',
    custom: 'مخصص',
    save: 'حفظ',
    add: 'إضافة',
    edit: 'تعديل',
    cancel: 'إلغاء',
    archive: 'أرشفة',
    restored: 'تمت استعادة هذا السجل المؤرشف.',
    empty: 'لا توجد سجلات بعد.',
    code: 'الرمز',
    nameEn: 'الاسم بالإنجليزية',
    nameAr: 'الاسم بالعربية',
    sortOrder: 'ترتيب العرض',
    status: 'الحالة',
    active: 'نشط',
    inactive: 'غير نشط',
    archived: 'مؤرشف',
    context: 'السياق',
    select: 'اختر',
    none: 'بدون',
    sectionLabel: 'تسمية الشعبة',
    quickLabels: 'تسميات الشعب السريعة',
    quickCreate: 'إنشاء سريع',
    tabs: {
      checklist: 'القائمة',
      settings: 'الإعدادات',
      branches: 'الفروع',
      stages: 'المراحل',
      years: 'السنوات الدراسية',
      levels: 'المستويات',
      sections: 'الشعب',
      subjects: 'المواد',
      groups: 'مجموعات المواد'
    },
    settings: {
      levelLabel: 'تسمية المستوى',
      customLabel: 'تسمية مخصصة'
    },
    branches: {
      title: 'الفروع والحرم المدرسي',
      single: 'الفرع أو الحرم'
    },
    stages: {
      title: 'المراحل التعليمية',
      single: 'المرحلة التعليمية'
    },
    years: {
      title: 'السنوات الدراسية',
      single: 'السنة الدراسية',
      current: 'الحالية',
      startDate: 'تاريخ البداية',
      endDate: 'تاريخ النهاية'
    },
    levels: {
      title: 'المستويات'
    },
    sections: {
      title: 'الشعب والصفوف الرئيسية',
      single: 'الشعبة'
    },
    subjects: {
      title: 'المواد',
      single: 'المادة'
    },
    groups: {
      title: 'مجموعات المواد'
    }
  },
  faq: {
    pageTitle: 'الأسئلة الشائعة | كلاس هيرو هب',
    heading: 'الأسئلة الشائعة',
    intro: 'TODO: استبدال أسئلة المنزل السابقة بأسئلة تواصل مدرسي.',
    placeholderHeading: 'نسخة الأسئلة المدرسية TODO',
    placeholderText: 'تم الاحتفاظ بهذه الصفحة أثناء إعادة كتابة نسخة المنتج لكلاس هيرو هب.'
  },
  safetyPrivacy: {
    pageTitle: 'السلامة والخصوصية | كلاس هيرو هب',
    heading: 'السلامة والخصوصية',
    intro: 'TODO: استبدال نسخة السلامة والخصوصية المنزلية بنسخة تواصل مدرسي.',
    placeholderHeading: 'نسخة السلامة TODO',
    placeholderText: 'تم الاحتفاظ بهذه الصفحة أثناء إعداد نسخة الخصوصية الموجهة للمدرسة.'
  },
  privacyPolicy: {
    pageTitle: 'سياسة الخصوصية | كلاس هيرو هب',
    heading: 'سياسة الخصوصية',
    intro: 'TODO: استبدال سياسة الخصوصية المنزلية بنسخة تواصل مدرسي.',
    placeholderHeading: 'نسخة سياسة الخصوصية TODO',
    placeholderText: 'تم الاحتفاظ بهذه الصفحة كعنصر نائب لإعادة كتابة سياسة كلاس هيرو هب.'
  },
  terms: {
    pageTitle: 'شروط الخدمة | كلاس هيرو هب',
    heading: 'شروط الخدمة',
    intro: 'TODO: استبدال شروط المنزل السابقة بنسخة تواصل مدرسي.',
    placeholderHeading: 'نسخة الشروط TODO',
    placeholderText: 'تم الاحتفاظ بهذه الصفحة كعنصر نائب لشروط كلاس هيرو هب المحدثة.'
  },
  contact: {
    pageTitle: 'تواصل مع كلاس هيرو هب',
    heading: 'تواصل مع كلاس هيرو هب',
    intro: 'TODO: استبدال نسخة التواصل المنزلية بنسخة دعم للتواصل المدرسي.',
    emailSupport: 'الدعم عبر البريد الإلكتروني',
    emailAddress: 'support@familyherohub.com'
  },
  login: {
    title: 'مرحبا بك في كلاس هيرو هب',
    intro: 'سجل الدخول للوصول إلى لوحة التواصل المدرسي عندما يتم تعيين دور مدرسي لك.',
    continueGoogle: 'المتابعة باستخدام Google',
    emailLabel: 'عنوان البريد الإلكتروني',
    emailPlaceholder: 'you@example.com',
    emailMagicLink: 'أرسل لي رابط تسجيل الدخول',
    magicSent: 'تحقق من بريدك الإلكتروني للحصول على رابط تسجيل دخول لمرة واحدة.',
    magicError: 'تعذر إرسال رابط تسجيل الدخول',
    accountHelp: 'استخدم حساب Google المرتبط بوصولك إلى كلاس هيرو هب.',
    sessionHelp: 'تبقى الجلسات مسجلة الدخول للراحة. سجّل الخروج دائما على الأجهزة المشتركة.',
    accessHelp: 'يتم تعيين الوصول حاليا من المدرسة أو المسؤول.'
  },
  parent: {
    title: 'لوحة التحكم | كلاس هيرو هب',
    loginRequired: 'تسجيل الدخول مطلوب',
    goToLogin: 'الذهاب إلى تسجيل الدخول',
    failedLoad: 'تعذر تحميل الهوية',
    eyebrow: 'لوحة التحكم',
    noRoleHeading: 'لم يتم تعيين دور مدرسي بعد',
    noRoleText: 'أنت مسجل الدخول، لكن هذا الحساب لا يملك دورا مدرسيا بعد.',
    signedInAs: 'مسجل الدخول باسم'
  }
};
