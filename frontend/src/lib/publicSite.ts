import type { SupportedLocale } from "$lib/i18n";

export type PublicSection = {
  title: string;
  text: string;
  bullets?: string[];
};

export type PublicPageCopy = {
  pageTitle: string;
  metaDescription: string;
  eyebrow: string;
  heading: string;
  intro: string;
  highlights?: string[];
  sections: PublicSection[];
  notice?: {
    title: string;
    text: string;
  };
  cta: {
    heading: string;
    text: string;
    label: string;
    href: string;
    secondaryLabel?: string;
    secondaryHref?: string;
  };
};

export type FaqItem = {
  question: string;
  answer: string;
};

type PublicSiteCopy = {
  nav: {
    product: string;
    howItWorks: string;
    schools: string;
    familyConnection: string;
    requestPilot: string;
    staffLogin: string;
    dashboard: string;
    menu: string;
    openMenu: string;
    closeMenu: string;
  };
  footer: {
    description: string;
    tagline: string;
    product: string;
    support: string;
    legal: string;
    home: string;
    features: string;
    howItWorks: string;
    schools: string;
    familyConnection: string;
    faq: string;
    requestPilot: string;
    contact: string;
    administratorGuide: string;
    teacherGuide: string;
    familyGuide: string;
    safetyPrivacy: string;
    privacy: string;
    terms: string;
    dataRequests: string;
    emailLabel: string;
  };
  home: {
    pageTitle: string;
    metaDescription: string;
    eyebrow: string;
    heading: string;
    intro: string;
    primaryCta: string;
    secondaryCta: string;
    strapline: string;
    schoolWorkspaceLabel: string;
    schoolWorkspaceTitle: string;
    schoolWorkspaceText: string;
    familyDeliveryLabel: string;
    familyDeliveryTitle: string;
    familyDeliveryText: string;
    boundaryLabel: string;
    boundaryText: string;
    benefitsEyebrow: string;
    benefitsHeading: string;
    benefitsIntro: string;
    benefits: Array<{ title: string; text: string }>;
    workflowEyebrow: string;
    workflowHeading: string;
    workflowIntro: string;
    workflow: Array<{ title: string; text: string }>;
    featureEyebrow: string;
    featureHeading: string;
    featureIntro: string;
    featureGroups: Array<{ title: string; text: string; items: string[] }>;
    familyEyebrow: string;
    familyHeading: string;
    familyIntro: string;
    schoolSideTitle: string;
    schoolSideText: string;
    connectionTitle: string;
    connectionText: string;
    familySideTitle: string;
    familySideText: string;
    familyBoundary: string;
    familyCta: string;
    trustEyebrow: string;
    trustHeading: string;
    trustIntro: string;
    trustItems: Array<{ title: string; text: string }>;
    bilingualEyebrow: string;
    bilingualHeading: string;
    bilingualText: string;
    bilingualPoint1: string;
    bilingualPoint2: string;
    faqEyebrow: string;
    faqHeading: string;
    faqIntro: string;
    faqCta: string;
    finalHeading: string;
    finalText: string;
    finalPrimary: string;
    finalSecondary: string;
  };
  faq: {
    pageTitle: string;
    metaDescription: string;
    eyebrow: string;
    heading: string;
    intro: string;
    items: FaqItem[];
    ctaHeading: string;
    ctaText: string;
    ctaLabel: string;
  };
  pages: {
    howItWorks: PublicPageCopy;
    features: PublicPageCopy;
    schools: PublicPageCopy;
    familyConnection: PublicPageCopy;
    pilot: PublicPageCopy;
    contact: PublicPageCopy;
    administratorGuide: PublicPageCopy;
    teacherGuide: PublicPageCopy;
    familyGuide: PublicPageCopy;
    safetyPrivacy: PublicPageCopy;
    privacy: PublicPageCopy;
    terms: PublicPageCopy;
    dataRequests: PublicPageCopy;
  };
};

const supportEmailHref = "mailto:support@classherohub.com";
const pilotEmailHref =
  "mailto:support@classherohub.com?subject=Class%20Hero%20Hub%20pilot%20enquiry";

const englishFaq: FaqItem[] = [
  {
    question: "What is Class Hero Hub?",
    answer:
      "Class Hero Hub is a school-facing workspace for authorised staff. It brings school setup, rosters, behaviour, learning updates, communication, family engagement, reporting and safeguarding workflows into one connected product.",
  },
  {
    question: "Who uses Class Hero Hub?",
    answer:
      "School leaders, administrators, teachers and other authorised school roles use CHH according to their permissions. Students are school records, not independent CHH account holders.",
  },
  {
    question: "Do parents log in to Class Hero Hub?",
    answer:
      "No. Parents and guardians view their child’s linked school information through Family Hero Hub. They do not sign in to CHH and there is no Class Hero Hub parent app.",
  },
  {
    question: "What if a teacher is also a parent?",
    answer:
      "They use CHH for their staff role and Family Hero Hub for their parent or family role. The two roles and their data access stay separate.",
  },
  {
    question: "What can families see in Family Hero Hub?",
    answer:
      "Depending on the school’s enabled features and the child’s active link, families may see homework, notices, updates, protected photos, school points, calendar items, surveys and School Chats.",
  },
  {
    question: "Does CHH support behaviour points?",
    answer:
      "Yes. Schools can use positive and needs-work categories. Negative behaviour remains private, and CHH does not create public rankings or shaming features. Positive recognition can be supported by recorded evidence and staff review.",
  },
  {
    question: "How is safeguarding review handled?",
    answer:
      "Safeguarding review is kept separate from ordinary participation, receipts and notifications. Access is explicitly authorised, reason-gated and audited, with protected evidence handled in dedicated workflows.",
  },
  {
    question: "Does CHH support English and Arabic?",
    answer:
      "Yes. The product supports English and Arabic, including right-to-left presentation. School-entered names and content remain exactly as supplied unless the school provides both language versions.",
  },
  {
    question: "Can a school import existing records?",
    answer:
      "CHH supports staged CSV imports from existing MIS or SMS exports, with preview, validation and commit steps. Annual updates, history and authorised exports help schools keep records usable over time.",
  },
  {
    question: "Can schools export their data?",
    answer:
      "Authorised roles can use available exports for supported records and reports. Schools can contact support for questions about portability or an account and data request.",
  },
  {
    question: "What does Class Hero Hub cost?",
    answer:
      "A public commercial price has not been set. Schools can request a demonstration or discuss pilot access while the commercial model is being defined.",
  },
  {
    question: "Is CHH available for general production use?",
    answer:
      "CHH is currently presented for demonstrations and carefully scoped pilot access. Availability and enabled features are agreed with each participating school.",
  },
];

const arabicFaq: FaqItem[] = [
  {
    question: "ما منصة كلاس هيرو هب؟",
    answer:
      "كلاس هيرو هب مساحة عمل مدرسية للموظفين المصرح لهم. تجمع إعداد المدرسة والقوائم والسلوك وتحديثات التعلم والتواصل ومشاركة الأسرة والتقارير وإجراءات الحماية في منتج مترابط واحد.",
  },
  {
    question: "من يستخدم كلاس هيرو هب؟",
    answer:
      "يستخدمها قادة المدارس والمسؤولون والمعلمون والأدوار المدرسية المصرح لها وفق صلاحياتها. يُسجل الطلاب كسجلات مدرسية، وليس كأصحاب حسابات مستقلة في كلاس هيرو هب.",
  },
  {
    question: "هل يسجل أولياء الأمور الدخول إلى كلاس هيرو هب؟",
    answer:
      "لا. يعرض أولياء الأمور والأوصياء معلومات المدرسة المرتبطة بأبنائهم من خلال Family Hero Hub. ولا يسجلون الدخول إلى كلاس هيرو هب، ولا يوجد تطبيق مستقل لأولياء الأمور باسم كلاس هيرو هب.",
  },
  {
    question: "ماذا لو كان المعلم ولي أمر أيضا؟",
    answer:
      "يستخدم كلاس هيرو هب في دوره الوظيفي، ويستخدم Family Hero Hub في دوره الأسري. وتبقى صلاحيات الدورين وبياناتهما منفصلة.",
  },
  {
    question: "ما الذي يمكن للأسرة رؤيته في Family Hero Hub؟",
    answer:
      "بحسب الميزات التي تفعلها المدرسة والرابط النشط للطفل، قد ترى الأسرة الواجبات والتنبيهات والتحديثات والصور المحمية ونقاط المدرسة وعناصر التقويم والاستبيانات ومحادثات المدرسة.",
  },
  {
    question: "هل تدعم المنصة نقاط السلوك؟",
    answer:
      "نعم. يمكن للمدرسة استخدام فئات إيجابية وفئات تحتاج إلى تحسين. يبقى السلوك السلبي خاصا، ولا تنشئ المنصة تصنيفات علنية أو أدوات للتشهير. ويمكن أن يستند التقدير الإيجابي إلى أدلة مسجلة ومراجعة الموظفين.",
  },
  {
    question: "كيف تتم مراجعة مسائل الحماية؟",
    answer:
      "تبقى مراجعة الحماية منفصلة عن المشاركة العادية وإيصالات التسليم والقراءة والإشعارات. ويتطلب الوصول تفويضا صريحا وسببا مسجلا، مع تدقيق الإجراءات ومعالجة الأدلة المحمية في مسارات مخصصة.",
  },
  {
    question: "هل تدعم كلاس هيرو هب الإنجليزية والعربية؟",
    answer:
      "نعم. تدعم المنصة الإنجليزية والعربية، بما في ذلك العرض من اليمين إلى اليسار. وتبقى الأسماء والمحتويات التي تدخلها المدرسة كما هي ما لم توفر المدرسة نسختين لغويتين.",
  },
  {
    question: "هل يمكن للمدرسة استيراد سجلاتها الحالية؟",
    answer:
      "تدعم المنصة استيراد ملفات CSV المرحلي من صادرات أنظمة معلومات أو إدارة المدارس، مع المعاينة والتحقق والاعتماد. كما تساعد التحديثات السنوية والسجل والصادرات المصرح بها على إبقاء البيانات قابلة للاستخدام بمرور الوقت.",
  },
  {
    question: "هل يمكن للمدرسة تصدير بياناتها؟",
    answer:
      "يمكن للأدوار المصرح لها استخدام الصادرات المتاحة للسجلات والتقارير المدعومة. ويمكن للمدرسة التواصل مع الدعم بشأن قابلية نقل البيانات أو طلبات الحساب والبيانات.",
  },
  {
    question: "ما تكلفة كلاس هيرو هب؟",
    answer:
      "لم يُحدد سعر تجاري معلن بعد. يمكن للمدارس طلب عرض توضيحي أو مناقشة الوصول التجريبي ريثما يكتمل تحديد النموذج التجاري.",
  },
  {
    question: "هل المنصة متاحة للاستخدام العام؟",
    answer:
      "تُقدم كلاس هيرو هب حاليا للعروض التوضيحية وبرامج تجريبية محددة النطاق بعناية. ويُتفق مع كل مدرسة مشاركة على التوفر والميزات المفعلة.",
  },
];

const en: PublicSiteCopy = {
  nav: {
    product: "Product",
    howItWorks: "How it works",
    schools: "For schools",
    familyConnection: "Family connection",
    requestPilot: "Request a pilot",
    staffLogin: "Staff login",
    dashboard: "Dashboard",
    menu: "Explore Class Hero Hub",
    openMenu: "Open public website menu",
    closeMenu: "Close public website menu",
  },
  footer: {
    description:
      "Class Hero Hub is the school-facing workspace for communication, learning updates, behaviour, family engagement and school operations.",
    tagline: "School life, clearly connected.",
    product: "Product",
    support: "Support",
    legal: "Legal",
    home: "Home",
    features: "Product overview",
    howItWorks: "How it works",
    schools: "For schools",
    familyConnection: "Family Hero Hub connection",
    faq: "FAQ",
    requestPilot: "Request a pilot",
    contact: "Contact",
    administratorGuide: "School administrator guide",
    teacherGuide: "Teacher guide",
    familyGuide: "Parent / FHH guide",
    safetyPrivacy: "Safety, privacy & support",
    privacy: "Privacy Policy",
    terms: "Terms of Service",
    dataRequests: "Data & account requests",
    emailLabel: "Support and pilot enquiries",
  },
  home: {
    pageTitle: "Class Hero Hub | School life, clearly connected",
    metaDescription:
      "A connected school workspace for communication, behaviour, learning updates, reporting and protected family engagement through Family Hero Hub.",
    eyebrow: "School life, clearly connected",
    heading: "One clear place for the work that keeps a school moving.",
    intro:
      "Class Hero Hub brings school operations, teaching workflows, communication and family engagement together — without making staff fight a traditional school-management maze.",
    primaryCta: "Request a pilot",
    secondaryCta: "Explore the product",
    strapline:
      "For authorised school staff · Parents use Family Hero Hub · English and Arabic",
    schoolWorkspaceLabel: "School workspace",
    schoolWorkspaceTitle: "Set up once. Work clearly every day.",
    schoolWorkspaceText:
      "Organise years, classes, rosters and staff, then manage teaching, communication, reporting and review from the same school-scoped workspace.",
    familyDeliveryLabel: "Family delivery",
    familyDeliveryTitle: "The right information reaches home.",
    familyDeliveryText:
      "Linked parents see enabled school information in Family Hero Hub — never by signing in to the staff system.",
    boundaryLabel: "Clear role boundary",
    boundaryText:
      "CHH is for school staff and authorised school roles. Family Hero Hub is for parents, guardians and family identity.",
    benefitsEyebrow: "Built around the school day",
    benefitsHeading:
      "Less switching. Better visibility. Clearer responsibility.",
    benefitsIntro:
      "CHH organises the work schools already do, while keeping access, evidence and family delivery tied to the right school and role.",
    benefits: [
      {
        title: "Organise the foundations",
        text: "Keep branches, academic years, grades, classes, subjects, rosters and records structured and ready for the year.",
      },
      {
        title: "Support everyday teaching",
        text: "Record behaviour, recognise positive effort, set homework and share timely class information without leaving the teacher workflow.",
      },
      {
        title: "Keep families informed",
        text: "Deliver enabled homework, notices, updates, points, calendar items, surveys and School Chats through Family Hero Hub.",
      },
      {
        title: "Lead with evidence",
        text: "Use reports, trends, receipts, audit trails and dedicated safeguarding review to understand what happened and what needs attention.",
      },
    ],
    workflowEyebrow: "How it works",
    workflowHeading: "From school setup to a better-informed family.",
    workflowIntro:
      "Each step stays within the correct role and data boundary, from the school record to the family-facing view.",
    workflow: [
      {
        title: "Build the school structure",
        text: "School administrators configure the school, current academic year, classes, subjects, staff and rosters, manually or through staged CSV imports.",
      },
      {
        title: "Staff work in context",
        text: "Authorised staff see the classes, students and workflows their role permits — from homework and recognition to notices, messages and reports.",
      },
      {
        title: "CHH protects and delivers",
        text: "School data remains scoped to the school. Enabled family information passes through the protected server-side integration boundary.",
      },
      {
        title: "Parents use Family Hero Hub",
        text: "Parents and guardians see their linked child’s school information in FHH alongside their family tools. They never use CHH directly.",
      },
    ],
    featureEyebrow: "Connected capability",
    featureHeading:
      "A complete view of the product — organised by the work it supports.",
    featureIntro:
      "Start with the essentials a school needs now. Enable additional communication, engagement and governance workflows when the school is ready.",
    featureGroups: [
      {
        title: "School foundations",
        text: "Create a dependable structure for every authorised workflow.",
        items: [
          "Schools, branches and academic years",
          "Grades, classes, subjects and staff assignments",
          "Student and guardian records",
          "MIS / SMS CSV imports, annual updates, history and exports",
        ],
      },
      {
        title: "Teaching and learning",
        text: "Keep everyday classroom actions quick, visible and connected.",
        items: [
          "Positive and needs-work behaviour points",
          "Evidence-based positive recognition and certificates",
          "Homework, diary and required items",
          "Notices, calendar events, school updates and protected photos",
        ],
      },
      {
        title: "Communication and engagement",
        text: "Give the right people a clear channel without opening unnecessary access.",
        items: [
          "Text, protected photo and voice messaging",
          "Delivery and read receipts",
          "School contact-hour controls",
          "Surveys, polls and Family Hero Hub delivery",
        ],
      },
      {
        title: "Insight and governance",
        text: "Support school decisions and protected review with traceable records.",
        items: [
          "Reports and behaviour trends",
          "Dedicated safeguarding review and evidence handling",
          "Operational health and audit records",
          "English / Arabic presentation and data portability tools",
        ],
      },
    ],
    familyEyebrow: "CHH + Family Hero Hub",
    familyHeading: "The school stays in control. Families see what matters.",
    familyIntro:
      "The two products have distinct responsibilities and a protected connection between them.",
    schoolSideTitle: "1 · School staff use CHH",
    schoolSideText:
      "Authorised staff create and manage school records, teaching information, communications and enabled family-facing content.",
    connectionTitle: "2 · A protected server connection",
    connectionText:
      "FHH requests linked school information through its server-side CHH proxy using opaque, scoped identifiers. Family devices never call CHH directly.",
    familySideTitle: "3 · Parents use FHH",
    familySideText:
      "Parents and guardians view the enabled information for their linked child in Family Hero Hub. FHH keeps family, household and device identity on the family side.",
    familyBoundary:
      "A teacher who is also a parent uses CHH in their staff role and FHH in their family role. The roles are not merged.",
    familyCta: "See the family connection",
    trustEyebrow: "Privacy and safeguarding",
    trustHeading: "Designed for school trust, without oversized promises.",
    trustIntro:
      "CHH uses clear access boundaries and dedicated protected workflows. No online service can promise perfect security; the product is designed to reduce unnecessary exposure and keep authority explicit.",
    trustItems: [
      {
        title: "School and role scope",
        text: "Authorised users see only the schools, classes, students and tools allowed by their active roles and assignments.",
      },
      {
        title: "Private behaviour records",
        text: "Needs-work behaviour is not turned into public rankings or shaming. Positive recognition remains evidence-led and staff-reviewed.",
      },
      {
        title: "Separate safeguarding review",
        text: "Protected review does not make a reviewer a conversation participant or change receipts, unread counts or notifications.",
      },
      {
        title: "Traceable operations",
        text: "Audit records, operational health checks, authorised exports and controlled evidence workflows support accountable administration.",
      },
    ],
    bilingualEyebrow: "English + العربية",
    bilingualHeading: "One product, ready for bilingual school communities.",
    bilingualText:
      "CHH supports English and professional Arabic throughout the public website and product interface, including right-to-left layouts.",
    bilingualPoint1:
      "Interface language can change without altering school-entered names or content.",
    bilingualPoint2:
      "Responsive layouts are designed for staff working across phones, tablets and desktops.",
    faqEyebrow: "FAQ",
    faqHeading: "The questions schools and families ask first.",
    faqIntro:
      "Clear answers about roles, family access, product scope, safety and pilot availability.",
    faqCta: "Read all questions",
    finalHeading: "Ready to see how CHH fits your school?",
    finalText:
      "Tell us about your school, current systems and the workflows you want to improve. We will respond with the most relevant next step for a demonstration or pilot discussion.",
    finalPrimary: "Request a pilot",
    finalSecondary: "Contact the team",
  },
  faq: {
    pageTitle: "Frequently asked questions | Class Hero Hub",
    metaDescription:
      "Answers about Class Hero Hub, school staff access, Family Hero Hub parent delivery, privacy, safeguarding, imports, exports and pilot access.",
    eyebrow: "Straight answers",
    heading: "Frequently asked questions",
    intro:
      "CHH has a deliberately clear school-and-family boundary. These answers explain who uses each product and how the main workflows fit together.",
    items: englishFaq,
    ctaHeading: "Have a question that is specific to your school?",
    ctaText:
      "Send a short enquiry without including sensitive student or safeguarding information.",
    ctaLabel: "Contact Class Hero Hub",
  },
  pages: {
    howItWorks: {
      pageTitle: "How Class Hero Hub works",
      metaDescription:
        "See how schools configure CHH, how staff use role-scoped workflows and how linked parents receive enabled school information through Family Hero Hub.",
      eyebrow: "How it works",
      heading: "A clear path from school setup to family understanding.",
      intro:
        "CHH connects the work of school administrators and teachers without blurring who owns school data, family identity or protected review.",
      highlights: [
        "School-scoped",
        "Role-aware",
        "Family delivery through FHH",
      ],
      sections: [
        {
          title: "1. Configure the school",
          text: "School administrators create the operational structure that every later workflow relies on.",
          bullets: [
            "School and branch details",
            "Academic years, grades, classes and subjects",
            "Staff roles and assignments",
            "Behaviour categories and enabled features",
          ],
        },
        {
          title: "2. Bring records across carefully",
          text: "Existing student, guardian and roster data can be prepared through staged CSV import rather than an uncontrolled one-step upload.",
          bullets: [
            "Preview and validation before commit",
            "External MIS / SMS references where available",
            "Historical enrolment and annual-update support",
            "Authorised exports for portability",
          ],
        },
        {
          title: "3. Give staff the right workspace",
          text: "Teachers and school leaders sign in to CHH and see workflows appropriate to their current school roles, classes and assignments.",
          bullets: [
            "Class and student context",
            "Homework, diary and calendar",
            "Behaviour and positive recognition",
            "Notices, updates, messaging, surveys and reports",
          ],
        },
        {
          title: "4. Keep communication accountable",
          text: "School communications stay attached to the correct audience and school context, with delivery state and policy controls where supported.",
          bullets: [
            "Text, protected photo and voice messages",
            "Delivery and read receipts",
            "Contact-hour controls",
            "Protected updates and school calendar items",
          ],
        },
        {
          title: "5. Deliver to families through FHH",
          text: "Parents do not enter the staff system. Family Hero Hub displays enabled school information only for a child with an active, verified school link.",
        },
        {
          title: "6. Review, report and improve",
          text: "Authorised leaders can use reports, trends, audits and exports. Safeguarding review stays a separate, reason-gated and audited workflow.",
        },
      ],
      notice: {
        title: "The boundary matters",
        text: "CHH owns school data and school-side access. FHH owns family, parent, child, household and device identity. Family clients never call CHH directly.",
      },
      cta: {
        heading:
          "Walk through the workflow with your own school structure in mind.",
        text: "Request a demonstration or pilot conversation with the Class Hero Hub team.",
        label: "Request a pilot",
        href: "/pilot",
        secondaryLabel: "Explore all features",
        secondaryHref: "/features",
      },
    },
    features: {
      pageTitle: "Class Hero Hub product overview and features",
      metaDescription:
        "Explore CHH school setup, rosters, behaviour, learning updates, messaging, surveys, reporting, safeguarding, bilingual support and Family Hero Hub integration.",
      eyebrow: "Product overview",
      heading: "The connected school workflows that matter now.",
      intro:
        "CHH is organised around how schools actually work: set up the structure, support staff, communicate clearly, include families and keep protected work governed.",
      highlights: [
        "School operations",
        "Teaching workflows",
        "Family engagement",
        "Governance",
      ],
      sections: [
        {
          title: "School structure and administration",
          text: "Set up schools, branches, academic years, grade levels, classes, subjects, assignments and rosters. Manage student and guardian records with school-scoped history.",
          bullets: [
            "Manual setup and guided school onboarding",
            "MIS / SMS CSV imports with staged review",
            "Annual updates, history and supported exports",
            "Role and membership administration",
          ],
        },
        {
          title: "Behaviour and positive recognition",
          text: "Record school-defined positive and needs-work events in context. Use positive evidence to support staff-reviewed recognition and printable certificates.",
          bullets: [
            "Quick classroom award flows",
            "Corrections without silently rewriting history",
            "Private needs-work information",
            "No public rankings or shaming",
          ],
        },
        {
          title: "Homework, diary and calendar",
          text: "Keep due work, tests, reminders, required items and calendar events connected to the right school, class, group or student audience.",
        },
        {
          title: "Notices, updates and protected media",
          text: "Publish school or class information with appropriate audiences, including protected school update photos where enabled.",
        },
        {
          title: "School messaging",
          text: "Support text, protected photo and voice communication with delivery and read receipts, contact-hour controls and school-defined availability.",
          bullets: [
            "School-to-family and staff contexts",
            "Protected media access",
            "Voice notes",
            "Separate safeguarding review",
          ],
        },
        {
          title: "Surveys and polls",
          text: "Create targeted parent surveys, manage availability and reminders, and review response progress and results according to school permissions.",
        },
        {
          title: "Reports, trends and operations",
          text: "Give authorised leaders behaviour reports and trends, supported exports, audit information and operational health visibility without exposing protected content to unrelated roles.",
        },
        {
          title: "Bilingual and family-connected",
          text: "Use CHH in English or Arabic, with responsive RTL layouts, while linked parents receive enabled school information in Family Hero Hub.",
        },
      ],
      cta: {
        heading: "Choose the workflows your pilot needs.",
        text: "We can focus a demonstration on school setup, teaching, family communication, reporting or protected review.",
        label: "Discuss a pilot",
        href: "/pilot",
        secondaryLabel: "See how it works",
        secondaryHref: "/how-it-works",
      },
    },
    schools: {
      pageTitle: "Class Hero Hub for school leaders and staff",
      metaDescription:
        "See how Class Hero Hub supports school leaders, administrators and teachers with connected, role-scoped school workflows.",
      eyebrow: "For schools",
      heading:
        "A school platform people can understand before they have to master it.",
      intro:
        "CHH gives each authorised role a clearer starting point, while keeping the underlying school structure, evidence and permissions consistent.",
      highlights: ["For leaders", "For administrators", "For teachers"],
      sections: [
        {
          title: "For school leaders",
          text: "See patterns, delivery state and operational context without turning every leadership question into a spreadsheet request.",
          bullets: [
            "Reports and trends",
            "Family-engagement visibility",
            "Operational health and audit context",
            "Clear governance boundaries",
          ],
        },
        {
          title: "For school administrators",
          text: "Manage the school structure and year-to-year records that make every staff workflow reliable.",
          bullets: [
            "Academic years, grades, classes and subjects",
            "Staff, student and guardian records",
            "CSV imports, annual updates and exports",
            "Feature, messaging and contact-hour controls",
          ],
        },
        {
          title: "For teachers",
          text: "Move from class context to the next useful action quickly: recognise effort, record behaviour, set homework, publish an update or communicate with a family.",
        },
        {
          title: "For bilingual communities",
          text: "Staff can use English or Arabic with right-to-left layouts. School-entered names and content remain under school control.",
        },
        {
          title: "For a controlled rollout",
          text: "Start with a defined school, branch or workflow, agree enabled features and roles, then widen the pilot only when the operational foundation is ready.",
        },
        {
          title: "For schools with existing systems",
          text: "CHH can use staged CSV imports from existing MIS or SMS exports. It does not require schools to trust an opaque, all-or-nothing data migration.",
        },
      ],
      cta: {
        heading: "Show us where school work is currently fragmented.",
        text: "We will focus the conversation on the workflows that matter to your staff and families.",
        label: "Request a school conversation",
        href: "/pilot",
        secondaryLabel: "Read the administrator guide",
        secondaryHref: "/guides/administrator",
      },
    },
    familyConnection: {
      pageTitle: "Class Hero Hub and Family Hero Hub parent connection",
      metaDescription:
        "Understand how CHH school data reaches linked parents through Family Hero Hub while staff, family identity and device data stay on the correct side.",
      eyebrow: "Family connection",
      heading:
        "School information reaches parents without giving parents staff-system access.",
      intro:
        "CHH and FHH are related products with separate responsibilities. The boundary is intentional, visible and part of how access stays understandable.",
      highlights: [
        "Staff use CHH",
        "Parents use FHH",
        "Server-side connection",
      ],
      sections: [
        {
          title: "CHH is the school authority",
          text: "Schools and authorised staff manage school structures, student records, learning information, behaviour, communications, surveys, reports and safeguarding workflows in CHH.",
        },
        {
          title: "FHH is the family authority",
          text: "Family Hero Hub manages parent, child, household and device identity. It presents school information alongside family tools without moving family device identity into CHH.",
        },
        {
          title: "Parents never call CHH directly",
          text: "FHH requests protected school data through its server-side CHH proxy. The connection uses opaque, scoped identifiers and an active child-school link.",
        },
        {
          title: "What a linked family may see",
          text: "Depending on the school’s enabled features, a parent may see homework, notices, school updates, protected photos, school points, calendar items, surveys and School Chats.",
        },
        {
          title: "Home and school stay separate",
          text: "Family points, rewards, household routines and family-device information remain in FHH. They are not sent to CHH merely because a school link exists.",
        },
        {
          title: "One person can hold two distinct roles",
          text: "A teacher who is also a parent uses CHH for authorised staff work and FHH for their own family. Staff permissions never become parent access, and parent access never becomes staff access.",
        },
      ],
      notice: {
        title: "There is no CHH parent app",
        text: "Parents and guardians should use Family Hero Hub. Any school information they can see depends on the school’s enabled features and their child’s active link.",
      },
      cta: {
        heading: "Need to explain the connection to your school community?",
        text: "Use the parent / FHH guide for a concise, role-accurate explanation.",
        label: "Read the parent / FHH guide",
        href: "/guides/families",
        secondaryLabel: "Visit Family Hero Hub",
        secondaryHref: "https://familyherohub.com",
      },
    },
    pilot: {
      pageTitle: "Request a Class Hero Hub pilot or demonstration",
      metaDescription:
        "Contact Class Hero Hub to discuss a school demonstration, a carefully scoped pilot or product information.",
      eyebrow: "Pilot and demonstrations",
      heading: "Start with the school problem you want to solve.",
      intro:
        "There is no invented package or price list here. Tell us what your school is trying to improve, and we will decide together whether a demonstration or scoped pilot is the right next step.",
      highlights: [
        "No published pricing yet",
        "Scoped pilots",
        "School-led rollout",
      ],
      sections: [
        {
          title: "Tell us about the school",
          text: "A useful enquiry includes the school or group name, country or timezone, approximate scale, languages and the staff role of the person contacting us.",
        },
        {
          title: "Name the workflow",
          text: "Explain whether the priority is school setup, imports, behaviour and recognition, homework, notices and updates, messaging, surveys, reporting, safeguarding, or the FHH family connection.",
        },
        {
          title: "Define a safe scope",
          text: "A pilot may start with one school, branch, year group or operational workflow. Enabled features, roles and review responsibilities should be agreed before real school data is introduced.",
        },
        {
          title: "Prepare the right people",
          text: "Include a school leader or sponsor, an operational administrator and representative teachers. Add safeguarding or data leads when those workflows are in scope.",
        },
        {
          title: "Keep sensitive data out of the first email",
          text: "Do not send student records, private messages, survey answers, safeguarding evidence, credentials or tokens in an enquiry. We will agree an appropriate next step if data review becomes necessary.",
        },
        {
          title: "Commercial terms come later",
          text: "A public pricing model has not been defined. Any pilot scope, support expectations and future commercial terms must be agreed explicitly.",
        },
      ],
      cta: {
        heading: "Request a pilot conversation",
        text: "Email the team with a short, non-sensitive description of your school and priority workflow.",
        label: "Email a pilot enquiry",
        href: pilotEmailHref,
        secondaryLabel: "View product features",
        secondaryHref: "/features",
      },
    },
    contact: {
      pageTitle: "Contact Class Hero Hub",
      metaDescription:
        "Contact Class Hero Hub for school product information, pilot enquiries, support, privacy questions or account and data requests.",
      eyebrow: "Contact",
      heading: "Talk to the Class Hero Hub team.",
      intro:
        "Use the same support address for school product questions, pilot enquiries, operational support, privacy questions and account or data-request guidance.",
      highlights: [
        "Product enquiries",
        "School support",
        "Privacy and data requests",
      ],
      sections: [
        {
          title: "Product and pilot enquiries",
          text: "Tell us your school, role, country or timezone and the workflows you would like to explore. Do not include sensitive student information.",
        },
        {
          title: "Existing school support",
          text: "Include the school name, the affected area and a concise description of what you expected and what happened. Never email passwords, tokens, private messages or safeguarding evidence.",
        },
        {
          title: "Parents and guardians",
          text: "Parents use Family Hero Hub for linked school information. For a school-record question, contact the school first. For an FHH family-account question, use Family Hero Hub support.",
        },
        {
          title: "Privacy, access and data requests",
          text: "The school normally handles requests about school records. Contact CHH support for platform-account questions or help identifying the correct route.",
        },
      ],
      notice: {
        title: "Support email",
        text: "support@classherohub.com",
      },
      cta: {
        heading: "Send a concise, non-sensitive enquiry.",
        text: "We will route it to the appropriate product, support or privacy next step.",
        label: "Email support@classherohub.com",
        href: supportEmailHref,
        secondaryLabel: "Data and account requests",
        secondaryHref: "/data-requests",
      },
    },
    administratorGuide: {
      pageTitle: "Class Hero Hub school administrator guide",
      metaDescription:
        "A concise guide for school administrators setting up structures, staff, rosters, imports, features, communication and governance in CHH.",
      eyebrow: "School administrator guide",
      heading:
        "Build a reliable school foundation before the busy work begins.",
      intro:
        "School administrators control the structure, people and settings that determine what authorised staff and linked families can see and do.",
      sections: [
        {
          title: "1. Confirm school identity and scope",
          text: "Check the school and branch names, timezone, default language and current authorised administrators before adding operational records.",
        },
        {
          title: "2. Create the academic structure",
          text: "Set the current academic year, grade levels, class sections, subjects and optional subject groups. Assign staff only after the structure is correct.",
        },
        {
          title: "3. Add staff, students and guardians",
          text: "Invite staff into the correct roles and assignments. Add students manually or use a staged CSV import, then review guardian records and links.",
        },
        {
          title: "4. Configure school workflows",
          text: "Review behaviour categories, points policy, family-facing features, messaging availability, contact hours, surveys and other controls before broad use.",
        },
        {
          title: "5. Publish with the correct audience",
          text: "Check whether each homework item, notice, update, calendar event, survey or message is intended for the school, a class, a group or selected families.",
        },
        {
          title: "6. Monitor, correct and export",
          text: "Use reports, delivery state, audit information and supported exports. Correct records through the intended workflow rather than silently rewriting history.",
        },
        {
          title: "7. Keep safeguarding separate",
          text: "Grant protected review only to explicitly authorised people. Reviews require a reason and do not turn reviewers into message participants.",
        },
        {
          title: "8. Prepare the next academic year",
          text: "Use annual-update and history-aware processes so prior enrolments and records remain meaningful. Validate staged changes before they become current.",
        },
      ],
      cta: {
        heading: "Need help with a school setup decision?",
        text: "Contact support without sending student records or credentials by email.",
        label: "Contact support",
        href: supportEmailHref,
        secondaryLabel: "Read the teacher guide",
        secondaryHref: "/guides/teacher",
      },
    },
    teacherGuide: {
      pageTitle: "Class Hero Hub teacher guide",
      metaDescription:
        "A concise CHH guide for teachers using classes, behaviour, homework, updates, messaging, receipts and bilingual presentation.",
      eyebrow: "Teacher guide",
      heading:
        "Work from the class context, with the next action close at hand.",
      intro:
        "Teachers use CHH only for the schools, classes and students covered by their active assignments and permissions.",
      sections: [
        {
          title: "Start from your assigned classes",
          text: "After signing in, choose the relevant class or subject group. If an expected class is missing, ask the school administrator to review your assignment.",
        },
        {
          title: "Record behaviour in context",
          text: "Choose the student or authorised group and the school-defined category. Add a useful note only when needed. Needs-work information remains private.",
        },
        {
          title: "Recognise positive effort",
          text: "Positive recognition should be supported by recorded evidence and staff judgement. CHH does not use negative behaviour to create public rankings.",
        },
        {
          title: "Set homework and diary items",
          text: "Use a clear title, audience, date or due date and only the information families need. Confirm the class or group before publishing.",
        },
        {
          title: "Share notices, updates and photos",
          text: "Choose the correct audience and use protected photo workflows where available. Do not reuse protected media outside its intended school context.",
        },
        {
          title: "Use School Chats responsibly",
          text: "Text, photo and voice messaging may show delivery and read state and may be limited by school contact hours. Keep communication professional and within school policy.",
        },
        {
          title: "Switch language when needed",
          text: "The interface supports English and Arabic. Changing the interface language does not translate or alter names and content entered by the school.",
        },
        {
          title: "Remember the parent boundary",
          text: "Parents reply or view enabled school information through Family Hero Hub. A teacher who is also a parent uses FHH separately for their own family.",
        },
      ],
      cta: {
        heading: "Something does not match your assignment or school policy?",
        text: "Start with your school administrator, then contact support if platform help is needed.",
        label: "Contact support",
        href: supportEmailHref,
        secondaryLabel: "Read the safety guidance",
        secondaryHref: "/safety-privacy",
      },
    },
    familyGuide: {
      pageTitle: "Parent and Family Hero Hub guide for linked schools",
      metaDescription:
        "A clear guide explaining that parents use Family Hero Hub — not CHH — to view enabled information from a linked school.",
      eyebrow: "Parent / FHH guide",
      heading: "Parents use Family Hero Hub for linked school information.",
      intro:
        "Class Hero Hub is the school staff system. Family Hero Hub is the family app. Parents and guardians do not sign in to CHH.",
      highlights: [
        "No CHH parent login",
        "School link required",
        "Features depend on the school",
      ],
      sections: [
        {
          title: "Connect through the school’s process",
          text: "A school provides its approved linking route or code. Complete the link in Family Hero Hub and confirm the child and school information shown there.",
        },
        {
          title: "View enabled school information in FHH",
          text: "A linked school may make homework, notices, updates, protected photos, school points, calendar items, surveys and School Chats available.",
        },
        {
          title: "Your school decides what is available",
          text: "The visible information depends on the school’s enabled features, the child’s active link and the current school records. Not every school uses every feature.",
        },
        {
          title: "School and home information stay separate",
          text: "Family points, rewards, routines and household settings stay in FHH. They are not shared with the school simply because the child has a school link.",
        },
        {
          title: "Use the correct support route",
          text: "Ask the school about the accuracy or availability of school records. Contact Family Hero Hub support for family-account, household or device access questions.",
        },
        {
          title: "If you are also school staff",
          text: "Use CHH only for your authorised staff responsibilities. Use FHH for your own family. The two roles remain separate even when the same person holds both.",
        },
      ],
      notice: {
        title: "No Class Hero Hub parent app",
        text: "Do not look for or install a separate CHH parent app. The family-facing experience is provided through Family Hero Hub.",
      },
      cta: {
        heading: "Open the family-facing product",
        text: "Visit Family Hero Hub to learn about the parent-led family space and linked school information.",
        label: "Visit Family Hero Hub",
        href: "https://familyherohub.com",
        secondaryLabel: "Read the family connection",
        secondaryHref: "/family-connection",
      },
    },
    safetyPrivacy: {
      pageTitle: "Class Hero Hub safety, privacy and support information",
      metaDescription:
        "Learn about CHH school and role scoping, private behaviour records, dedicated safeguarding review, protected media, audit and the FHH data boundary.",
      eyebrow: "Safety, privacy and support",
      heading:
        "Clear authority for school data. Deliberate boundaries for protected work.",
      intro:
        "CHH is designed to help schools limit access to the people, records and workflows that their current roles require. This page describes the product approach, not a legal or security guarantee.",
      highlights: [
        "Role-scoped access",
        "Private needs-work records",
        "Dedicated safeguarding review",
      ],
      sections: [
        {
          title: "School, tenancy and role scope",
          text: "School records remain tied to the school. Staff access depends on active memberships, roles and assignments; links and identifiers used across system boundaries are intentionally scoped and opaque.",
        },
        {
          title: "Private behaviour information",
          text: "Positive and needs-work behaviour may be recorded, but negative behaviour is not used for public rankings or shaming. Positive recognition can use transparent evidence and staff review.",
        },
        {
          title: "Safeguarding is a separate mode",
          text: "Safeguarding access is explicitly granted, reason-gated, time-aware and audited. A reviewer does not become a participant and does not change receipts, unread counts or notifications.",
        },
        {
          title: "Protected messages and media",
          text: "Text, protected photos and voice notes use school-scoped access paths. Evidence and protected media should be handled only through authorised product workflows.",
        },
        {
          title: "Family data stays on the family side",
          text: "Parents use FHH. CHH does not need FHH device tokens or unnecessary family identifiers, and family clients do not call CHH directly.",
        },
        {
          title: "Audit, health and portability",
          text: "Authorised operational views, audit records and supported exports help schools understand service state and retain accountable records.",
        },
        {
          title: "Report a concern safely",
          text: "For an immediate child-safety concern, follow the school’s safeguarding and emergency procedures first. For a platform issue, contact support without emailing protected evidence.",
        },
        {
          title: "No absolute guarantee",
          text: "No online service can promise perfect security or uninterrupted availability. CHH is designed to reduce unnecessary exposure, preserve boundaries and support controlled response when something needs review.",
        },
      ],
      cta: {
        heading: "Need help with access, privacy or a product safety question?",
        text: "Contact support with a non-sensitive summary. Do not email private messages, survey answers or safeguarding evidence.",
        label: "Contact support",
        href: supportEmailHref,
        secondaryLabel: "Read the Privacy Policy",
        secondaryHref: "/privacy",
      },
    },
    privacy: {
      pageTitle: "Privacy Policy | Class Hero Hub",
      metaDescription:
        "Class Hero Hub public privacy information for school staff accounts, school records, protected content, Family Hero Hub integration, retention, requests and support.",
      eyebrow: "Legal information",
      heading: "Privacy Policy",
      intro:
        "Last updated: 2 August 2026. This policy explains the information CHH uses to provide its school-facing service and the choices available to schools and users.",
      sections: [
        {
          title: "1. Scope and roles",
          text: "CHH is for schools and authorised school users. A participating school controls the school records, purposes and people it places in the service. The precise legal controller and processor roles must be confirmed in the applicable school agreement and jurisdiction.",
        },
        {
          title: "2. Information used by CHH",
          text: "CHH may process authorised staff account details; school, branch and academic structures; staff assignments; student and guardian records; imports and exports; behaviour, homework, diary, notice, update, calendar, survey, message and report information; protected media; safeguarding records; and technical, session, audit and operational information needed to run and protect the service.",
        },
        {
          title: "3. How information is used",
          text: "Information is used to authenticate users, apply school and role scope, provide enabled school workflows, deliver linked school information through FHH, maintain records and history, support authorised reports and exports, protect the service, investigate operational issues and respond to support or legal obligations.",
        },
        {
          title: "4. Students, guardians and family access",
          text: "Students and guardians do not receive CHH staff accounts merely because the school stores their records. Parents view enabled information through FHH after an active school link. Family clients do not call CHH directly.",
        },
        {
          title: "5. CHH and FHH data boundary",
          text: "CHH remains the authority for school records. FHH owns family, parent, child, household and device identity and accesses protected school information through its server-side proxy. CHH does not require FHH device tokens or unnecessary family identifiers.",
        },
        {
          title: "6. Sharing and service providers",
          text: "Information may be handled by providers used to host, operate, secure, deliver or support the service and by FHH only for the linked-school workflows described above. CHH does not make school records public. Any further disclosures must follow the applicable school arrangement or legal requirement.",
        },
        {
          title: "7. Retention and records",
          text: "School information is retained while needed for the service, school recordkeeping, audit, security, support, safeguarding or legal obligations. Some records are historical or append-only by design. Deleted information may remain in protected backups until normal rotation completes, subject to the applicable operational and legal requirements.",
        },
        {
          title: "8. Security and access",
          text: "CHH uses school and role scoping, controlled sessions, opaque integration identifiers, audit records and protected workflows to reduce unnecessary exposure. No online service can promise perfect security.",
        },
        {
          title: "9. Requests and corrections",
          text: "Requests about a student or school record should normally be made to the school that controls it. Authorised school users may correct records or use supported exports according to their permissions. Platform-account and routing questions can be sent to CHH support.",
        },
        {
          title: "10. Changes and contact",
          text: "This policy may be updated as the service, school agreements or legal requirements develop. Material wording and jurisdiction-specific obligations require review before general commercial launch. Contact support@classherohub.com with privacy questions without including sensitive school data.",
        },
      ],
      notice: {
        title: "Legal review required",
        text: "Controller/processor roles, jurisdiction, retention periods, subprocessor disclosures, cross-border transfer wording and statutory rights must be confirmed by Dom and appropriate legal counsel before general commercial use.",
      },
      cta: {
        heading: "Need the correct route for a privacy or data question?",
        text: "Start with the school for school records, or contact CHH support for platform-account and routing help.",
        label: "Data and account requests",
        href: "/data-requests",
        secondaryLabel: "Contact support",
        secondaryHref: supportEmailHref,
      },
    },
    terms: {
      pageTitle: "Terms of Service | Class Hero Hub",
      metaDescription:
        "Pilot-stage terms for authorised school use of Class Hero Hub, including role boundaries, acceptable use, school responsibilities and service limitations.",
      eyebrow: "Legal information",
      heading: "Terms of Service",
      intro:
        "Last updated: 2 August 2026. These public terms describe the intended conditions for demonstration and pilot use. A signed school agreement takes precedence where applicable.",
      sections: [
        {
          title: "1. Purpose of the service",
          text: "CHH is a school-facing product for authorised school administration, teaching, communication, family engagement, reporting and protected review. It is not an emergency service, a substitute for professional safeguarding judgement or a parent app.",
        },
        {
          title: "2. Authorised users and roles",
          text: "Users must access CHH only through an account and school role they are authorised to use. Schools are responsible for assigning and reviewing staff roles, class assignments and specialist permissions.",
        },
        {
          title: "3. School responsibility",
          text: "The school is responsible for the accuracy, lawfulness and appropriateness of the records, audiences, communications, policies and instructions it places in CHH, and for deciding which features are enabled for its community.",
        },
        {
          title: "4. Parents and Family Hero Hub",
          text: "Parents and guardians do not use CHH directly. They may view enabled information through FHH after an active school link. A staff role in CHH does not grant family access, and family access does not grant staff permissions.",
        },
        {
          title: "5. Acceptable use",
          text: "Do not attempt unauthorised access, bypass school or role scope, share credentials, interfere with security, upload unlawful or harmful content, misuse protected information, or use the product to rank, shame or publicly expose negative student behaviour.",
        },
        {
          title: "6. Safeguarding and emergencies",
          text: "Schools remain responsible for safeguarding decisions, mandatory procedures and emergency response. CHH’s safeguarding workflow supports controlled review but does not replace school policy, designated professionals or emergency services.",
        },
        {
          title: "7. Imports, exports and integrations",
          text: "Schools are responsible for checking staged imports, authorised exports and integration results. FHH integration is limited to linked-school workflows and does not merge the two products’ identity authorities.",
        },
        {
          title: "8. Pilot availability and change",
          text: "Demonstration and pilot access may be limited, changed, suspended or ended while the product is evaluated and improved. Enabled features and support arrangements are agreed with the participating school.",
        },
        {
          title: "9. Service limitations",
          text: "CHH is provided as a school workflow tool. It cannot be guaranteed to be uninterrupted, error-free or suitable for every school situation. Schools remain responsible for operational continuity and professional decisions.",
        },
        {
          title: "10. Commercial and jurisdiction terms",
          text: "Public pricing, payment terms, governing law, liability limits, service levels, data-protection terms and termination provisions are not defined by this page and must be agreed in the applicable school contract before commercial use.",
        },
        {
          title: "11. Contact",
          text: "Contact support@classherohub.com with a non-sensitive summary of any question about these terms or pilot access.",
        },
      ],
      notice: {
        title: "Legal review required",
        text: "These pilot-stage terms require Dom and professional legal review before general commercial launch. They do not invent governing law, pricing, service levels or liability terms.",
      },
      cta: {
        heading: "Questions about pilot conditions?",
        text: "Contact the team before introducing real school data or relying on a workflow outside the agreed scope.",
        label: "Contact support",
        href: supportEmailHref,
        secondaryLabel: "Read the Privacy Policy",
        secondaryHref: "/privacy",
      },
    },
    dataRequests: {
      pageTitle: "Class Hero Hub data and account requests",
      metaDescription:
        "Find the correct route for CHH school-record, staff-account, access, correction, export and deletion enquiries.",
      eyebrow: "Data and account requests",
      heading: "Start with the organisation that controls the record.",
      intro:
        "School records, CHH staff accounts and FHH family accounts have different authorities. Using the correct route helps protect identity and avoids exposing sensitive information in email.",
      highlights: [
        "School records → the school",
        "CHH account → school admin or CHH support",
        "FHH family account → FHH support",
      ],
      sections: [
        {
          title: "Student, guardian or school-record requests",
          text: "Contact the school that created or manages the record. The school is normally best placed to verify identity, correct school information and decide how the request should be handled.",
        },
        {
          title: "CHH staff account or access",
          text: "Ask the school administrator to review your staff role, assignment or membership. Contact CHH support if the school confirms the role is correct but platform access still fails.",
        },
        {
          title: "Exports and portability",
          text: "Authorised school roles can use supported exports for available records and reports. A school can contact CHH support for help identifying an appropriate export route.",
        },
        {
          title: "Correction, restriction or deletion",
          text: "School records may be subject to historical, audit, safeguarding, legal-hold or backup requirements. Requests are assessed by the school and service according to the applicable authority and agreement; deletion is not always the correct or immediately available action.",
        },
        {
          title: "Family Hero Hub accounts",
          text: "FHH owns family, household and device identity. Use Family Hero Hub support for family-account, caregiver, child-dashboard or linked-device requests. A CHH school link does not move that identity into CHH.",
        },
        {
          title: "What to include",
          text: "Provide your name, school, role, a safe contact address and the type of request. Do not send passwords, tokens, full student datasets, private messages, survey answers or safeguarding evidence by email.",
        },
      ],
      notice: {
        title: "Identity checks may be required",
        text: "Support may ask the school or requester to verify authority before disclosing, changing or exporting protected information.",
      },
      cta: {
        heading: "Not sure which route applies?",
        text: "Send a minimal, non-sensitive summary and we will help identify the correct next step.",
        label: "Email CHH support",
        href: supportEmailHref,
        secondaryLabel: "Read the Privacy Policy",
        secondaryHref: "/privacy",
      },
    },
  },
};

const ar: PublicSiteCopy = {
  nav: {
    product: "المنتج",
    howItWorks: "كيف يعمل",
    schools: "للمدارس",
    familyConnection: "الربط مع الأسرة",
    requestPilot: "اطلب تجربة",
    staffLogin: "دخول الموظفين",
    dashboard: "لوحة المعلومات",
    menu: "استكشف كلاس هيرو هب",
    openMenu: "فتح قائمة الموقع العام",
    closeMenu: "إغلاق قائمة الموقع العام",
  },
  footer: {
    description:
      "كلاس هيرو هب مساحة العمل المدرسية للتواصل وتحديثات التعلم والسلوك ومشاركة الأسرة والعمليات المدرسية.",
    tagline: "حياة مدرسية مترابطة بوضوح.",
    product: "المنتج",
    support: "الدعم",
    legal: "المعلومات القانونية",
    home: "الرئيسية",
    features: "نظرة عامة على المنتج",
    howItWorks: "كيف يعمل",
    schools: "للمدارس",
    familyConnection: "الربط مع Family Hero Hub",
    faq: "الأسئلة الشائعة",
    requestPilot: "طلب تجربة",
    contact: "تواصل معنا",
    administratorGuide: "دليل مسؤول المدرسة",
    teacherGuide: "دليل المعلم",
    familyGuide: "دليل ولي الأمر وFHH",
    safetyPrivacy: "السلامة والخصوصية والدعم",
    privacy: "سياسة الخصوصية",
    terms: "شروط الخدمة",
    dataRequests: "طلبات البيانات والحساب",
    emailLabel: "الدعم والاستفسار عن التجربة",
  },
  home: {
    pageTitle: "كلاس هيرو هب | حياة مدرسية مترابطة بوضوح",
    metaDescription:
      "مساحة عمل مدرسية مترابطة للتواصل والسلوك وتحديثات التعلم والتقارير ومشاركة الأسرة المحمية من خلال Family Hero Hub.",
    eyebrow: "حياة مدرسية مترابطة بوضوح",
    heading: "مكان واحد واضح للعمل الذي يحافظ على سير المدرسة.",
    intro:
      "تجمع كلاس هيرو هب العمليات المدرسية ومسارات التدريس والتواصل ومشاركة الأسرة، من دون تعقيد منصات الإدارة المدرسية التقليدية.",
    primaryCta: "اطلب تجربة",
    secondaryCta: "استكشف المنتج",
    strapline:
      "للموظفين المصرح لهم · يستخدم أولياء الأمور Family Hero Hub · بالعربية والإنجليزية",
    schoolWorkspaceLabel: "مساحة عمل المدرسة",
    schoolWorkspaceTitle: "أعدها مرة، واعمل بوضوح كل يوم.",
    schoolWorkspaceText:
      "نظّم السنوات والصفوف والقوائم والموظفين، ثم أدر التدريس والتواصل والتقارير والمراجعة من مساحة واحدة مقيدة بالمدرسة.",
    familyDeliveryLabel: "إيصال المعلومات للأسرة",
    familyDeliveryTitle: "تصل المعلومات المناسبة إلى المنزل.",
    familyDeliveryText:
      "يرى أولياء الأمور المرتبطون معلومات المدرسة المفعلة في Family Hero Hub، ولا يسجلون الدخول إلى نظام الموظفين.",
    boundaryLabel: "فصل واضح بين الأدوار",
    boundaryText:
      "كلاس هيرو هب لموظفي المدرسة والأدوار المدرسية المصرح لها. وFamily Hero Hub لهوية الأسرة وأولياء الأمور والأوصياء.",
    benefitsEyebrow: "مصممة حول اليوم المدرسي",
    benefitsHeading: "تنقل أقل. رؤية أفضل. مسؤولية أوضح.",
    benefitsIntro:
      "تنظم كلاس هيرو هب العمل الذي تقوم به المدارس أصلا، مع إبقاء الوصول والأدلة وإيصال المعلومات للأسر مرتبطا بالمدرسة والدور الصحيحين.",
    benefits: [
      {
        title: "نظّم الأساس",
        text: "حافظ على الفروع والسنوات الدراسية والصفوف والمواد والقوائم والسجلات منظمة وجاهزة للسنة.",
      },
      {
        title: "ادعم التدريس اليومي",
        text: "سجّل السلوك وقدّر الجهد الإيجابي وحدد الواجبات وشارك معلومات الصف في الوقت المناسب من مسار المعلم نفسه.",
      },
      {
        title: "أبق الأسر على اطلاع",
        text: "أوصل الواجبات والتنبيهات والتحديثات والنقاط والتقويم والاستبيانات ومحادثات المدرسة المفعلة من خلال Family Hero Hub.",
      },
      {
        title: "قد المدرسة بالأدلة",
        text: "استخدم التقارير والاتجاهات والإيصالات وسجلات التدقيق ومراجعة الحماية المخصصة لفهم ما حدث وما يحتاج إلى اهتمام.",
      },
    ],
    workflowEyebrow: "كيف تعمل",
    workflowHeading: "من إعداد المدرسة إلى أسرة أوضح اطلاعا.",
    workflowIntro:
      "تبقى كل خطوة ضمن الدور وحدود البيانات الصحيحة، من سجل المدرسة إلى العرض المخصص للأسرة.",
    workflow: [
      {
        title: "ابن الهيكل المدرسي",
        text: "يضبط مسؤولو المدرسة بيانات المدرسة والسنة الحالية والصفوف والمواد والموظفين والقوائم يدويا أو عبر استيراد CSV مرحلي.",
      },
      {
        title: "يعمل الموظفون في سياقهم",
        text: "يرى الموظفون المصرح لهم الصفوف والطلاب والمسارات التي يسمح بها دورهم، من الواجبات والتقدير إلى التنبيهات والرسائل والتقارير.",
      },
      {
        title: "تحمي المنصة المعلومات وتوصلها",
        text: "تبقى بيانات المدرسة مقيدة بها، وتعبر معلومات الأسرة المفعلة حدود التكامل المحمية من خادم إلى خادم.",
      },
      {
        title: "يستخدم أولياء الأمور Family Hero Hub",
        text: "يرى أولياء الأمور معلومات مدرسة طفلهم المرتبط في FHH إلى جانب أدوات الأسرة، ولا يستخدمون كلاس هيرو هب مباشرة.",
      },
    ],
    featureEyebrow: "قدرات مترابطة",
    featureHeading: "صورة كاملة للمنتج، منظمة بحسب العمل الذي تدعمه.",
    featureIntro:
      "ابدأ بالأساسيات التي تحتاجها المدرسة الآن، ثم فعّل مسارات تواصل ومشاركة وحوكمة إضافية عندما تكون المدرسة جاهزة.",
    featureGroups: [
      {
        title: "أساس المدرسة",
        text: "أنشئ هيكلا موثوقا لكل مسار عمل مصرح به.",
        items: [
          "المدارس والفروع والسنوات الدراسية",
          "الصفوف والمواد وتكليفات الموظفين",
          "سجلات الطلاب وأولياء الأمور",
          "استيراد CSV من MIS أو SMS والتحديثات السنوية والسجل والصادرات",
        ],
      },
      {
        title: "التدريس والتعلم",
        text: "اجعل إجراءات الصف اليومية سريعة وواضحة ومترابطة.",
        items: [
          "نقاط السلوك الإيجابي وما يحتاج إلى تحسين",
          "تقدير إيجابي قائم على الأدلة وشهادات",
          "الواجبات والمفكرة والأغراض المطلوبة",
          "التنبيهات والتقويم وتحديثات المدرسة والصور المحمية",
        ],
      },
      {
        title: "التواصل والمشاركة",
        text: "امنح الأشخاص المناسبين قناة واضحة من دون فتح وصول غير ضروري.",
        items: [
          "رسائل نصية وصور محمية ورسائل صوتية",
          "إيصالات التسليم والقراءة",
          "ضوابط ساعات التواصل المدرسي",
          "الاستبيانات والتصويت والربط مع Family Hero Hub",
        ],
      },
      {
        title: "الرؤى والحوكمة",
        text: "ادعم قرارات المدرسة والمراجعة المحمية بسجلات قابلة للتتبع.",
        items: [
          "التقارير واتجاهات السلوك",
          "مراجعة الحماية ومعالجة الأدلة في مسار مخصص",
          "الصحة التشغيلية وسجلات التدقيق",
          "العربية والإنجليزية وأدوات قابلية نقل البيانات",
        ],
      },
    ],
    familyEyebrow: "كلاس هيرو هب + Family Hero Hub",
    familyHeading: "تبقى المدرسة مسيطرة، وترى الأسر ما يهم.",
    familyIntro: "للمنتجين مسؤوليات منفصلة وبينهما اتصال محمي.",
    schoolSideTitle: "١ · يستخدم موظفو المدرسة كلاس هيرو هب",
    schoolSideText:
      "ينشئ الموظفون المصرح لهم سجلات المدرسة ومعلومات التدريس والتواصل والمحتوى المفعّل الموجه للأسر ويديرونها.",
    connectionTitle: "٢ · اتصال محمي بين الخوادم",
    connectionText:
      "يطلب FHH معلومات المدرسة المرتبطة عبر وسيط CHH في الخادم باستخدام معرفات مبهمة ومقيدة. ولا تتصل أجهزة الأسرة بـ CHH مباشرة.",
    familySideTitle: "٣ · يستخدم أولياء الأمور FHH",
    familySideText:
      "يرى أولياء الأمور والأوصياء المعلومات المفعلة للطفل المرتبط في Family Hero Hub. وتبقى هوية الأسرة والمنزل والجهاز على جانب الأسرة.",
    familyBoundary:
      "المعلم الذي يكون ولي أمر أيضا يستخدم CHH في دوره الوظيفي وFHH في دوره الأسري. ولا يندمج الدوران.",
    familyCta: "تعرف على الربط مع الأسرة",
    trustEyebrow: "الخصوصية والحماية",
    trustHeading: "مصممة لثقة المدرسة من دون وعود مبالغ فيها.",
    trustIntro:
      "تستخدم كلاس هيرو هب حدود وصول واضحة ومسارات مخصصة للعمل المحمي. لا يمكن لأي خدمة إلكترونية أن تضمن أمانا مثاليا، لكن المنتج مصمم لتقليل التعرض غير الضروري وإبقاء السلطة صريحة.",
    trustItems: [
      {
        title: "تقييد الوصول بالمدرسة والدور",
        text: "يرى المستخدمون المصرح لهم المدارس والصفوف والطلاب والأدوات التي تسمح بها أدوارهم وتكليفاتهم النشطة فقط.",
      },
      {
        title: "سجلات سلوك خاصة",
        text: "لا تتحول معلومات ما يحتاج إلى تحسين إلى تصنيفات علنية أو تشهير. ويبقى التقدير الإيجابي قائما على الأدلة ومراجعة الموظفين.",
      },
      {
        title: "مراجعة حماية منفصلة",
        text: "لا تجعل المراجعة المحمية المراجع مشاركا في المحادثة، ولا تغير الإيصالات أو غير المقروء أو الإشعارات.",
      },
      {
        title: "عمليات قابلة للتتبع",
        text: "تدعم سجلات التدقيق وفحوص الصحة التشغيلية والصادرات المصرح بها ومسارات الأدلة المضبوطة إدارة مسؤولة.",
      },
    ],
    bilingualEyebrow: "العربية + English",
    bilingualHeading: "منتج واحد جاهز للمجتمعات المدرسية ثنائية اللغة.",
    bilingualText:
      "تدعم كلاس هيرو هب العربية المهنية والإنجليزية في الموقع العام وواجهة المنتج، بما في ذلك التخطيطات من اليمين إلى اليسار.",
    bilingualPoint1:
      "يمكن تغيير لغة الواجهة من دون تعديل الأسماء أو المحتوى الذي أدخلته المدرسة.",
    bilingualPoint2:
      "صُممت التخطيطات المتجاوبة للموظفين على الهواتف والأجهزة اللوحية وأجهزة سطح المكتب.",
    faqEyebrow: "الأسئلة الشائعة",
    faqHeading: "الأسئلة التي تطرحها المدارس والأسر أولا.",
    faqIntro:
      "إجابات واضحة عن الأدوار ووصول الأسرة ونطاق المنتج والسلامة والتوفر التجريبي.",
    faqCta: "اقرأ جميع الأسئلة",
    finalHeading: "هل أنت مستعد لمعرفة كيف تناسب CHH مدرستك؟",
    finalText:
      "أخبرنا عن مدرستك وأنظمتك الحالية والمسارات التي تريد تحسينها، وسنرد بالخطوة التالية الأنسب لعرض توضيحي أو مناقشة تجربة.",
    finalPrimary: "اطلب تجربة",
    finalSecondary: "تواصل مع الفريق",
  },
  faq: {
    pageTitle: "الأسئلة الشائعة | كلاس هيرو هب",
    metaDescription:
      "إجابات عن كلاس هيرو هب ووصول موظفي المدرسة وإيصال المعلومات للأهل عبر Family Hero Hub والخصوصية والحماية والاستيراد والتصدير والوصول التجريبي.",
    eyebrow: "إجابات مباشرة",
    heading: "الأسئلة الشائعة",
    intro:
      "تضع CHH حدا واضحا ومقصودا بين المدرسة والأسرة. توضح هذه الإجابات من يستخدم كل منتج وكيف تترابط المسارات الرئيسية.",
    items: arabicFaq,
    ctaHeading: "هل لديك سؤال خاص بمدرستك؟",
    ctaText: "أرسل استفسارا موجزا من دون معلومات حساسة عن الطلاب أو الحماية.",
    ctaLabel: "تواصل مع كلاس هيرو هب",
  },
  pages: {
    howItWorks: {
      pageTitle: "كيف تعمل كلاس هيرو هب",
      metaDescription:
        "تعرف على إعداد المدرسة في CHH ومسارات الموظفين المقيدة بالأدوار وكيف يتلقى أولياء الأمور المرتبطون معلومات المدرسة المفعلة عبر Family Hero Hub.",
      eyebrow: "كيف تعمل",
      heading: "مسار واضح من إعداد المدرسة إلى فهم الأسرة.",
      intro:
        "تربط CHH عمل مسؤولي المدرسة والمعلمين من دون خلط ملكية بيانات المدرسة أو هوية الأسرة أو المراجعة المحمية.",
      highlights: ["مقيدة بالمدرسة", "مراعية للأدوار", "إيصال الأسرة عبر FHH"],
      sections: [
        {
          title: "١. إعداد المدرسة",
          text: "ينشئ مسؤولو المدرسة الهيكل التشغيلي الذي تعتمد عليه جميع المسارات اللاحقة.",
          bullets: [
            "بيانات المدرسة والفروع",
            "السنوات الدراسية والصفوف والمواد",
            "أدوار الموظفين وتكليفاتهم",
            "فئات السلوك والميزات المفعلة",
          ],
        },
        {
          title: "٢. نقل السجلات بعناية",
          text: "يمكن إعداد بيانات الطلاب وأولياء الأمور والقوائم الحالية عبر استيراد CSV مرحلي بدلا من رفع غير مضبوط بخطوة واحدة.",
          bullets: [
            "المعاينة والتحقق قبل الاعتماد",
            "مراجع MIS أو SMS الخارجية عند توفرها",
            "دعم السجل والتحديث السنوي",
            "صادرات مصرح بها لقابلية النقل",
          ],
        },
        {
          title: "٣. منح الموظفين مساحة العمل الصحيحة",
          text: "يسجل المعلمون وقادة المدرسة الدخول إلى CHH ويرون المسارات المناسبة لأدوارهم وصفوفهم وتكليفاتهم الحالية.",
          bullets: [
            "سياق الصف والطالب",
            "الواجبات والمفكرة والتقويم",
            "السلوك والتقدير الإيجابي",
            "التنبيهات والتحديثات والرسائل والاستبيانات والتقارير",
          ],
        },
        {
          title: "٤. تواصل يمكن متابعته",
          text: "تبقى اتصالات المدرسة مرتبطة بالجمهور والسياق المدرسي الصحيحين، مع حالة التسليم وضوابط السياسة عند دعمها.",
          bullets: [
            "النصوص والصور المحمية والرسائل الصوتية",
            "إيصالات التسليم والقراءة",
            "ضوابط ساعات التواصل",
            "التحديثات المحمية وعناصر تقويم المدرسة",
          ],
        },
        {
          title: "٥. إيصال المعلومات للأسر عبر FHH",
          text: "لا يدخل أولياء الأمور نظام الموظفين. يعرض Family Hero Hub معلومات المدرسة المفعلة فقط لطفل لديه رابط مدرسي نشط ومتحقق.",
        },
        {
          title: "٦. المراجعة والتقرير والتحسين",
          text: "يمكن للقادة المصرح لهم استخدام التقارير والاتجاهات والتدقيق والصادرات. وتبقى مراجعة الحماية مسارا منفصلا مرتبطا بسبب وخاضعا للتدقيق.",
        },
      ],
      notice: {
        title: "الحد الفاصل مهم",
        text: "تملك CHH بيانات المدرسة ووصولها. ويملك FHH هوية الأسرة وولي الأمر والطفل والمنزل والجهاز. ولا تتصل تطبيقات الأسرة بـ CHH مباشرة.",
      },
      cta: {
        heading: "راجع المسار مع وضع هيكل مدرستك في الاعتبار.",
        text: "اطلب عرضا توضيحيا أو مناقشة تجربة مع فريق كلاس هيرو هب.",
        label: "اطلب تجربة",
        href: "/pilot",
        secondaryLabel: "استكشف جميع الميزات",
        secondaryHref: "/features",
      },
    },
    features: {
      pageTitle: "نظرة عامة وميزات كلاس هيرو هب",
      metaDescription:
        "استكشف إعداد المدرسة والقوائم والسلوك وتحديثات التعلم والرسائل والاستبيانات والتقارير والحماية ودعم اللغتين والربط مع Family Hero Hub.",
      eyebrow: "نظرة عامة على المنتج",
      heading: "مسارات المدرسة المترابطة التي تهم الآن.",
      intro:
        "نُظمت CHH حول طريقة عمل المدارس: إعداد الهيكل ودعم الموظفين والتواصل بوضوح وإشراك الأسر وحوكمة العمل المحمي.",
      highlights: [
        "العمليات المدرسية",
        "مسارات التدريس",
        "مشاركة الأسرة",
        "الحوكمة",
      ],
      sections: [
        {
          title: "هيكل المدرسة وإدارتها",
          text: "أعد المدارس والفروع والسنوات الدراسية والمراحل والصفوف والمواد والتكليفات والقوائم. وأدر سجلات الطلاب وأولياء الأمور مع سجل مقيد بالمدرسة.",
          bullets: [
            "إعداد يدوي وتهيئة مدرسية موجهة",
            "استيراد CSV من MIS أو SMS مع مراجعة مرحلية",
            "تحديثات سنوية وسجل وصادرات مدعومة",
            "إدارة الأدوار والعضويات",
          ],
        },
        {
          title: "السلوك والتقدير الإيجابي",
          text: "سجّل الأحداث الإيجابية وما يحتاج إلى تحسين وفق فئات المدرسة وفي سياقها. واستخدم الأدلة الإيجابية لدعم تقدير يراجعه الموظفون وشهادات قابلة للطباعة.",
          bullets: [
            "إجراءات سريعة داخل الصف",
            "تصحيحات لا تعيد كتابة السجل بصمت",
            "خصوصية معلومات ما يحتاج إلى تحسين",
            "لا تصنيفات علنية ولا تشهير",
          ],
        },
        {
          title: "الواجبات والمفكرة والتقويم",
          text: "اربط الواجبات والاختبارات والتذكيرات والأغراض المطلوبة وأحداث التقويم بالمدرسة أو الصف أو المجموعة أو الطالب الصحيح.",
        },
        {
          title: "التنبيهات والتحديثات والوسائط المحمية",
          text: "انشر معلومات المدرسة أو الصف للجمهور المناسب، بما في ذلك صور تحديثات المدرسة المحمية عند تفعيلها.",
        },
        {
          title: "الرسائل المدرسية",
          text: "ادعم النصوص والصور المحمية والرسائل الصوتية مع إيصالات التسليم والقراءة وضوابط ساعات التواصل والتوفر الذي تحدده المدرسة.",
          bullets: [
            "سياقات المدرسة والأسرة والموظفين",
            "وصول محمي للوسائط",
            "رسائل صوتية",
            "مراجعة حماية منفصلة",
          ],
        },
        {
          title: "الاستبيانات والتصويت",
          text: "أنشئ استبيانات موجهة لأولياء الأمور، وأدر التوفر والتذكيرات، وراجع تقدم الاستجابة والنتائج بحسب صلاحيات المدرسة.",
        },
        {
          title: "التقارير والاتجاهات والعمليات",
          text: "امنح القادة المصرح لهم تقارير السلوك واتجاهاته والصادرات المدعومة وسياق التدقيق والصحة التشغيلية من دون كشف المحتوى المحمي لأدوار غير معنية.",
        },
        {
          title: "ثنائية اللغة ومتصلة بالأسرة",
          text: "استخدم CHH بالعربية أو الإنجليزية مع تخطيط RTL متجاوب، بينما يتلقى أولياء الأمور المرتبطون معلومات المدرسة المفعلة في Family Hero Hub.",
        },
      ],
      cta: {
        heading: "اختر المسارات التي تحتاجها تجربتك.",
        text: "يمكننا تركيز العرض على إعداد المدرسة أو التدريس أو التواصل مع الأسر أو التقارير أو المراجعة المحمية.",
        label: "ناقش تجربة",
        href: "/pilot",
        secondaryLabel: "شاهد كيف تعمل",
        secondaryHref: "/how-it-works",
      },
    },
    schools: {
      pageTitle: "كلاس هيرو هب لقادة المدارس وموظفيها",
      metaDescription:
        "تعرف على دعم كلاس هيرو هب لقادة المدارس والمسؤولين والمعلمين عبر مسارات مدرسية مترابطة ومقيدة بالأدوار.",
      eyebrow: "للمدارس",
      heading: "منصة مدرسية يمكن فهمها قبل الحاجة إلى إتقانها.",
      intro:
        "تمنح CHH كل دور مصرح له نقطة بداية أوضح، مع إبقاء هيكل المدرسة والأدلة والصلاحيات متسقة.",
      highlights: ["للقادة", "للمسؤولين", "للمعلمين"],
      sections: [
        {
          title: "لقادة المدارس",
          text: "شاهد الأنماط وحالة التسليم والسياق التشغيلي من دون تحويل كل سؤال قيادي إلى طلب جدول بيانات.",
          bullets: [
            "التقارير والاتجاهات",
            "رؤية مشاركة الأسرة",
            "سياق الصحة التشغيلية والتدقيق",
            "حدود حوكمة واضحة",
          ],
        },
        {
          title: "لمسؤولي المدارس",
          text: "أدر هيكل المدرسة وسجلاتها السنوية التي تجعل كل مسار للموظفين موثوقا.",
          bullets: [
            "السنوات الدراسية والصفوف والمواد",
            "سجلات الموظفين والطلاب وأولياء الأمور",
            "استيراد CSV والتحديثات السنوية والصادرات",
            "ضوابط الميزات والرسائل وساعات التواصل",
          ],
        },
        {
          title: "للمعلمين",
          text: "انتقل من سياق الصف إلى الإجراء المفيد التالي بسرعة: تقدير الجهد أو تسجيل السلوك أو تحديد واجب أو نشر تحديث أو التواصل مع أسرة.",
        },
        {
          title: "للمجتمعات ثنائية اللغة",
          text: "يمكن للموظفين استخدام العربية أو الإنجليزية مع تخطيط من اليمين إلى اليسار. وتبقى الأسماء والمحتوى المدخلان تحت سيطرة المدرسة.",
        },
        {
          title: "لإطلاق مضبوط",
          text: "ابدأ بمدرسة أو فرع أو مرحلة أو مسار محدد، واتفق على الميزات والأدوار المفعلة، ثم وسع التجربة عندما يصبح الأساس التشغيلي جاهزا.",
        },
        {
          title: "للمدارس ذات الأنظمة الحالية",
          text: "يمكن لـ CHH استخدام استيراد CSV مرحلي من صادرات MIS أو SMS الحالية. ولا تجبر المدرسة على هجرة بيانات مبهمة لا رجعة فيها.",
        },
      ],
      cta: {
        heading: "أرنا أين يتشتت العمل المدرسي حاليا.",
        text: "سنركز الحديث على المسارات التي تهم موظفيك وأسرك.",
        label: "اطلب مناقشة مدرسية",
        href: "/pilot",
        secondaryLabel: "اقرأ دليل المسؤول",
        secondaryHref: "/guides/administrator",
      },
    },
    familyConnection: {
      pageTitle: "ربط كلاس هيرو هب مع Family Hero Hub للأهل",
      metaDescription:
        "افهم كيف تصل بيانات مدرسة CHH إلى أولياء الأمور المرتبطين عبر Family Hero Hub مع بقاء هوية الموظفين والأسرة والجهاز في الجانب الصحيح.",
      eyebrow: "الربط مع الأسرة",
      heading:
        "تصل معلومات المدرسة إلى الأهل من دون منحهم وصولا إلى نظام الموظفين.",
      intro:
        "CHH وFHH منتجان مترابطان بمسؤوليات منفصلة. والحد بينهما مقصود وواضح وجزء من سهولة فهم الوصول.",
      highlights: [
        "الموظفون يستخدمون CHH",
        "الأهل يستخدمون FHH",
        "اتصال بين الخوادم",
      ],
      sections: [
        {
          title: "CHH هي مرجع المدرسة",
          text: "تدير المدارس وموظفوها المصرح لهم الهياكل المدرسية وسجلات الطلاب ومعلومات التعلم والسلوك والتواصل والاستبيانات والتقارير ومسارات الحماية في CHH.",
        },
        {
          title: "FHH هي مرجع الأسرة",
          text: "يدير Family Hero Hub هوية ولي الأمر والطفل والمنزل والجهاز، ويعرض معلومات المدرسة إلى جانب أدوات الأسرة من دون نقل هوية أجهزة الأسرة إلى CHH.",
        },
        {
          title: "لا يتصل الأهل بـ CHH مباشرة",
          text: "يطلب FHH بيانات المدرسة المحمية عبر وسيط CHH في خادمه. ويستخدم الاتصال معرفات مبهمة ومقيدة ورابطا نشطا بين الطفل والمدرسة.",
        },
        {
          title: "ما قد تراه الأسرة المرتبطة",
          text: "بحسب الميزات التي تفعلها المدرسة، قد يرى ولي الأمر الواجبات والتنبيهات والتحديثات والصور المحمية ونقاط المدرسة والتقويم والاستبيانات ومحادثات المدرسة.",
        },
        {
          title: "تبقى بيانات المنزل والمدرسة منفصلة",
          text: "تبقى نقاط الأسرة ومكافآتها وروتين المنزل ومعلومات أجهزته في FHH، ولا تُرسل إلى CHH لمجرد وجود رابط مدرسي.",
        },
        {
          title: "يمكن للشخص أن يحمل دورين منفصلين",
          text: "يستخدم المعلم الذي يكون ولي أمر CHH لعمله المصرح به وFHH لأسرته. ولا تتحول صلاحيات الموظف إلى وصول أسري ولا العكس.",
        },
      ],
      notice: {
        title: "لا يوجد تطبيق CHH للأهل",
        text: "يستخدم أولياء الأمور والأوصياء Family Hero Hub. وتتوقف معلومات المدرسة التي يمكنهم رؤيتها على ميزات المدرسة المفعلة والرابط النشط لطفلهم.",
      },
      cta: {
        heading: "هل تحتاج إلى شرح الاتصال لمجتمع مدرستك؟",
        text: "استخدم دليل ولي الأمر وFHH لشرح موجز ودقيق للأدوار.",
        label: "اقرأ دليل ولي الأمر وFHH",
        href: "/guides/families",
        secondaryLabel: "زر Family Hero Hub",
        secondaryHref: "https://familyherohub.com",
      },
    },
    pilot: {
      pageTitle: "طلب تجربة أو عرض كلاس هيرو هب",
      metaDescription:
        "تواصل مع كلاس هيرو هب لمناقشة عرض مدرسي أو تجربة محددة بعناية أو معلومات المنتج.",
      eyebrow: "التجارب والعروض",
      heading: "ابدأ بالمشكلة المدرسية التي تريد حلها.",
      intro:
        "لا توجد هنا باقة أو قائمة أسعار مختلقة. أخبرنا بما تريد مدرستك تحسينه، وسنقرر معا إن كان العرض أو التجربة المحددة هو الخطوة المناسبة.",
      highlights: ["لا أسعار معلنة بعد", "تجارب محددة", "إطلاق تقوده المدرسة"],
      sections: [
        {
          title: "عرّفنا بالمدرسة",
          text: "يتضمن الاستفسار المفيد اسم المدرسة أو المجموعة والبلد أو المنطقة الزمنية والحجم التقريبي واللغات ودور الشخص المتواصل.",
        },
        {
          title: "حدد مسار العمل",
          text: "وضح إن كانت الأولوية إعداد المدرسة أو الاستيراد أو السلوك والتقدير أو الواجبات أو التنبيهات والتحديثات أو الرسائل أو الاستبيانات أو التقارير أو الحماية أو الربط مع FHH.",
        },
        {
          title: "حدد نطاقا آمنا",
          text: "يمكن أن تبدأ التجربة بمدرسة أو فرع أو مرحلة أو مسار واحد. ويجب الاتفاق على الميزات والأدوار ومسؤوليات المراجعة قبل إدخال بيانات مدرسية حقيقية.",
        },
        {
          title: "جهز الأشخاص المناسبين",
          text: "أشرك قائدا أو راعيا مدرسيا ومسؤولا تشغيليا ومعلمين ممثلين. وأضف مسؤولي الحماية أو البيانات عندما تكون هذه المسارات ضمن النطاق.",
        },
        {
          title: "لا ترسل بيانات حساسة في الرسالة الأولى",
          text: "لا ترسل سجلات الطلاب أو الرسائل الخاصة أو إجابات الاستبيانات أو أدلة الحماية أو بيانات الدخول أو الرموز في الاستفسار.",
        },
        {
          title: "تأتي الشروط التجارية لاحقا",
          text: "لم يُحدد نموذج أسعار عام. ويجب الاتفاق صراحة على نطاق التجربة وتوقعات الدعم وأي شروط تجارية مستقبلية.",
        },
      ],
      cta: {
        heading: "اطلب مناقشة تجربة",
        text: "راسل الفريق بوصف موجز وغير حساس لمدرستك ومسار العمل ذي الأولوية.",
        label: "أرسل استفسار تجربة",
        href: pilotEmailHref,
        secondaryLabel: "اعرض ميزات المنتج",
        secondaryHref: "/features",
      },
    },
    contact: {
      pageTitle: "تواصل مع كلاس هيرو هب",
      metaDescription:
        "تواصل مع كلاس هيرو هب لمعلومات المنتج المدرسي أو التجارب أو الدعم أو أسئلة الخصوصية أو طلبات الحساب والبيانات.",
      eyebrow: "تواصل معنا",
      heading: "تحدث مع فريق كلاس هيرو هب.",
      intro:
        "استخدم عنوان الدعم نفسه لأسئلة المنتج والتجارب والدعم التشغيلي والخصوصية وإرشاد طلبات الحساب أو البيانات.",
      highlights: [
        "استفسارات المنتج",
        "دعم المدرسة",
        "الخصوصية وطلبات البيانات",
      ],
      sections: [
        {
          title: "استفسارات المنتج والتجربة",
          text: "أخبرنا عن مدرستك ودورك وبلدك أو منطقتك الزمنية والمسارات التي تريد استكشافها. لا ترفق معلومات حساسة عن الطلاب.",
        },
        {
          title: "دعم المدارس الحالية",
          text: "اذكر اسم المدرسة والجزء المتأثر ووصفا موجزا لما توقعته وما حدث. لا ترسل كلمات مرور أو رموزا أو رسائل خاصة أو أدلة حماية.",
        },
        {
          title: "أولياء الأمور والأوصياء",
          text: "يستخدم الأهل Family Hero Hub لمعلومات المدرسة المرتبطة. اسأل المدرسة أولا عن سجلاتها، واستخدم دعم FHH لأسئلة حساب الأسرة.",
        },
        {
          title: "الخصوصية والوصول والبيانات",
          text: "تتولى المدرسة عادة طلبات السجلات المدرسية. تواصل مع دعم CHH لأسئلة حساب المنصة أو للمساعدة في تحديد المسار الصحيح.",
        },
      ],
      notice: { title: "بريد الدعم", text: "support@classherohub.com" },
      cta: {
        heading: "أرسل استفسارا موجزا وغير حساس.",
        text: "سنوجهه إلى الخطوة المناسبة للمنتج أو الدعم أو الخصوصية.",
        label: "راسل support@classherohub.com",
        href: supportEmailHref,
        secondaryLabel: "طلبات البيانات والحساب",
        secondaryHref: "/data-requests",
      },
    },
    administratorGuide: {
      pageTitle: "دليل مسؤول المدرسة في كلاس هيرو هب",
      metaDescription:
        "دليل موجز لمسؤولي المدارس لإعداد الهيكل والموظفين والقوائم والاستيراد والميزات والتواصل والحوكمة في CHH.",
      eyebrow: "دليل مسؤول المدرسة",
      heading: "ابن أساسا مدرسيا موثوقا قبل بدء ضغط العمل.",
      intro:
        "يتحكم مسؤولو المدرسة في الهيكل والأشخاص والإعدادات التي تحدد ما يمكن للموظفين المصرح لهم والأسر المرتبطة رؤيته وفعله.",
      sections: [
        {
          title: "١. تأكد من هوية المدرسة ونطاقها",
          text: "راجع أسماء المدرسة والفروع والمنطقة الزمنية واللغة الافتراضية والمسؤولين الحاليين قبل إضافة السجلات التشغيلية.",
        },
        {
          title: "٢. أنشئ الهيكل الدراسي",
          text: "حدد السنة الحالية والمراحل والصفوف والمواد ومجموعات المواد الاختيارية، ثم عيّن الموظفين بعد التأكد من الهيكل.",
        },
        {
          title: "٣. أضف الموظفين والطلاب وأولياء الأمور",
          text: "ادع الموظفين إلى الأدوار والتكليفات الصحيحة. أضف الطلاب يدويا أو باستيراد CSV مرحلي، ثم راجع سجلات وروابط أولياء الأمور.",
        },
        {
          title: "٤. اضبط مسارات المدرسة",
          text: "راجع فئات السلوك وسياسة النقاط والميزات الموجهة للأسر وتوفر الرسائل وساعات التواصل والاستبيانات قبل الاستخدام الواسع.",
        },
        {
          title: "٥. انشر للجمهور الصحيح",
          text: "تأكد مما إذا كان كل واجب أو تنبيه أو تحديث أو حدث تقويم أو استبيان أو رسالة موجها للمدرسة أو صف أو مجموعة أو أسر محددة.",
        },
        {
          title: "٦. راقب وصحح وصدّر",
          text: "استخدم التقارير وحالة التسليم والتدقيق والصادرات المدعومة. صحح السجلات عبر المسار المخصص بدلا من إعادة كتابة التاريخ بصمت.",
        },
        {
          title: "٧. أبق الحماية منفصلة",
          text: "امنح الوصول المحمي فقط للمصرح لهم صراحة. تتطلب المراجعات سببا ولا تجعل المراجعين مشاركين في الرسائل.",
        },
        {
          title: "٨. استعد للسنة التالية",
          text: "استخدم إجراءات تحديث سنوية تحفظ السجل لكي تبقى القوائم السابقة ذات معنى، وتحقق من التغييرات المرحلية قبل اعتمادها.",
        },
      ],
      cta: {
        heading: "هل تحتاج إلى مساعدة في قرار إعداد؟",
        text: "تواصل مع الدعم من دون إرسال سجلات الطلاب أو بيانات الدخول بالبريد.",
        label: "تواصل مع الدعم",
        href: supportEmailHref,
        secondaryLabel: "اقرأ دليل المعلم",
        secondaryHref: "/guides/teacher",
      },
    },
    teacherGuide: {
      pageTitle: "دليل المعلم في كلاس هيرو هب",
      metaDescription:
        "دليل موجز للمعلمين لاستخدام الصفوف والسلوك والواجبات والتحديثات والرسائل والإيصالات والعرض ثنائي اللغة في CHH.",
      eyebrow: "دليل المعلم",
      heading: "اعمل من سياق الصف، واجعل الإجراء التالي قريبا.",
      intro:
        "يستخدم المعلمون CHH فقط للمدارس والصفوف والطلاب المشمولين بتكليفاتهم وصلاحياتهم النشطة.",
      sections: [
        {
          title: "ابدأ من صفوفك المكلف بها",
          text: "بعد الدخول اختر الصف أو مجموعة المادة الصحيحة. إذا غاب صف متوقع، اطلب من مسؤول المدرسة مراجعة تكليفك.",
        },
        {
          title: "سجّل السلوك في سياقه",
          text: "اختر الطالب أو المجموعة المصرح بها وفئة المدرسة. أضف ملاحظة مفيدة عند الحاجة فقط. وتبقى معلومات ما يحتاج إلى تحسين خاصة.",
        },
        {
          title: "قدّر الجهد الإيجابي",
          text: "ينبغي أن يستند التقدير الإيجابي إلى أدلة مسجلة وحكم الموظف. ولا تستخدم CHH السلوك السلبي لإنشاء تصنيفات علنية.",
        },
        {
          title: "حدد الواجبات وعناصر المفكرة",
          text: "استخدم عنوانا وجمهورا وتاريخا أو موعد تسليم واضحا، وأدرج المعلومات التي تحتاجها الأسرة فقط. تأكد من الصف أو المجموعة قبل النشر.",
        },
        {
          title: "شارك التنبيهات والتحديثات والصور",
          text: "اختر الجمهور الصحيح واستخدم مسارات الصور المحمية عند توفرها. لا تعِد استخدام الوسائط المحمية خارج سياقها المدرسي.",
        },
        {
          title: "استخدم محادثات المدرسة بمسؤولية",
          text: "قد تعرض الرسائل النصية والصور والصوت حالة التسليم والقراءة وقد تقيدها ساعات تواصل المدرسة. حافظ على المهنية وسياسة المدرسة.",
        },
        {
          title: "غيّر اللغة عند الحاجة",
          text: "تدعم الواجهة العربية والإنجليزية. ولا يترجم تغيير لغة الواجهة الأسماء والمحتوى المدخل من المدرسة ولا يعدله.",
        },
        {
          title: "تذكر حد ولي الأمر",
          text: "يرد أولياء الأمور أو يرون المعلومات المفعلة عبر Family Hero Hub. ويستخدم المعلم الذي يكون ولي أمر FHH منفصلا لأسرته.",
        },
      ],
      cta: {
        heading: "هل هناك ما لا يطابق تكليفك أو سياسة مدرستك؟",
        text: "ابدأ بمسؤول المدرسة، ثم تواصل مع الدعم إذا لزم دعم المنصة.",
        label: "تواصل مع الدعم",
        href: supportEmailHref,
        secondaryLabel: "اقرأ إرشادات السلامة",
        secondaryHref: "/safety-privacy",
      },
    },
    familyGuide: {
      pageTitle: "دليل الأهل وFamily Hero Hub للمدارس المرتبطة",
      metaDescription:
        "دليل واضح يشرح أن الأهل يستخدمون Family Hero Hub وليس CHH لعرض المعلومات المفعلة من مدرسة مرتبطة.",
      eyebrow: "دليل ولي الأمر وFHH",
      heading:
        "يستخدم أولياء الأمور Family Hero Hub لمعلومات المدرسة المرتبطة.",
      intro:
        "كلاس هيرو هب نظام موظفي المدرسة، وFamily Hero Hub تطبيق الأسرة. لا يسجل أولياء الأمور والأوصياء الدخول إلى CHH.",
      highlights: [
        "لا دخول للأهل إلى CHH",
        "يلزم رابط مدرسي",
        "الميزات بحسب المدرسة",
      ],
      sections: [
        {
          title: "اربط عبر إجراء المدرسة",
          text: "توفر المدرسة طريقة الربط أو الرمز المعتمد. أكمل الربط في Family Hero Hub وتأكد من معلومات الطفل والمدرسة المعروضة هناك.",
        },
        {
          title: "اعرض المعلومات المفعلة في FHH",
          text: "قد تتيح المدرسة المرتبطة الواجبات والتنبيهات والتحديثات والصور المحمية ونقاط المدرسة والتقويم والاستبيانات ومحادثات المدرسة.",
        },
        {
          title: "تقرر المدرسة ما يتوفر",
          text: "تعتمد المعلومات الظاهرة على ميزات المدرسة المفعلة والرابط النشط للطفل والسجلات الحالية. ولا تستخدم كل مدرسة جميع الميزات.",
        },
        {
          title: "تبقى معلومات المدرسة والمنزل منفصلة",
          text: "تبقى نقاط الأسرة ومكافآتها وروتينها وإعداداتها المنزلية في FHH، ولا تُشارك مع المدرسة لمجرد وجود رابط.",
        },
        {
          title: "استخدم مسار الدعم الصحيح",
          text: "اسأل المدرسة عن دقة السجلات المدرسية أو توفرها. وتواصل مع دعم Family Hero Hub لأسئلة حساب الأسرة أو المنزل أو الجهاز.",
        },
        {
          title: "إذا كنت موظفا في المدرسة أيضا",
          text: "استخدم CHH فقط لمسؤولياتك الوظيفية المصرح بها وFHH لأسرتك. ويبقى الدوران منفصلين.",
        },
      ],
      notice: {
        title: "لا يوجد تطبيق للأهل باسم كلاس هيرو هب",
        text: "لا تبحث عن تطبيق مستقل للأهل باسم CHH ولا تثبته. تُقدم تجربة الأسرة من خلال Family Hero Hub.",
      },
      cta: {
        heading: "افتح المنتج المخصص للأسرة",
        text: "زر Family Hero Hub للتعرف على مساحة الأسرة والمعلومات المدرسية المرتبطة.",
        label: "زر Family Hero Hub",
        href: "https://familyherohub.com",
        secondaryLabel: "اقرأ عن الربط مع الأسرة",
        secondaryHref: "/family-connection",
      },
    },
    safetyPrivacy: {
      pageTitle: "السلامة والخصوصية والدعم | كلاس هيرو هب",
      metaDescription:
        "تعرف على تقييد CHH بالمدرسة والدور وخصوصية السلوك ومراجعة الحماية المخصصة والوسائط المحمية والتدقيق وحد البيانات مع FHH.",
      eyebrow: "السلامة والخصوصية والدعم",
      heading: "سلطة واضحة لبيانات المدرسة وحدود مقصودة للعمل المحمي.",
      intro:
        "صُممت CHH لمساعدة المدارس على قصر الوصول على الأشخاص والسجلات والمسارات التي تتطلبها أدوارهم الحالية. تصف هذه الصفحة نهج المنتج وليست ضمانا قانونيا أو أمنيا.",
      highlights: [
        "وصول مقيد بالدور",
        "خصوصية ما يحتاج إلى تحسين",
        "مراجعة حماية مخصصة",
      ],
      sections: [
        {
          title: "تقييد المدرسة والجهة والدور",
          text: "تبقى سجلات المدرسة مرتبطة بها. ويعتمد وصول الموظف على العضويات والأدوار والتكليفات النشطة، كما تكون الروابط والمعرفات عبر حدود الأنظمة مبهمة ومقيدة.",
        },
        {
          title: "معلومات سلوك خاصة",
          text: "يمكن تسجيل السلوك الإيجابي وما يحتاج إلى تحسين، لكن لا يُستخدم السلوك السلبي لتصنيفات علنية أو تشهير. ويمكن للتقدير الإيجابي استخدام أدلة شفافة ومراجعة الموظفين.",
        },
        {
          title: "الحماية وضع منفصل",
          text: "يُمنح وصول الحماية صراحة ويُربط بسبب ومدة ويخضع للتدقيق. ولا يصبح المراجع مشاركا ولا يغير الإيصالات أو غير المقروء أو الإشعارات.",
        },
        {
          title: "الرسائل والوسائط المحمية",
          text: "تستخدم النصوص والصور المحمية والرسائل الصوتية مسارات وصول مقيدة بالمدرسة. ويجب التعامل مع الأدلة والوسائط المحمية عبر المسارات المصرح بها فقط.",
        },
        {
          title: "تبقى بيانات الأسرة على جانب الأسرة",
          text: "يستخدم الأهل FHH. ولا تحتاج CHH رموز أجهزة FHH أو معرفات أسرية غير ضرورية، ولا تتصل تطبيقات الأسرة بـ CHH مباشرة.",
        },
        {
          title: "التدقيق والصحة وقابلية النقل",
          text: "تساعد العروض التشغيلية المصرح بها وسجلات التدقيق والصادرات المدعومة المدرسة على فهم حالة الخدمة والاحتفاظ بسجلات مسؤولة.",
        },
        {
          title: "أبلغ عن القلق بأمان",
          text: "عند وجود قلق فوري على سلامة طفل، اتبع إجراءات الحماية والطوارئ في المدرسة أولا. ولمشكلة في المنصة تواصل مع الدعم من دون إرسال أدلة محمية بالبريد.",
        },
        {
          title: "لا ضمان مطلق",
          text: "لا يمكن لأي خدمة إلكترونية أن تضمن الأمان المثالي أو التوفر دون انقطاع. صُممت CHH لتقليل التعرض غير الضروري وحفظ الحدود ودعم الاستجابة المضبوطة.",
        },
      ],
      cta: {
        heading: "هل تحتاج إلى مساعدة في الوصول أو الخصوصية أو سلامة المنتج؟",
        text: "أرسل ملخصا غير حساس. لا ترسل الرسائل الخاصة أو إجابات الاستبيانات أو أدلة الحماية بالبريد.",
        label: "تواصل مع الدعم",
        href: supportEmailHref,
        secondaryLabel: "اقرأ سياسة الخصوصية",
        secondaryHref: "/privacy",
      },
    },
    privacy: {
      pageTitle: "سياسة الخصوصية | كلاس هيرو هب",
      metaDescription:
        "معلومات خصوصية كلاس هيرو هب العامة لحسابات موظفي المدرسة والسجلات والمحتوى المحمي والربط مع Family Hero Hub والاحتفاظ والطلبات والدعم.",
      eyebrow: "معلومات قانونية",
      heading: "سياسة الخصوصية",
      intro:
        "آخر تحديث: ٢ أغسطس ٢٠٢٦. توضح هذه السياسة المعلومات التي تستخدمها CHH لتقديم خدمتها المدرسية والخيارات المتاحة للمدارس والمستخدمين.",
      sections: [
        {
          title: "١. النطاق والأدوار",
          text: "CHH مخصصة للمدارس والمستخدمين المدرسيين المصرح لهم. تتحكم المدرسة المشاركة في سجلات المدرسة والأغراض والأشخاص الذين تضعهم في الخدمة. ويجب تأكيد أدوار المتحكم والمعالج القانونية بدقة في اتفاق المدرسة والولاية القضائية المعمول بها.",
        },
        {
          title: "٢. المعلومات التي تستخدمها CHH",
          text: "قد تعالج CHH بيانات حسابات الموظفين المصرح لهم، وهياكل المدارس والفروع والسنوات، وتكليفات الموظفين، وسجلات الطلاب وأولياء الأمور، والاستيراد والتصدير، ومعلومات السلوك والواجبات والمفكرة والتنبيهات والتحديثات والتقويم والاستبيانات والرسائل والتقارير، والوسائط المحمية، وسجلات الحماية، والمعلومات التقنية ومعلومات الجلسة والتدقيق والتشغيل اللازمة لتشغيل الخدمة وحمايتها.",
        },
        {
          title: "٣. كيفية استخدام المعلومات",
          text: "تُستخدم المعلومات للتحقق من المستخدمين وتطبيق نطاق المدرسة والدور وتقديم المسارات المفعلة وإيصال معلومات المدرسة المرتبطة عبر FHH وحفظ السجلات والتاريخ ودعم التقارير والصادرات المصرح بها وحماية الخدمة والتحقيق في المشكلات التشغيلية والاستجابة للدعم أو الالتزامات القانونية.",
        },
        {
          title: "٤. الطلاب وأولياء الأمور ووصول الأسرة",
          text: "لا يحصل الطلاب أو أولياء الأمور على حسابات موظفين في CHH لمجرد تخزين المدرسة لسجلاتهم. يعرض الأهل المعلومات المفعلة عبر FHH بعد رابط مدرسي نشط، ولا تتصل تطبيقات الأسرة بـ CHH مباشرة.",
        },
        {
          title: "٥. حد البيانات بين CHH وFHH",
          text: "تبقى CHH مرجع سجلات المدرسة. ويملك FHH هوية الأسرة وولي الأمر والطفل والمنزل والجهاز ويصل إلى معلومات المدرسة المحمية عبر وسيطه في الخادم. ولا تحتاج CHH رموز أجهزة FHH أو معرفات أسرية غير ضرورية.",
        },
        {
          title: "٦. المشاركة ومقدمو الخدمة",
          text: "قد يتعامل مع المعلومات مقدمو الخدمات المستخدمون لاستضافة الخدمة وتشغيلها وتأمينها وتسليمها ودعمها، وFHH فقط لمسارات المدرسة المرتبطة المذكورة. لا تجعل CHH سجلات المدرسة عامة، ويجب أن تتبع أي إفصاحات أخرى اتفاق المدرسة أو المتطلب القانوني.",
        },
        {
          title: "٧. الاحتفاظ والسجلات",
          text: "تُحفظ معلومات المدرسة ما دامت لازمة للخدمة أو حفظ سجلات المدرسة أو التدقيق أو الأمن أو الدعم أو الحماية أو الالتزامات القانونية. بعض السجلات تاريخية أو غير قابلة للاستبدال بطبيعتها. وقد تبقى المعلومات المحذوفة في نسخ احتياطية محمية حتى اكتمال دورة التدوير المعتادة.",
        },
        {
          title: "٨. الأمان والوصول",
          text: "تستخدم CHH تقييد المدرسة والدور والجلسات المضبوطة ومعرفات التكامل المبهمة وسجلات التدقيق والمسارات المحمية لتقليل التعرض غير الضروري. ولا يمكن لأي خدمة إلكترونية أن تضمن أمانا مثاليا.",
        },
        {
          title: "٩. الطلبات والتصحيحات",
          text: "يُقدم طلب سجل الطالب أو المدرسة عادة إلى المدرسة التي تتحكم فيه. ويمكن للمستخدمين المدرسيين المصرح لهم تصحيح السجلات أو استخدام الصادرات المدعومة بحسب صلاحياتهم. ويمكن إرسال أسئلة حساب المنصة وتوجيه الطلب إلى دعم CHH.",
        },
        {
          title: "١٠. التغييرات والتواصل",
          text: "قد تُحدث هذه السياسة مع تطور الخدمة واتفاقات المدارس والمتطلبات القانونية. وتتطلب الصياغة الجوهرية والالتزامات الخاصة بالولاية مراجعة قبل الإطلاق التجاري العام. تواصل مع support@classherohub.com من دون تضمين بيانات مدرسية حساسة.",
        },
      ],
      notice: {
        title: "تلزم مراجعة قانونية",
        text: "يجب على Dom والمستشار القانوني المناسب تأكيد أدوار المتحكم والمعالج والولاية وفترات الاحتفاظ والإفصاح عن المعالجين الفرعيين وصياغة نقل البيانات عبر الحدود والحقوق النظامية قبل الاستخدام التجاري العام.",
      },
      cta: {
        heading: "هل تحتاج إلى المسار الصحيح لسؤال خصوصية أو بيانات؟",
        text: "ابدأ بالمدرسة للسجلات المدرسية، أو بدعم CHH لأسئلة حساب المنصة وتوجيه الطلب.",
        label: "طلبات البيانات والحساب",
        href: "/data-requests",
        secondaryLabel: "تواصل مع الدعم",
        secondaryHref: supportEmailHref,
      },
    },
    terms: {
      pageTitle: "شروط الخدمة | كلاس هيرو هب",
      metaDescription:
        "شروط المرحلة التجريبية للاستخدام المدرسي المصرح به لكلاس هيرو هب، بما في ذلك حدود الأدوار والاستخدام المقبول ومسؤوليات المدرسة وحدود الخدمة.",
      eyebrow: "معلومات قانونية",
      heading: "شروط الخدمة",
      intro:
        "آخر تحديث: ٢ أغسطس ٢٠٢٦. تصف هذه الشروط العامة الظروف المقصودة للعرض والاستخدام التجريبي. وتسود اتفاقية المدرسة الموقعة عند انطباقها.",
      sections: [
        {
          title: "١. غرض الخدمة",
          text: "CHH منتج مدرسي للإدارة والتدريس والتواصل ومشاركة الأسرة والتقارير والمراجعة المحمية للمستخدمين المصرح لهم. وليست خدمة طوارئ أو بديلا للحكم المهني في الحماية أو تطبيقا للأهل.",
        },
        {
          title: "٢. المستخدمون والأدوار المصرح بها",
          text: "يجب على المستخدم الوصول إلى CHH فقط عبر حساب ودور مدرسي مصرح بهما. والمدارس مسؤولة عن تعيين أدوار الموظفين وتكليفات الصف والصلاحيات المتخصصة ومراجعتها.",
        },
        {
          title: "٣. مسؤولية المدرسة",
          text: "المدرسة مسؤولة عن دقة السجلات ومشروعيتها وملاءمتها، والجماهير والاتصالات والسياسات والتعليمات التي تضعها في CHH، وتحديد الميزات المفعلة لمجتمعها.",
        },
        {
          title: "٤. أولياء الأمور وFamily Hero Hub",
          text: "لا يستخدم أولياء الأمور والأوصياء CHH مباشرة. وقد يرون المعلومات المفعلة عبر FHH بعد رابط مدرسي نشط. ولا يمنح دور الموظف وصولا للأسرة ولا يمنح وصول الأسرة صلاحيات الموظف.",
        },
        {
          title: "٥. الاستخدام المقبول",
          text: "لا تحاول الوصول غير المصرح به أو تجاوز نطاق المدرسة أو الدور أو مشاركة بيانات الدخول أو التدخل في الأمان أو رفع محتوى غير قانوني أو ضار أو إساءة استخدام المعلومات المحمية أو استخدام المنتج لتصنيف السلوك السلبي أو التشهير به علنا.",
        },
        {
          title: "٦. الحماية والطوارئ",
          text: "تبقى المدارس مسؤولة عن قرارات الحماية والإجراءات الإلزامية والاستجابة للطوارئ. يدعم مسار الحماية في CHH المراجعة المضبوطة لكنه لا يحل محل سياسة المدرسة أو المختصين أو خدمات الطوارئ.",
        },
        {
          title: "٧. الاستيراد والتصدير والتكامل",
          text: "المدارس مسؤولة عن التحقق من الاستيراد المرحلي والصادرات المصرح بها ونتائج التكامل. ويقتصر تكامل FHH على مسارات المدرسة المرتبطة ولا يدمج سلطات الهوية في المنتجين.",
        },
        {
          title: "٨. التوفر والتغيير التجريبي",
          text: "قد يكون وصول العرض أو التجربة محدودا أو يتغير أو يعلق أو ينتهي أثناء تقييم المنتج وتحسينه. ويُتفق مع المدرسة المشاركة على الميزات المفعلة وترتيبات الدعم.",
        },
        {
          title: "٩. حدود الخدمة",
          text: "تُقدم CHH كأداة لمسارات المدرسة. ولا يمكن ضمان استمرارها دون انقطاع أو خلوها من الأخطاء أو ملاءمتها لكل حالة. وتبقى المدرسة مسؤولة عن الاستمرارية التشغيلية والقرارات المهنية.",
        },
        {
          title: "١٠. الشروط التجارية والولاية",
          text: "لا تحدد هذه الصفحة الأسعار أو شروط الدفع أو القانون الحاكم أو حدود المسؤولية أو مستويات الخدمة أو شروط حماية البيانات أو الإنهاء، ويجب الاتفاق عليها في عقد المدرسة قبل الاستخدام التجاري.",
        },
        {
          title: "١١. التواصل",
          text: "تواصل مع support@classherohub.com بملخص غير حساس لأي سؤال عن هذه الشروط أو الوصول التجريبي.",
        },
      ],
      notice: {
        title: "تلزم مراجعة قانونية",
        text: "تتطلب هذه الشروط التجريبية مراجعة Dom ومستشار قانوني قبل الإطلاق التجاري العام. ولا تخترع قانونا حاكما أو أسعارا أو مستويات خدمة أو شروط مسؤولية.",
      },
      cta: {
        heading: "هل لديك سؤال عن شروط التجربة؟",
        text: "تواصل مع الفريق قبل إدخال بيانات مدرسية حقيقية أو الاعتماد على مسار خارج النطاق المتفق عليه.",
        label: "تواصل مع الدعم",
        href: supportEmailHref,
        secondaryLabel: "اقرأ سياسة الخصوصية",
        secondaryHref: "/privacy",
      },
    },
    dataRequests: {
      pageTitle: "طلبات البيانات والحساب | كلاس هيرو هب",
      metaDescription:
        "اعثر على المسار الصحيح لطلبات سجلات المدرسة وحساب الموظف والوصول والتصحيح والتصدير والحذف في CHH.",
      eyebrow: "طلبات البيانات والحساب",
      heading: "ابدأ بالجهة التي تتحكم في السجل.",
      intro:
        "لسجلات المدرسة وحسابات موظفي CHH وحسابات أسر FHH سلطات مختلفة. يساعد المسار الصحيح على حماية الهوية وتجنب كشف معلومات حساسة في البريد.",
      highlights: [
        "السجل المدرسي ← المدرسة",
        "حساب CHH ← مسؤول المدرسة أو دعم CHH",
        "حساب أسرة FHH ← دعم FHH",
      ],
      sections: [
        {
          title: "طلبات سجلات الطلاب أو أولياء الأمور أو المدرسة",
          text: "تواصل مع المدرسة التي أنشأت السجل أو تديره. فهي الأقدر عادة على التحقق من الهوية وتصحيح معلومات المدرسة وتحديد كيفية معالجة الطلب.",
        },
        {
          title: "حساب موظف CHH أو الوصول",
          text: "اطلب من مسؤول المدرسة مراجعة دورك الوظيفي أو تكليفك أو عضويتك. وتواصل مع دعم CHH إذا أكدت المدرسة صحة الدور واستمر تعذر الوصول.",
        },
        {
          title: "الصادرات وقابلية النقل",
          text: "يمكن للأدوار المدرسية المصرح لها استخدام الصادرات المدعومة للسجلات والتقارير المتاحة. ويمكن للمدرسة التواصل مع دعم CHH لتحديد مسار التصدير المناسب.",
        },
        {
          title: "التصحيح أو التقييد أو الحذف",
          text: "قد تخضع السجلات المدرسية لمتطلبات التاريخ أو التدقيق أو الحماية أو الحجز القانوني أو النسخ الاحتياطية. وتقيم المدرسة والخدمة الطلب بحسب السلطة والاتفاق المعمول به؛ فالحذف ليس دائما الإجراء الصحيح أو الفوري.",
        },
        {
          title: "حسابات Family Hero Hub",
          text: "يملك FHH هوية الأسرة والمنزل والجهاز. استخدم دعم Family Hero Hub لطلبات حساب الأسرة أو مقدم الرعاية أو لوحة الطفل أو الجهاز المرتبط. ولا ينقل الرابط المدرسي هذه الهوية إلى CHH.",
        },
        {
          title: "ما ينبغي تضمينه",
          text: "قدم اسمك ومدرستك ودورك وعنوان تواصل آمنا ونوع الطلب. لا ترسل كلمات مرور أو رموزا أو مجموعات بيانات كاملة للطلاب أو رسائل خاصة أو إجابات استبيانات أو أدلة حماية بالبريد.",
        },
      ],
      notice: {
        title: "قد يلزم التحقق من الهوية",
        text: "قد يطلب الدعم من المدرسة أو صاحب الطلب التحقق من السلطة قبل كشف المعلومات المحمية أو تغييرها أو تصديرها.",
      },
      cta: {
        heading: "ألست متأكدا من المسار الصحيح؟",
        text: "أرسل ملخصا محدودا وغير حساس وسنساعدك على تحديد الخطوة التالية.",
        label: "راسل دعم CHH",
        href: supportEmailHref,
        secondaryLabel: "اقرأ سياسة الخصوصية",
        secondaryHref: "/privacy",
      },
    },
  },
};

export function getPublicSiteCopy(
  value: string | null | undefined,
): PublicSiteCopy {
  return value === "ar" ? ar : en;
}

export function publicLocale(
  value: string | null | undefined,
): SupportedLocale {
  return value === "ar" ? "ar" : "en";
}
