import type { SupportedLocale } from "$lib/i18n";

export type PublicSection = {
  title: string;
  text: string;
  bullets?: string[];
};

export type PilotFormCopy = {
  heading: string;
  intro: string;
  nameLabel: string;
  schoolLabel: string;
  roleLabel: string;
  regionLabel: string;
  emailLabel: string;
  messageLabel: string;
  messageHint: string;
  submitLabel: string;
  submittingLabel: string;
  successHeading: string;
  successText: string;
  rateLimitError: string;
  unavailableError: string;
  generalError: string;
  directHeading: string;
  directText: string;
  directLabel: string;
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
  form?: PilotFormCopy;
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

type ProductVisual = {
  src: string;
  alt: string;
  height: number;
  eyebrow: string;
  title: string;
  text: string;
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
    featureEyebrow: string;
    featureHeading: string;
    featureIntro: string;
    featureGroups: Array<{ title: string; text: string; items: string[] }>;
    proofEyebrow: string;
    proofHeading: string;
    proofIntro: string;
    proofDataNote: string;
    proofItems: ProductVisual[];
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
      "A practical workspace for teachers, school communication and family updates that can complement the systems the school already uses.",
  },
  {
    question: "Who uses Class Hero Hub?",
    answer:
      "School staff use Class Hero Hub. Each person sees only the schools, classes and tools they need for their job.",
  },
  {
    question: "Do parents sign in to Class Hero Hub?",
    answer:
      "No. Parents and guardians see the school information shared with them through Family Hero Hub. There is no separate Class Hero Hub parent app.",
  },
  {
    question: "What can families see in Family Hero Hub?",
    answer:
      "Depending on what the school uses, families may see homework, notices, updates, school points, calendar items, surveys and School Chats for their linked child.",
  },
  {
    question: "How does Class Hero Hub fit with our existing systems?",
    answer:
      "Class Hero Hub is designed to work alongside the systems a school already uses. It focuses on everyday teaching, communication, follow-up and family updates; school teams can use checked CSV files for supported student and staff setup.",
  },
  {
    question: "Does Class Hero Hub support English and Arabic?",
    answer:
      "Yes. The website and staff experience support English and Arabic, including right-to-left layouts. Names and school-written content stay exactly as the school enters them.",
  },
  {
    question: "Can staff communicate with families?",
    answer:
      "Schools can share notices, updates, homework, calendar information and School Chats. Available features and who may use them are set for each school.",
  },
  {
    question: "How does behaviour and recognition work?",
    answer:
      "Staff can record positive and needs-work behaviour from the relevant class or student record. Needs-work information stays private, while positive recognition can celebrate effort without turning children into a public ranking.",
  },
  {
    question: "How are safeguarding concerns handled?",
    answer:
      "Safeguarding concerns are reviewed in a restricted area where authorised staff can see what changed and when. This stays separate from ordinary School Chats.",
  },
  {
    question: "How can our school try Class Hero Hub?",
    answer:
      "Request a conversation and tell us what you would most like to improve. We can show the parts of Class Hero Hub that could help and discuss a focused pilot.",
  },
];

const arabicFaq: FaqItem[] = [
  {
    question: "ما كلاس هيرو هب؟",
    answer:
      "مساحة عملية للمعلمين والتواصل المدرسي وتحديثات الأسرة، تكمل الأنظمة التي تستخدمها المدرسة بالفعل.",
  },
  {
    question: "من يستخدم كلاس هيرو هب؟",
    answer:
      "يستخدم موظفو المدرسة كلاس هيرو هب، ويرى كل شخص فقط المدارس والصفوف والأدوات التي يحتاجها في عمله.",
  },
  {
    question: "هل يسجل أولياء الأمور الدخول إلى كلاس هيرو هب؟",
    answer:
      "لا. يرى أولياء الأمور والأوصياء المعلومات التي تشاركها المدرسة معهم عبر Family Hero Hub. ولا يوجد تطبيق منفصل لأولياء الأمور باسم كلاس هيرو هب.",
  },
  {
    question: "ما الذي يمكن أن تراه الأسرة في Family Hero Hub؟",
    answer:
      "بحسب ما تستخدمه المدرسة، قد ترى الأسرة الواجبات والتنبيهات والتحديثات ونقاط المدرسة وعناصر التقويم والاستبيانات ومحادثات المدرسة الخاصة بالطفل المرتبط.",
  },
  {
    question: "كيف يعمل كلاس هيرو هب إلى جانب أنظمة المدرسة الحالية؟",
    answer:
      "صُمم كلاس هيرو هب ليكمل الأنظمة التي تستخدمها المدرسة. يركز على عمل المعلم اليومي والتواصل والمتابعة وتحديثات الأسرة، ويمكن لفرق المدرسة استخدام ملفات CSV لإعداد بيانات الطلبة والموظفين المدعومة بعد مراجعتها.",
  },
  {
    question: "هل يدعم كلاس هيرو هب العربية والإنجليزية؟",
    answer:
      "نعم. يدعم الموقع وتجربة الموظفين العربية والإنجليزية، بما في ذلك العرض من اليمين إلى اليسار. وتبقى الأسماء والمحتويات التي تكتبها المدرسة كما أدخلتها تماماً.",
  },
  {
    question: "هل يمكن للموظفين التواصل مع الأسر؟",
    answer:
      "يمكن للمدرسة مشاركة التنبيهات والتحديثات والواجبات ومعلومات التقويم ومحادثات المدرسة. وتُحدد الميزات المتاحة ومن يستخدمها بحسب احتياجات كل مدرسة.",
  },
  {
    question: "كيف يعمل تسجيل السلوك والتقدير؟",
    answer:
      "يمكن للموظفين تسجيل السلوك الإيجابي والسلوك الذي يحتاج إلى تحسين من سجل الصف أو الطالب المعني. تبقى ملاحظات التحسين خاصة، بينما يتيح التقدير الإيجابي الاحتفاء بالجهد من دون تحويل الأطفال إلى ترتيب علني.",
  },
  {
    question: "كيف تُعالج مخاوف حماية الطلبة؟",
    answer:
      "تُراجع مخاوف حماية الطلبة في مساحة مخصصة تتيح للموظفين المخولين معرفة ما تغير ومتى. وتبقى هذه المراجعة منفصلة عن محادثات المدرسة العادية.",
  },
  {
    question: "كيف يمكن لمدرستنا تجربة كلاس هيرو هب؟",
    answer:
      "اطلبوا محادثة وأخبرونا بما ترغبون في تحسينه أولاً. سنعرض الأجزاء التي قد تساعدكم من كلاس هيرو هب ونناقش برنامجاً تجريبياً محدداً.",
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
    openMenu: "Open website menu",
    closeMenu: "Close website menu",
  },
  footer: {
    description:
      "Class Hero Hub gives teachers and school teams one place for everyday teaching, communication and updates shared with families.",
    tagline: "Practical tools for the school day.",
    product: "Product",
    support: "Support",
    legal: "Legal",
    home: "Home",
    features: "Product overview",
    howItWorks: "How it works",
    schools: "For schools",
    familyConnection: "Family connection",
    faq: "FAQ",
    requestPilot: "Request a pilot",
    contact: "Contact",
    administratorGuide: "School administrator guide",
    teacherGuide: "Teacher guide",
    familyGuide: "Family guide",
    safetyPrivacy: "Safety, privacy & support",
    privacy: "Privacy Policy",
    terms: "Terms of Service",
    dataRequests: "Data & account requests",
    emailLabel: "Support and pilot enquiries",
  },
  home: {
    pageTitle: "Class Hero Hub | A practical workspace for the school day",
    metaDescription:
      "One place for teachers, school communication and family updates, alongside the systems the school already uses.",
    eyebrow: "Practical tools for the school day.",
    heading: "Help teachers. Keep families informed.",
    intro:
      "Class Hero Hub gives school teams one place for homework, behaviour, recognition, notices, chats, surveys and family updates—alongside the systems your school already uses.",
    primaryCta: "Request a pilot",
    secondaryCta: "Explore the product",
    strapline:
      "For school leaders, administrators and teachers · English and Arabic",
    schoolWorkspaceLabel: "Everyday school work",
    schoolWorkspaceTitle: "Start with your class.",
    schoolWorkspaceText:
      "Open a class, then go straight to homework, notices, behaviour, recognition, calendars or messages.",
    familyDeliveryLabel: "Family updates",
    familyDeliveryTitle: "Share the right update with home.",
    familyDeliveryText:
      "Parents see the school information shared for their child in Family Hero Hub.",
    boundaryLabel: "Alongside existing systems",
    boundaryText:
      "Keep your current core systems and use Class Hero Hub for teachers, communication and family updates.",
    benefitsEyebrow: "Everyday tools for staff",
    benefitsHeading: "The tools teachers use most are easy to find.",
    benefitsIntro:
      "Teachers and school teams can start with the task at hand and pick up where they left off.",
    benefits: [
      {
        title: "Teach from the class in front of you",
        text: "Open an assigned class and move directly to students, homework, diary items, behaviour or recognition.",
      },
      {
        title: "Share clear school updates",
        text: "Publish notices, updates, calendar items and school photos from one staff workspace.",
      },
      {
        title: "Recognise and follow up",
        text: "Celebrate positive effort, keep needs-work behaviour private and return when follow-up is needed.",
      },
      {
        title: "Hear from families",
        text: "Use School Chats, surveys and polls to keep useful school-to-home communication moving.",
      },
    ],
    featureEyebrow: "Visibility and supporting setup",
    featureHeading: "Clear information for leaders. Simple setup for teams.",
    featureIntro:
      "Reports show what happened and where follow-up may be needed. School setup keeps staff and classes up to date.",
    featureGroups: [
      {
        title: "See where follow-up is needed",
        text: "Leaders can review school activity, see what changed and decide what to discuss or follow up.",
        items: [
          "Reports and behaviour trends",
          "See whether messages have arrived and been read",
          "See what changed and when",
          "A dedicated safeguarding review area",
        ],
      },
      {
        title: "Support the work around existing systems",
        text: "School administrators can prepare the Class Hero Hub workspace while the school keeps its current core systems in place.",
        items: [
          "Academic years, grades, classes and subjects",
          "Staff assignments and student rosters",
          "Checked CSV imports and annual updates",
          "Supported record exports",
        ],
      },
    ],
    proofEyebrow: "Inside Class Hero Hub",
    proofHeading: "See the product at work.",
    proofIntro:
      "These are real Class Hero Hub screens, shown with demonstration data created for this website.",
    proofDataNote: "Demonstration school and staff data only.",
    proofItems: [
      {
        src: "/product/teacher-workflow.png",
        alt: "Class Hero Hub teacher screen showing demonstration classes",
        height: 650,
        eyebrow: "Teacher workspace",
        title: "Classes and common tools stay in reach",
        text: "Teachers can begin with their assigned classes and move to students, notices and the calendar without hunting through menus.",
      },
      {
        src: "/product/school-overview.png",
        alt: "Class Hero Hub school setup screen for a demonstration school",
        height: 900,
        eyebrow: "Supporting setup",
        title: "A clear view of what is ready",
        text: "Administrators can see what is ready, what still needs attention and pick up where they left off.",
      },
    ],
    familyEyebrow: "Class Hero Hub + Family Hero Hub",
    familyHeading: "School updates for families.",
    familyIntro:
      "Staff use Class Hero Hub for school work and communication. Parents see the school updates shared with them in Family Hero Hub.",
    schoolSideTitle: "1 · Staff work in Class Hero Hub",
    schoolSideText:
      "Staff manage homework, notices, messages and other school updates.",
    connectionTitle: "2 · The school shares an update",
    connectionText:
      "When staff share a family update, parents can see it for their child.",
    familySideTitle: "3 · Parents see it in Family Hero Hub",
    familySideText:
      "Homework, notices, calendar items, school points, surveys or chats appear alongside the family’s own tools.",
    familyBoundary:
      "Parents do not need another school app or a staff login. Their school view stays in Family Hero Hub.",
    familyCta: "See the family connection",
    trustEyebrow: "Trust in everyday use",
    trustHeading: "Simple safeguards for everyday school work.",
    trustIntro:
      "Staff see only the information and tools they need. Sensitive records stay private, and schools can check what changed and when.",
    trustItems: [
      {
        title: "Clear access for staff",
        text: "Staff see the schools, classes, students and tools they need for their work.",
      },
      {
        title: "Private behaviour records",
        text: "Needs-work behaviour is not turned into public rankings or student-shaming features.",
      },
      {
        title: "A separate safeguarding area",
        text: "Safeguarding review is kept apart from ordinary conversations and everyday messaging activity.",
      },
    ],
    bilingualEyebrow: "English + العربية",
    bilingualHeading: "Ready for bilingual school communities.",
    bilingualText:
      "Staff can use Class Hero Hub in English or Arabic, with right-to-left layouts throughout the Arabic experience.",
    bilingualPoint1:
      "Changing the interface language does not alter names or content entered by the school.",
    bilingualPoint2:
      "Responsive layouts support staff working across phones, tablets and desktops.",
    faqEyebrow: "Questions schools ask",
    faqHeading: "Answers to common school questions.",
    faqIntro:
      "Learn who uses Class Hero Hub, how families receive updates and what a pilot can look like.",
    faqCta: "Read all questions",
    finalHeading: "Could Class Hero Hub make your school day easier?",
    finalText:
      "Tell us what takes too much time or leaves families unsure. We will show you the parts of Class Hero Hub that could help.",
    finalPrimary: "Request a pilot",
    finalSecondary: "Contact the team",
  },
  faq: {
    pageTitle: "Frequently asked questions | Class Hero Hub",
    metaDescription:
      "Answers about Class Hero Hub, school use, family updates, languages and pilot conversations.",
    eyebrow: "Frequently asked questions",
    heading: "The practical questions schools ask first.",
    intro:
      "A straightforward introduction to the product, who it is for and how it connects school staff with families.",
    items: englishFaq,
    ctaHeading: "Have a question about your school?",
    ctaText:
      "Tell us what you are trying to improve and we will point you to the most useful answer or demonstration.",
    ctaLabel: "Contact the team",
  },
  pages: {
    howItWorks: {
      pageTitle: "How Class Hero Hub works",
      metaDescription:
        "See how teachers and school teams move from everyday work to family updates, follow-up and supporting setup.",
      eyebrow: "How it works",
      heading: "Start with the work that needs doing today.",
      intro:
        "Teachers and school teams start with the class, message or follow-up in front of them. Family updates they share appear in Family Hero Hub.",
      highlights: [
        "Work from the class",
        "Keep communication moving",
        "Share with families",
      ],
      sections: [
        {
          title: "Start with your class",
          text: "Teachers begin with their assigned classes and move directly to students, homework, notices, behaviour, recognition, calendars or messages.",
          bullets: [
            "Keep common tools close to each class",
            "Pick up where you left off",
          ],
        },
        {
          title: "Share updates with families",
          text: "When the school shares family-facing information, parents see it in Family Hero Hub for their linked child. The school team continues to work in Class Hero Hub.",
          bullets: [
            "Parents keep using Family Hero Hub",
            "Schools decide which features to introduce",
          ],
        },
        {
          title: "Prepare the supporting workspace",
          text: "Administrators set up staff, students, academic years, classes and subjects. Supported student and staff details can be entered manually or prepared through checked CSV files.",
        },
      ],
      cta: {
        heading: "See how it could work at your school.",
        text: "A short demonstration can cover the daily tasks and family communication that matter most to your team.",
        label: "Request a demonstration",
        href: "/pilot",
        secondaryLabel: "Explore the product",
        secondaryHref: "/features",
      },
    },
    features: {
      pageTitle: "Class Hero Hub product overview",
      metaDescription:
        "Explore everyday teaching, school communication, family updates, follow-up and supporting setup in Class Hero Hub.",
      eyebrow: "Product overview",
      heading: "Practical tools for work that repeats every school day.",
      intro:
        "Teachers can find common tools by class or student. Class Hero Hub works alongside the school’s existing systems.",
      highlights: [
        "Everyday teaching",
        "School communication",
        "Family updates",
        "Reports and follow-up",
      ],
      sections: [
        {
          title: "Everyday teaching tools",
          text: "Help teachers move quickly between their classes and the work they do most often.",
          bullets: [
            "Homework, diary items and required items",
            "Private behaviour records and positive recognition",
            "Notices, updates, calendars and photos",
          ],
        },
        {
          title: "School communication",
          text: "Send class or student messages, see whether they have arrived and been read, and set school contact hours.",
          bullets: [
            "School Chats with text, photos and voice notes",
            "Notices, surveys and polls",
            "Family updates in Family Hero Hub",
          ],
        },
        {
          title: "Insight for better follow-up",
          text: "Use reports and trends to see what happened, recognise progress and decide what needs attention.",
          bullets: [
            "Behaviour and engagement trends",
            "Message status and school activity checks",
            "A dedicated safeguarding review area",
          ],
        },
        {
          title: "Supporting school setup",
          text: "Set up academic years, classes, subjects, staff assignments and student rosters while keeping existing core systems in place.",
          bullets: [
            "Checked CSV imports for supported student and staff details",
            "Annual record updates",
            "Supported record exports",
          ],
        },
      ],
      cta: {
        heading: "Which part would make the biggest difference first?",
        text: "We can shape a demonstration around one real school problem rather than asking you to sit through every feature.",
        label: "Request a pilot",
        href: "/pilot",
        secondaryLabel: "How it works",
        secondaryHref: "/how-it-works",
      },
    },
    schools: {
      pageTitle: "Class Hero Hub for schools",
      metaDescription:
        "A practical school workspace for leaders, administrators, teachers and bilingual communities.",
      eyebrow: "For schools",
      heading:
        "A practical workspace for the people who keep the school day moving.",
      intro:
        "Class Hero Hub gives teachers and school teams one place for daily tasks, communication and family updates, alongside existing school systems.",
      highlights: [
        "Teachers",
        "School teams",
        "School leaders",
        "Bilingual teams",
      ],
      sections: [
        {
          title: "For teachers",
          text: "Begin with assigned classes and keep common actions nearby, so recording, communicating and following up takes less time.",
        },
        {
          title: "For the wider school team",
          text: "Publish notices and updates, manage calendars, use School Chats and surveys, and see what needs follow-up.",
        },
        {
          title: "For school leaders and administrators",
          text: "Review communication, behaviour, recognition and engagement, then keep staff, class and student details up to date.",
        },
        {
          title: "For English and Arabic communities",
          text: "Use the interface in English or Arabic while keeping the school’s own names and written content exactly as entered.",
        },
      ],
      cta: {
        heading: "Tell us which parts of the school day take too much time.",
        text: "We will focus on the teachers, teams and school tasks that need the most help.",
        label: "Start a conversation",
        href: "/pilot",
        secondaryLabel: "Read the FAQ",
        secondaryHref: "/faq",
      },
    },
    familyConnection: {
      pageTitle: "Class Hero Hub and Family Hero Hub",
      metaDescription:
        "See how school staff use Class Hero Hub while parents receive school updates in Family Hero Hub.",
      eyebrow: "The family connection",
      heading: "School updates for families.",
      intro:
        "Staff use Class Hero Hub for school work and communication. Parents see the school updates shared with them in Family Hero Hub.",
      highlights: [
        "One place for staff",
        "Family Hero Hub for parents",
        "Clear school updates",
      ],
      sections: [
        {
          title: "The school works in Class Hero Hub",
          text: "Staff manage homework, notices, chats and other school updates in Class Hero Hub.",
        },
        {
          title: "Parents see school information in Family Hero Hub",
          text: "For a linked child, this may include homework, notices, updates, school points, calendar items, surveys and School Chats, depending on what the school uses.",
        },
        {
          title: "Families have one familiar place to look",
          text: "Parents do not sign in to Class Hero Hub. Their school information appears alongside their family tools in Family Hero Hub, with the school remaining the right first contact for school-record questions.",
        },
      ],
      cta: {
        heading: "Need to explain this to families?",
        text: "We can help your team explain what staff use and where parents see school updates.",
        label: "Talk to the team",
        href: "/contact",
        secondaryLabel: "Open the family guide",
        secondaryHref: "/guides/families",
      },
    },
    pilot: {
      pageTitle: "Request a Class Hero Hub pilot",
      metaDescription:
        "Tell us about your school and arrange a relevant Class Hero Hub demonstration or pilot conversation.",
      eyebrow: "Request a pilot",
      heading: "Let’s start with a conversation about your school.",
      intro:
        "Tell us what is working, what takes too much effort and what you would like to improve. We will keep the conversation focused.",
      highlights: [
        "A focused conversation",
        "A relevant demonstration",
        "A practical pilot",
      ],
      sections: [
        {
          title: "We learn about your school",
          text: "We ask about your current systems and the school work you would most like to improve.",
        },
        {
          title: "We show what matters",
          text: "Your demonstration focuses on the parts of Class Hero Hub that are relevant to your team and priorities.",
        },
        {
          title: "We agree what comes next",
          text: "If Class Hero Hub looks useful, we agree a manageable pilot with the school staff involved.",
        },
      ],
      form: {
        heading: "Tell us about your school",
        intro: "A few details will help us make the first conversation useful.",
        nameLabel: "Your name",
        schoolLabel: "School",
        roleLabel: "Your role",
        regionLabel: "Country or region",
        emailLabel: "Work email",
        messageLabel: "What would you like to improve?",
        messageHint:
          "A short overview is perfect. Please do not include confidential student information.",
        submitLabel: "Send pilot enquiry",
        submittingLabel: "Sending enquiry…",
        successHeading: "Thank you — your enquiry has been sent.",
        successText:
          "We will read it and get back to you at the email address provided.",
        rateLimitError:
          "We have received several enquiries from this connection. Please wait a little and try again.",
        unavailableError:
          "Email delivery is temporarily unavailable. Please use the direct email option below.",
        generalError:
          "We could not send your enquiry just now. Please try again or email us directly.",
        directHeading: "Prefer email?",
        directText:
          "You can contact the team directly at support@classherohub.com.",
        directLabel: "Email the team",
      },
      cta: {
        heading: "Would you rather begin by email?",
        text: "Send a short note about your school and the area you would like to discuss.",
        label: "Email the team",
        href: pilotEmailHref,
        secondaryLabel: "Explore the product",
        secondaryHref: "/features",
      },
    },
    contact: {
      pageTitle: "Contact Class Hero Hub",
      metaDescription:
        "Contact Class Hero Hub about product demonstrations, pilots, school support or privacy questions.",
      eyebrow: "Contact",
      heading: "How can we help?",
      intro:
        "Whether you are exploring the product or already using Class Hero Hub, send us a short note and we will get it to the right person.",
      highlights: ["Pilot enquiries", "School support", "Family guidance"],
      sections: [
        {
          title: "Product and pilot conversations",
          text: "Tell us about your school, your role and the task you would most like to improve.",
        },
        {
          title: "Support for an existing school",
          text: "Include your school name, your role and a short description of the issue. Screenshots are helpful when they do not contain private school information.",
        },
        {
          title: "Questions from families",
          text: "For a question about school information, contact the school first. For help with the Family Hero Hub account or family experience, use Family Hero Hub support.",
        },
        {
          title: "Privacy and data questions",
          text: "Use the data-request guide to find the best starting point for a school record, staff account or family account request.",
        },
      ],
      notice: {
        title: "Support email",
        text: "Email support@classherohub.com. Please leave passwords, sign-in links and confidential student information out of the message.",
      },
      cta: {
        heading: "Send us a short note.",
        text: "We will reply with the right support option without asking for sensitive information by email.",
        label: "Email Class Hero Hub",
        href: supportEmailHref,
        secondaryLabel: "Read the FAQ",
        secondaryHref: "/faq",
      },
    },
    administratorGuide: {
      pageTitle: "School administrator guide | Class Hero Hub",
      metaDescription:
        "A practical introduction to setting up and maintaining a school in Class Hero Hub.",
      eyebrow: "School administrator guide",
      heading: "Build a school workspace people can rely on.",
      intro:
        "A clear setup makes daily work easier for teachers, students, classes and families.",
      highlights: ["Set up", "Invite", "Review", "Prepare the next year"],
      sections: [
        {
          title: "Start with the academic structure",
          text: "Confirm the school profile, current academic year, campuses, grades, sections, subjects and the terms your school uses.",
        },
        {
          title: "Add staff and students carefully",
          text: "Create staff assignments and bring across student records using checked imports or the school tools provided.",
        },
        {
          title: "Set up the tools your school needs",
          text: "Set up behaviour categories, family features, communication choices and other school settings in a manageable order.",
        },
        {
          title: "Review before sharing",
          text: "Check the audience, class and timing before publishing notices, updates, calendar events or family information.",
        },
        {
          title: "Keep records up to date",
          text: "Correct records promptly, review activity and exports when needed, and prepare the next academic year without losing useful history.",
        },
      ],
      cta: {
        heading: "Need help with a setup decision?",
        text: "Tell us the school area you are working on and what you are trying to achieve.",
        label: "Contact support",
        href: supportEmailHref,
        secondaryLabel: "Teacher guide",
        secondaryHref: "/guides/teacher",
      },
    },
    teacherGuide: {
      pageTitle: "Teacher guide | Class Hero Hub",
      metaDescription:
        "A practical introduction to classes, homework, behaviour, recognition and communication in Class Hero Hub.",
      eyebrow: "Teacher guide",
      heading: "Start with your classes.",
      intro:
        "Class Hero Hub keeps common teaching tasks with the class and students you are already working with.",
      highlights: ["Classes", "Homework", "Recognition", "Communication"],
      sections: [
        {
          title: "Open the class you are working with",
          text: "Your teacher workspace shows assigned home-room classes and subjects, giving you a clear starting point for the day.",
        },
        {
          title: "Record behaviour and recognition",
          text: "Add behaviour information from the relevant class or student and use positive recognition to celebrate genuine effort.",
        },
        {
          title: "Set work and reminders",
          text: "Create homework, diary items, required items and calendar events with dates and instructions families can understand.",
        },
        {
          title: "Share useful updates",
          text: "Use notices, school updates, photos and School Chats for clear, purposeful communication.",
        },
        {
          title: "Ask when something looks wrong",
          text: "If a class, student or tool does not match your assignment, contact the school administrator before working around the issue.",
        },
      ],
      cta: {
        heading: "Need help with a teacher task?",
        text: "Include your school, class and what you were trying to do.",
        label: "Contact support",
        href: supportEmailHref,
        secondaryLabel: "Safety and support",
        secondaryHref: "/safety-privacy",
      },
    },
    familyGuide: {
      pageTitle: "Family guide | Class Hero Hub",
      metaDescription:
        "Learn where parents see school information shared from Class Hero Hub.",
      eyebrow: "Family guide",
      heading: "Parents see school information in Family Hero Hub.",
      intro:
        "If your child’s school uses Class Hero Hub, the school will explain how to connect and which information is available.",
      highlights: [
        "Follow the school’s steps",
        "Use Family Hero Hub",
        "Ask the right support team",
      ],
      sections: [
        {
          title: "Connect through the school",
          text: "Follow the invitation or linking steps provided by your child’s school. Contact the school if a child, class or school record does not look right.",
        },
        {
          title: "View school updates in Family Hero Hub",
          text: "Depending on the school, you may see homework, notices, updates, school points, calendar items, surveys and School Chats for your linked child.",
        },
        {
          title: "Use the right place for help",
          text: "The school is the first contact for school information. Family Hero Hub support can help with your family account and family experience.",
        },
      ],
      cta: {
        heading: "Looking for the family experience?",
        text: "Open Family Hero Hub to use family tools and view school information shared for your child.",
        label: "Open Family Hero Hub",
        href: "https://familyherohub.com/",
        secondaryLabel: "How the connection works",
        secondaryHref: "/family-connection",
      },
    },
    safetyPrivacy: {
      pageTitle: "Safety, privacy and support | Class Hero Hub",
      metaDescription:
        "Plain-language information about access, school records, behaviour, safeguarding, family updates and support in Class Hero Hub.",
      eyebrow: "Safety, privacy and support",
      heading: "Practical safeguards for everyday school work.",
      intro:
        "Class Hero Hub limits access to school information and keeps sensitive work in dedicated areas.",
      highlights: [
        "School-specific records",
        "Private behaviour information",
        "Dedicated safeguarding review",
      ],
      sections: [
        {
          title: "Staff see what they need",
          text: "People sign in as themselves and see only the schools, classes, students and tools they need for their work.",
        },
        {
          title: "School records stay with the right school",
          text: "Schools can see what changed and when for important staff and administration work.",
        },
        {
          title: "Needs-work behaviour stays private",
          text: "Class Hero Hub does not create public negative rankings or student-shaming features. Positive recognition is reviewed by school staff.",
        },
        {
          title: "Safeguarding review is separate",
          text: "Safeguarding staff use a dedicated area that stays separate from ordinary School Chats.",
        },
        {
          title: "Families receive updates through Family Hero Hub",
          text: "Parents see school information shared for their linked child in Family Hero Hub. Questions about the school record should begin with the school.",
        },
      ],
      notice: {
        title: "Report an urgent concern through the correct local route",
        text: "Class Hero Hub support is not an emergency service. Follow your school’s safeguarding policy and contact the appropriate local emergency or child-protection service when someone may be at immediate risk.",
      },
      cta: {
        heading: "Need help with access, privacy or product safety?",
        text: "Send a short, non-sensitive description and we will help you find the right support route.",
        label: "Contact support",
        href: supportEmailHref,
        secondaryLabel: "Read the Privacy Policy",
        secondaryHref: "/privacy",
      },
    },
    privacy: {
      pageTitle: "Privacy Policy | Class Hero Hub",
      metaDescription:
        "The baseline privacy policy for the Class Hero Hub pilot service.",
      eyebrow: "Privacy Policy",
      heading: "Privacy Policy",
      intro:
        "This policy explains, in general terms, how Class Hero Hub uses information while providing the current pilot-stage service to schools.",
      highlights: [
        "Effective 3 August 2026",
        "Pilot-stage service",
        "School and staff information",
        "Questions welcomed",
      ],
      sections: [
        {
          title: "1. What the service is",
          text: "Class Hero Hub is a school workspace used by authorised staff for school organisation, teaching workflows, communication, family updates, reporting and related administration. Schools decide how they use the service under their own policies and agreements.",
        },
        {
          title: "2. Information the service uses",
          text: "This may include school and class information, staff account details, student and guardian records supplied by a school, learning and behaviour information, messages and media, survey responses, sign-in and device information, and records of actions taken in the service.",
        },
        {
          title: "3. Why information is used",
          text: "Information is used to provide requested features, keep accounts and school records working, deliver school information to linked families, support users, maintain service security, investigate problems and meet obligations agreed with participating schools.",
        },
        {
          title: "4. Schools and Class Hero Hub",
          text: "Schools are responsible for the information they provide, the people they authorise and the school policies that apply to their use. Class Hero Hub provides and supports the service in line with the applicable school agreement.",
        },
        {
          title: "5. Necessary service providers",
          text: "Information may be handled by service providers that help operate hosting, email, monitoring, backups or other necessary functions. They should receive only what is needed for their work and be subject to suitable confidentiality and security commitments.",
        },
        {
          title: "6. Retention and security",
          text: "Information is kept only for as long as needed for the service, school instructions, safety, record-keeping and applicable obligations. Class Hero Hub uses technical and organisational measures intended to reduce unauthorised access, loss and misuse, but no online service can remove every risk.",
        },
        {
          title: "7. Requests, corrections and deletion",
          text: "Requests about school records should usually begin with the school. Staff account or service questions can be sent to Class Hero Hub support. A request may require identity and permission checks, and some records may need to be retained for school, safety, backup or legal reasons.",
        },
        {
          title: "8. Changes and contact",
          text: "This policy may be updated as the pilot service develops or agreements change. Material updates will be communicated through an appropriate service or school channel. Questions can be sent to support@classherohub.com.",
        },
      ],
      notice: {
        title: "School agreements and local law",
        text: "Applicable law and signed school agreements may provide additional or country-specific terms. Those terms take priority where they apply.",
      },
      cta: {
        heading: "Have a privacy or data question?",
        text: "Use the data-request guide to find the right first contact, or email support for help.",
        label: "Data and account requests",
        href: "/data-requests",
        secondaryLabel: "Contact support",
        secondaryHref: supportEmailHref,
      },
    },
    terms: {
      pageTitle: "Terms of Service | Class Hero Hub",
      metaDescription:
        "The baseline terms for authorised use of the Class Hero Hub pilot service.",
      eyebrow: "Terms of Service",
      heading: "Terms of Service",
      intro:
        "These baseline terms describe authorised use of the current Class Hero Hub pilot service. A signed school agreement may add or replace terms for a participating school.",
      highlights: [
        "Effective 3 August 2026",
        "Authorised school use",
        "Pilot availability",
        "Respectful and lawful use",
      ],
      sections: [
        {
          title: "1. The service",
          text: "Class Hero Hub provides school organisation, teaching, communication, family-update, reporting and related features for participating schools and their authorised staff.",
        },
        {
          title: "2. Authorised accounts",
          text: "Users must sign in with their own account, provide accurate information, keep access details secure and use only the schools, classes, students and features they are permitted to use. Accounts must not be shared.",
        },
        {
          title: "3. School responsibilities",
          text: "A school is responsible for deciding who may use the service, keeping staff and student information accurate, setting suitable policies, obtaining any permissions it needs and responding to its community about school records and decisions.",
        },
        {
          title: "4. Acceptable use",
          text: "The service must not be used to break the law, harm or harass others, access information without permission, bypass security, upload malicious material, disrupt the service or create public negative rankings of students.",
        },
        {
          title: "5. Content and communication",
          text: "Schools and users remain responsible for the information and material they add or share. They should use respectful, accurate communication and follow school policy for student information, photos, messaging and safeguarding matters.",
        },
        {
          title: "6. Pilot availability",
          text: "Pilot features may change, be limited or occasionally be unavailable while the service is evaluated and improved. We aim to communicate material changes and restore service issues reasonably, but uninterrupted availability is not promised.",
        },
        {
          title: "7. Suspension and ending access",
          text: "Access may be limited or removed when needed to protect people or the service, respond to misuse, follow a school instruction, address non-payment under an applicable agreement or end a pilot. Relevant school agreements may describe additional steps.",
        },
        {
          title: "8. Changes and contact",
          text: "These terms may be updated as the service develops. Material changes will be communicated appropriately. Questions about these terms can be sent to support@classherohub.com.",
        },
      ],
      notice: {
        title: "Additional school terms",
        text: "Applicable law and a signed school agreement may add jurisdiction-specific, commercial, service or liability terms. Those terms take priority where they apply.",
      },
      cta: {
        heading: "Have a question about use of the pilot service?",
        text: "Contact the team or review the Privacy Policy for more information about data use.",
        label: "Contact support",
        href: supportEmailHref,
        secondaryLabel: "Privacy Policy",
        secondaryHref: "/privacy",
      },
    },
    dataRequests: {
      pageTitle: "Data and account requests | Class Hero Hub",
      metaDescription:
        "Find the right first contact for school records, Class Hero Hub staff accounts and Family Hero Hub family accounts.",
      eyebrow: "Data and account requests",
      heading: "Start with the team that knows the record.",
      intro:
        "The quickest route depends on whether your question is about a school record, a staff account or a Family Hero Hub family account.",
      highlights: [
        "School record → your school",
        "Staff account → school administrator",
        "Family account → Family Hero Hub",
      ],
      sections: [
        {
          title: "Student, guardian or school records",
          text: "Contact the school that created or manages the record. The school can check your identity, correct its information and decide how the request should be handled.",
        },
        {
          title: "Class Hero Hub staff accounts",
          text: "Ask your school administrator to check your staff role, class assignment or account status. Contact Class Hero Hub support if the school confirms the details and you still cannot use the service.",
        },
        {
          title: "Copies, corrections or deletion",
          text: "Describe the record and the outcome you are requesting. Identity and permission checks may be required. Some information may need to remain for school history, safety, backups or applicable obligations.",
        },
        {
          title: "Family Hero Hub accounts",
          text: "Use Family Hero Hub support for a parent, caregiver, child dashboard or linked-device account question. The school remains the right contact for the school information shown there.",
        },
      ],
      notice: {
        title: "Keep the first message simple",
        text: "Include your name, school, role, a safe contact address and the type of request. Do not email passwords, sign-in links, complete student files, private messages, survey answers or safeguarding material.",
      },
      cta: {
        heading: "Not sure where to begin?",
        text: "Send a short, non-sensitive summary and support will help you identify the right route.",
        label: "Email Class Hero Hub",
        href: supportEmailHref,
        secondaryLabel: "Privacy Policy",
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
    requestPilot: "اطلب برنامجاً تجريبياً",
    staffLogin: "دخول الموظفين",
    dashboard: "لوحة التحكم",
    menu: "استكشف كلاس هيرو هب",
    openMenu: "فتح قائمة الموقع",
    closeMenu: "إغلاق قائمة الموقع",
  },
  footer: {
    description:
      "يمنح كلاس هيرو هب المعلمين وفرق المدرسة مكاناً واحداً للتعليم اليومي والتواصل والتحديثات التي تشاركها المدرسة مع الأسر.",
    tagline: "أدوات عملية لليوم المدرسي.",
    product: "المنتج",
    support: "الدعم",
    legal: "قانوني",
    home: "الرئيسية",
    features: "نظرة عامة على المنتج",
    howItWorks: "كيف يعمل",
    schools: "للمدارس",
    familyConnection: "الربط مع الأسرة",
    faq: "الأسئلة الشائعة",
    requestPilot: "اطلب برنامجاً تجريبياً",
    contact: "تواصل معنا",
    administratorGuide: "دليل مسؤول المدرسة",
    teacherGuide: "دليل المعلم",
    familyGuide: "دليل الأسرة",
    safetyPrivacy: "السلامة والخصوصية والدعم",
    privacy: "سياسة الخصوصية",
    terms: "شروط الخدمة",
    dataRequests: "طلبات البيانات والحساب",
    emailLabel: "الدعم وطلبات البرامج التجريبية",
  },
  home: {
    pageTitle: "كلاس هيرو هب | مساحة عملية ليوم المدرسة",
    metaDescription:
      "مكان واحد للمعلمين والتواصل المدرسي وتحديثات الأسر، إلى جانب الأنظمة التي تستخدمها المدرسة بالفعل.",
    eyebrow: "أدوات عملية لليوم المدرسي.",
    heading: "ندعم المعلمين. ونُبقي الأسر على اطّلاع.",
    intro:
      "يجمع كلاس هيرو هب للفرق المدرسية الواجبات والسلوك والتقدير والتنبيهات والمحادثات والاستبيانات وتحديثات الأسر في مكان واحد، إلى جانب الأنظمة التي تستخدمها المدرسة بالفعل.",
    primaryCta: "اطلب برنامجاً تجريبياً",
    secondaryCta: "استكشف المنتج",
    strapline: "لقادة المدارس والمسؤولين والمعلمين · العربية والإنجليزية",
    schoolWorkspaceLabel: "عمل المدرسة اليومي",
    schoolWorkspaceTitle: "ابدأ بصفك.",
    schoolWorkspaceText:
      "افتح الصف وانتقل مباشرة إلى الواجبات والتنبيهات والسلوك والتقدير والتقويم أو الرسائل.",
    familyDeliveryLabel: "تحديثات الأسرة",
    familyDeliveryTitle: "أوصل المعلومة المدرسية إلى الأسرة بوضوح.",
    familyDeliveryText:
      "يرى ولي الأمر ما تشاركه المدرسة عن طفله في Family Hero Hub.",
    boundaryLabel: "يكمل أنظمة المدرسة الحالية",
    boundaryText:
      "واصل استخدام أنظمة مدرستك الأساسية، واستخدم كلاس هيرو هب للمعلمين والتواصل وتحديثات الأسر.",
    benefitsEyebrow: "أدوات يومية للموظفين",
    benefitsHeading: "يسهل العثور على الأدوات التي يستخدمها المعلمون أكثر.",
    benefitsIntro:
      "يبدأ المعلمون وفرق المدرسة بالمهمة الحالية ويواصلون من حيث توقفوا.",
    benefits: [
      {
        title: "ابدأ من الصف الذي تدرّسه",
        text: "افتح الصف المكلف به وانتقل مباشرة إلى الطلبة والواجبات والمفكرة والسلوك أو التقدير.",
      },
      {
        title: "شارك تحديثات مدرسية واضحة",
        text: "انشر التنبيهات والتحديثات وعناصر التقويم والصور المدرسية من مساحة الموظفين نفسها.",
      },
      {
        title: "قدّر الجهد وتابع ما يلزم",
        text: "احتفِ بالسلوك الإيجابي، وأبقِ ملاحظات التحسين خاصة، وعُد إليها عند الحاجة إلى متابعة.",
      },
      {
        title: "استمع إلى الأسرة",
        text: "استخدم المحادثات المدرسية والاستبيانات والتصويتات لاستمرار التواصل المفيد بين المدرسة والمنزل.",
      },
    ],
    featureEyebrow: "رؤية أوضح وإعداد مساند",
    featureHeading: "معلومات واضحة للقادة. وإعداد بسيط للفرق.",
    featureIntro:
      "توضح التقارير ما حدث وأين قد تكون المتابعة مطلوبة، بينما يحافظ إعداد المدرسة على حداثة بيانات الموظفين والصفوف.",
    featureGroups: [
      {
        title: "اعرف أين تبدأ المتابعة",
        text: "يستطيع القادة مراجعة نشاط المدرسة ومعرفة ما تغير وتحديد ما يحتاج إلى نقاش أو متابعة.",
        items: [
          "التقارير واتجاهات السلوك",
          "معرفة ما إذا كانت الرسائل قد وصلت وقُرئت",
          "معرفة ما تغير ومتى",
          "مساحة مستقلة لمراجعة حماية الطلبة",
        ],
      },
      {
        title: "إعداد يساند الأنظمة الحالية",
        text: "يستطيع مسؤولو المدرسة تجهيز مساحة كلاس هيرو هب مع استمرار المدرسة في استخدام أنظمتها الأساسية.",
        items: [
          "الأعوام الدراسية والصفوف والمواد",
          "تكليفات الموظفين وقوائم الطلبة",
          "استيراد ملفات CSV بعد مراجعتها والتحديثات السنوية",
          "عمليات تصدير السجلات المدعومة",
        ],
      },
    ],
    proofEyebrow: "داخل كلاس هيرو هب",
    proofHeading: "شاهد المنتج أثناء العمل.",
    proofIntro:
      "هذه شاشات حقيقية من كلاس هيرو هب، مع بيانات توضيحية أُنشئت خصيصاً لهذا الموقع.",
    proofDataNote: "بيانات توضيحية للمدرسة والموظفين فقط.",
    proofItems: [
      {
        src: "/product/teacher-workflow.png",
        alt: "شاشة المعلم في كلاس هيرو هب تعرض صفوفاً توضيحية",
        height: 650,
        eyebrow: "مساحة عمل المعلم",
        title: "الصفوف والأدوات الشائعة في متناول اليد",
        text: "يبدأ المعلم من صفوفه المكلف بها وينتقل إلى الطلبة والتنبيهات والتقويم من دون البحث بين قوائم كثيرة.",
      },
      {
        src: "/product/school-overview.png",
        alt: "شاشة إعداد المدرسة في كلاس هيرو هب لمدرسة توضيحية",
        height: 900,
        eyebrow: "الإعداد المساند",
        title: "صورة واضحة لما أصبح جاهزاً",
        text: "يرى المسؤول ما أصبح جاهزاً وما يزال يحتاج إلى اهتمام، ويواصل من حيث توقف.",
      },
    ],
    familyEyebrow: "كلاس هيرو هب + Family Hero Hub",
    familyHeading: "تحديثات المدرسة للأسر.",
    familyIntro:
      "يستخدم الموظفون كلاس هيرو هب للعمل المدرسي والتواصل، ويرى أولياء الأمور تحديثات المدرسة التي تشاركها معهم في Family Hero Hub.",
    schoolSideTitle: "1 · يعمل الموظفون في كلاس هيرو هب",
    schoolSideText:
      "يدير الموظفون الواجبات والتنبيهات والرسائل وغيرها من تحديثات المدرسة.",
    connectionTitle: "2 · تشارك المدرسة تحديثاً",
    connectionText:
      "عندما يشارك الموظفون تحديثاً للأسرة، يستطيع ولي الأمر رؤيته لطفله.",
    familySideTitle: "3 · يراه ولي الأمر في Family Hero Hub",
    familySideText:
      "تظهر الواجبات والتنبيهات وعناصر التقويم ونقاط المدرسة والاستبيانات أو المحادثات إلى جانب أدوات الأسرة.",
    familyBoundary:
      "لا يحتاج أولياء الأمور إلى تطبيق مدرسي آخر أو بيانات دخول الموظفين. تبقى تجربتهم المدرسية داخل Family Hero Hub.",
    familyCta: "تعرّف على الربط مع الأسرة",
    trustEyebrow: "الثقة في الاستخدام اليومي",
    trustHeading: "حماية بسيطة للعمل المدرسي اليومي.",
    trustIntro:
      "يرى الموظفون المعلومات والأدوات التي يحتاجونها فقط. وتبقى السجلات الحساسة خاصة، ويمكن للمدرسة معرفة ما تغير ومتى.",
    trustItems: [
      {
        title: "صلاحيات واضحة للموظفين",
        text: "يرى الموظف المدارس والصفوف والطلبة والأدوات التي يحتاجها في عمله.",
      },
      {
        title: "سجلات سلوك خاصة",
        text: "لا يتحول السلوك الذي يحتاج إلى تحسين إلى ترتيب علني أو وسيلة لإحراج الطلبة.",
      },
      {
        title: "مساحة مستقلة لحماية الطلبة",
        text: "تظل مراجعة حماية الطلبة منفصلة عن المحادثات العادية ونشاط الرسائل اليومي.",
      },
    ],
    bilingualEyebrow: "العربية + English",
    bilingualHeading: "جاهز للمجتمعات المدرسية ثنائية اللغة.",
    bilingualText:
      "يمكن للموظفين استخدام كلاس هيرو هب بالعربية أو الإنجليزية، مع تصميم كامل من اليمين إلى اليسار في التجربة العربية.",
    bilingualPoint1:
      "لا يغيّر تبديل لغة الواجهة الأسماء أو المحتوى الذي أدخلته المدرسة.",
    bilingualPoint2:
      "تدعم التصاميم المتجاوبة عمل الموظفين عبر الهواتف والأجهزة اللوحية والحواسيب.",
    faqEyebrow: "أسئلة المدارس",
    faqHeading: "إجابات عن أسئلة المدارس الشائعة.",
    faqIntro:
      "تعرّف على من يستخدم كلاس هيرو هب، وكيف تصل التحديثات إلى الأسر، وكيف يمكن أن يبدأ البرنامج التجريبي.",
    faqCta: "اقرأ جميع الأسئلة",
    finalHeading: "هل يمكن لكلاس هيرو هب أن يجعل يوم مدرستك أسهل؟",
    finalText:
      "أخبرنا بما يستغرق وقتاً أطول من اللازم أو يترك الأسر من دون صورة واضحة. سنعرض أجزاء كلاس هيرو هب التي قد تساعدكم.",
    finalPrimary: "اطلب برنامجاً تجريبياً",
    finalSecondary: "تواصل مع الفريق",
  },
  faq: {
    pageTitle: "الأسئلة الشائعة | كلاس هيرو هب",
    metaDescription:
      "إجابات عن كلاس هيرو هب واستخدام المدارس وتحديثات الأسر واللغات والبرامج التجريبية.",
    eyebrow: "الأسئلة الشائعة",
    heading: "الأسئلة العملية التي تطرحها المدارس أولاً.",
    intro:
      "مقدمة مباشرة عن المنتج والفئات التي يخدمها وكيف يربط موظفي المدرسة بالأسر.",
    items: arabicFaq,
    ctaHeading: "هل لديك سؤال خاص بمدرستك؟",
    ctaText:
      "أخبرنا بما تحاول تحسينه وسنوجهك إلى الإجابة أو العرض الأكثر فائدة.",
    ctaLabel: "تواصل مع الفريق",
  },
  pages: {
    howItWorks: {
      pageTitle: "كيف يعمل كلاس هيرو هب",
      metaDescription:
        "تعرّف على انتقال المعلمين وفرق المدرسة من العمل اليومي إلى تحديثات الأسرة والمتابعة والإعداد المساند.",
      eyebrow: "كيف يعمل",
      heading: "ابدأ بالعمل المطلوب اليوم.",
      intro:
        "يبدأ المعلمون وفرق المدرسة بالصف أو الرسالة أو المتابعة المطلوبة. وتظهر تحديثات الأسرة التي يشاركونها في Family Hero Hub.",
      highlights: ["العمل من الصف", "تواصل مستمر", "تحديثات تصل إلى الأسرة"],
      sections: [
        {
          title: "ابدأ بصفك",
          text: "يبدأ المعلم من صفوفه المكلف بها وينتقل مباشرة إلى الطلبة والواجبات والتنبيهات والسلوك والتقدير والتقويم أو الرسائل.",
          bullets: ["الأدوات الشائعة قريبة من كل صف", "واصل من حيث توقفت"],
        },
        {
          title: "شارك التحديثات مع الأسر",
          text: "عندما تشارك المدرسة معلومات موجهة للأسرة، يراها ولي الأمر في Family Hero Hub للطفل المرتبط. ويواصل فريق المدرسة عمله في كلاس هيرو هب.",
          bullets: [
            "يواصل أولياء الأمور استخدام Family Hero Hub",
            "تختار المدرسة الميزات التي تبدأ بها",
          ],
        },
        {
          title: "جهّز مساحة العمل المساندة",
          text: "يُعد المسؤولون بيانات الموظفين والطلبة والأعوام الدراسية والصفوف والمواد. ويمكن إدخال بيانات الطلبة والموظفين المدعومة يدوياً أو تجهيزها من ملفات CSV بعد مراجعتها.",
        },
      ],
      cta: {
        heading: "شاهد كيف يمكن أن يعمل في مدرستك.",
        text: "يمكن للعرض القصير أن يغطي المهام اليومية والتواصل مع الأسر الأكثر أهمية لفريقك.",
        label: "اطلب عرضاً توضيحياً",
        href: "/pilot",
        secondaryLabel: "استكشف المنتج",
        secondaryHref: "/features",
      },
    },
    features: {
      pageTitle: "نظرة عامة على كلاس هيرو هب",
      metaDescription:
        "استكشف أدوات التعليم اليومي والتواصل المدرسي وتحديثات الأسرة والمتابعة والإعداد المساند في كلاس هيرو هب.",
      eyebrow: "نظرة عامة على المنتج",
      heading: "أدوات عملية للعمل الذي يتكرر كل يوم مدرسي.",
      intro:
        "يجد المعلمون الأدوات الشائعة من خلال الصف أو الطالب، ويعمل كلاس هيرو هب إلى جانب أنظمة المدرسة الحالية.",
      highlights: [
        "عمل المعلم اليومي",
        "التواصل المدرسي",
        "تحديثات الأسرة",
        "التقارير والمتابعة",
      ],
      sections: [
        {
          title: "أدوات المعلم اليومية",
          text: "ساعد المعلمين على الانتقال بسرعة بين صفوفهم والمهام التي ينفذونها أكثر من غيرها.",
          bullets: [
            "الواجبات وعناصر المفكرة والمتطلبات",
            "سجلات السلوك الخاصة والتقدير الإيجابي",
            "التنبيهات والتحديثات والتقويم والصور",
          ],
        },
        {
          title: "التواصل المدرسي",
          text: "أرسل الرسائل إلى الصف أو الطالب، واعرف ما إذا كانت قد وصلت وقُرئت، وحدد أوقات التواصل المدرسية.",
          bullets: [
            "محادثات مدرسية بالنص والصور والملاحظات الصوتية",
            "التنبيهات والاستبيانات والتصويتات",
            "تحديثات الأسرة في Family Hero Hub",
          ],
        },
        {
          title: "رؤية أوضح لمتابعة أفضل",
          text: "استخدم التقارير والاتجاهات لمعرفة ما حدث والاحتفاء بالتقدم وتحديد ما يحتاج إلى اهتمام.",
          bullets: [
            "اتجاهات السلوك والمشاركة",
            "مراجعة حالة الرسائل ونشاط المدرسة",
            "مساحة مستقلة لمراجعة حماية الطلبة",
          ],
        },
        {
          title: "إعداد مدرسي مساند",
          text: "أعد الأعوام الدراسية والصفوف والمواد وتكليفات الموظفين وقوائم الطلبة مع إبقاء أنظمة المدرسة الأساسية في مكانها.",
          bullets: [
            "استيراد بيانات الطلبة والموظفين المدعومة من ملفات CSV بعد مراجعتها",
            "تحديث السجلات سنوياً",
            "تصدير السجلات المدعومة",
          ],
        },
      ],
      cta: {
        heading: "أي جزء سيصنع الفرق الأكبر أولاً؟",
        text: "يمكننا تصميم العرض حول مشكلة مدرسية حقيقية بدلاً من عرض كل ميزة بلا تمييز.",
        label: "اطلب برنامجاً تجريبياً",
        href: "/pilot",
        secondaryLabel: "كيف يعمل",
        secondaryHref: "/how-it-works",
      },
    },
    schools: {
      pageTitle: "كلاس هيرو هب للمدارس",
      metaDescription:
        "مساحة عمل مدرسية عملية للقادة والمسؤولين والمعلمين والمجتمعات ثنائية اللغة.",
      eyebrow: "للمدارس",
      heading: "مساحة عملية لكل من يشارك في يوم المدرسة.",
      intro:
        "يمنح كلاس هيرو هب المعلمين وفرق المدرسة مكاناً واحداً للمهام اليومية والتواصل وتحديثات الأسر، إلى جانب أنظمة المدرسة الحالية.",
      highlights: [
        "المعلمون",
        "فريق المدرسة",
        "قادة المدارس",
        "الفرق ثنائية اللغة",
      ],
      sections: [
        {
          title: "للمعلمين",
          text: "ابدأ من الصفوف المكلف بها واجعل الإجراءات المتكررة قريبة، ليأخذ التسجيل والتواصل والمتابعة وقتاً أقل.",
        },
        {
          title: "لفريق المدرسة",
          text: "انشر التنبيهات والتحديثات، وأدر التقويم، واستخدم المحادثات والاستبيانات، واعرف ما يحتاج إلى متابعة.",
        },
        {
          title: "للقادة والمسؤولين",
          text: "راجع التواصل والسلوك والتقدير والمشاركة، ثم حافظ على حداثة بيانات الموظفين والصفوف والطلبة.",
        },
        {
          title: "للمجتمعات العربية والإنجليزية",
          text: "استخدم الواجهة بالعربية أو الإنجليزية مع إبقاء أسماء المدرسة ومحتواها المكتوب كما أُدخل تماماً.",
        },
      ],
      cta: {
        heading: "أخبرنا بأي أجزاء من اليوم المدرسي تستغرق وقتاً طويلاً.",
        text: "سنركز على المعلمين والفرق والمهام المدرسية التي تحتاج إلى أكبر قدر من المساعدة.",
        label: "ابدأ محادثة",
        href: "/pilot",
        secondaryLabel: "اقرأ الأسئلة الشائعة",
        secondaryHref: "/faq",
      },
    },
    familyConnection: {
      pageTitle: "كلاس هيرو هب وFamily Hero Hub",
      metaDescription:
        "تعرّف على استخدام الموظفين لكلاس هيرو هب ووصول تحديثات المدرسة إلى أولياء الأمور في Family Hero Hub.",
      eyebrow: "الربط مع الأسرة",
      heading: "تحديثات المدرسة للأسر.",
      intro:
        "يستخدم الموظفون كلاس هيرو هب للعمل المدرسي والتواصل، ويرى أولياء الأمور تحديثات المدرسة التي تشاركها معهم في Family Hero Hub.",
      highlights: [
        "مكان واحد للموظفين",
        "Family Hero Hub لأولياء الأمور",
        "تحديثات مدرسية واضحة",
      ],
      sections: [
        {
          title: "تعمل المدرسة في كلاس هيرو هب",
          text: "يدير الموظفون الواجبات والتنبيهات والمحادثات وغيرها من تحديثات المدرسة في كلاس هيرو هب.",
        },
        {
          title: "يرى ولي الأمر معلومات المدرسة في Family Hero Hub",
          text: "قد تشمل المعلومات الخاصة بالطفل المرتبط الواجبات والتنبيهات والتحديثات ونقاط المدرسة وعناصر التقويم والاستبيانات ومحادثات المدرسة، بحسب ما تستخدمه المدرسة.",
        },
        {
          title: "مكان واحد مألوف للأسرة",
          text: "لا يسجل أولياء الأمور الدخول إلى كلاس هيرو هب. تظهر معلومات المدرسة إلى جانب أدوات الأسرة في Family Hero Hub، وتبقى المدرسة جهة الاتصال الأولى بشأن السجلات المدرسية.",
        },
      ],
      cta: {
        heading: "هل تحتاج إلى شرح ذلك للأسر؟",
        text: "يمكننا مساعدة فريقك على شرح ما يستخدمه الموظفون وأين يرى أولياء الأمور تحديثات المدرسة.",
        label: "تحدث مع الفريق",
        href: "/contact",
        secondaryLabel: "افتح دليل الأسرة",
        secondaryHref: "/guides/families",
      },
    },
    pilot: {
      pageTitle: "اطلب برنامجاً تجريبياً لكلاس هيرو هب",
      metaDescription:
        "أخبرنا عن مدرستك ورتب عرضاً أو محادثة تجريبية مناسبة لكلاس هيرو هب.",
      eyebrow: "اطلب برنامجاً تجريبياً",
      heading: "لنبدأ بمحادثة عن مدرستك.",
      intro:
        "أخبرنا بما يعمل جيداً، وما يتطلب جهداً أكبر من اللازم، وما ترغب في تحسينه. سنحافظ على تركيز المحادثة.",
      highlights: ["محادثة مركزة", "عرض مناسب", "برنامج تجريبي عملي"],
      sections: [
        {
          title: "نتعرف على مدرستك",
          text: "نسأل عن أنظمتك الحالية والعمل المدرسي الذي ترغب في تحسينه أكثر.",
        },
        {
          title: "نعرض ما يهم",
          text: "يركز العرض على أجزاء كلاس هيرو هب المرتبطة بفريقك وأولوياتك.",
        },
        {
          title: "نتفق على ما يلي",
          text: "إذا بدا كلاس هيرو هب مفيداً، نتفق على برنامج تجريبي محدود يشارك فيه الموظفون المعنيون من المدرسة.",
        },
      ],
      form: {
        heading: "أخبرنا عن مدرستك",
        intro: "ستساعدنا بعض التفاصيل على جعل المحادثة الأولى مفيدة.",
        nameLabel: "اسمك",
        schoolLabel: "المدرسة",
        roleLabel: "دورك الوظيفي",
        regionLabel: "الدولة أو المنطقة",
        emailLabel: "البريد الإلكتروني للعمل",
        messageLabel: "ما الذي ترغب في تحسينه؟",
        messageHint: "تكفي نبذة قصيرة. يرجى عدم تضمين معلومات سرية عن الطلبة.",
        submitLabel: "إرسال طلب البرنامج التجريبي",
        submittingLabel: "جارٍ إرسال الطلب…",
        successHeading: "شكراً لك — تم إرسال طلبك.",
        successText: "سنقرأه ونتواصل معك عبر البريد الإلكتروني الذي قدمته.",
        rateLimitError:
          "وصلتنا عدة طلبات من هذا الاتصال. يرجى الانتظار قليلاً ثم المحاولة مرة أخرى.",
        unavailableError:
          "إرسال البريد غير متاح مؤقتاً. يرجى استخدام خيار البريد المباشر أدناه.",
        generalError: "تعذر إرسال طلبك الآن. حاول مرة أخرى أو راسلنا مباشرة.",
        directHeading: "تفضل البريد الإلكتروني؟",
        directText:
          "يمكنك التواصل مع الفريق مباشرة عبر support@classherohub.com.",
        directLabel: "راسل الفريق",
      },
      cta: {
        heading: "هل تفضل البدء عبر البريد الإلكتروني؟",
        text: "أرسل ملاحظة قصيرة عن مدرستك والموضوع الذي ترغب في مناقشته.",
        label: "راسل الفريق",
        href: pilotEmailHref,
        secondaryLabel: "استكشف المنتج",
        secondaryHref: "/features",
      },
    },
    contact: {
      pageTitle: "تواصل مع كلاس هيرو هب",
      metaDescription:
        "تواصل مع كلاس هيرو هب بشأن العروض والبرامج التجريبية ودعم المدارس وأسئلة الخصوصية.",
      eyebrow: "تواصل معنا",
      heading: "كيف يمكننا مساعدتك؟",
      intro:
        "سواء كنت تستكشف المنتج أو تستخدم كلاس هيرو هب حالياً، أرسل لنا رسالة قصيرة وسنوصلها إلى الشخص المناسب.",
      highlights: ["البرامج التجريبية", "دعم المدارس", "إرشاد الأسر"],
      sections: [
        {
          title: "محادثات المنتج والبرامج التجريبية",
          text: "أخبرنا عن مدرستك ودورك والمهمة التي ترغب في تحسينها أكثر من غيرها.",
        },
        {
          title: "دعم مدرسة تستخدم المنتج",
          text: "اذكر اسم المدرسة ودورك ووصفاً قصيراً للمشكلة. تفيد الصور عندما لا تتضمن معلومات مدرسية خاصة.",
        },
        {
          title: "أسئلة الأسر",
          text: "ابدأ بالمدرسة إذا كان السؤال عن معلومات مدرسية. واستخدم دعم Family Hero Hub للمساعدة في حساب الأسرة أو تجربتها.",
        },
        {
          title: "أسئلة الخصوصية والبيانات",
          text: "استخدم دليل طلبات البيانات لمعرفة نقطة البداية المناسبة لسجل مدرسي أو حساب موظف أو حساب أسرة.",
        },
      ],
      notice: {
        title: "بريد الدعم",
        text: "راسل support@classherohub.com. يرجى عدم إرسال كلمات المرور أو روابط الدخول أو معلومات سرية عن الطلبة.",
      },
      cta: {
        heading: "أرسل لنا رسالة قصيرة.",
        text: "سنرد بخيار الدعم المناسب من دون طلب معلومات حساسة عبر البريد.",
        label: "راسل كلاس هيرو هب",
        href: supportEmailHref,
        secondaryLabel: "اقرأ الأسئلة الشائعة",
        secondaryHref: "/faq",
      },
    },
    administratorGuide: {
      pageTitle: "دليل مسؤول المدرسة | كلاس هيرو هب",
      metaDescription:
        "مقدمة عملية لإعداد المدرسة والمحافظة على سجلاتها في كلاس هيرو هب.",
      eyebrow: "دليل مسؤول المدرسة",
      heading: "أنشئ مساحة عمل مدرسية يعتمد عليها الجميع.",
      intro:
        "يسهّل الإعداد الواضح العمل اليومي للمعلمين والطلبة والصفوف والأسر.",
      highlights: ["الإعداد", "الدعوات", "المراجعة", "التحضير للعام التالي"],
      sections: [
        {
          title: "ابدأ بالهيكل الأكاديمي",
          text: "أكد ملف المدرسة والعام الدراسي الحالي والفروع والصفوف والمواد والمصطلحات التي تستخدمها مدرستك.",
        },
        {
          title: "أضف الموظفين والطلبة بعناية",
          text: "أنشئ تكليفات الموظفين وانقل سجلات الطلبة عبر الاستيراد بعد مراجعته أو باستخدام أدوات المدرسة المتاحة.",
        },
        {
          title: "أعد الأدوات التي تحتاجها المدرسة",
          text: "جهّز فئات السلوك وميزات الأسرة وخيارات التواصل وإعدادات المدرسة الأخرى بترتيب عملي.",
        },
        {
          title: "راجع قبل المشاركة",
          text: "تحقق من الجمهور والصف والتوقيت قبل نشر التنبيهات أو التحديثات أو فعاليات التقويم أو معلومات الأسرة.",
        },
        {
          title: "حافظ على حداثة السجلات",
          text: "صحح السجلات سريعاً، وراجع الأنشطة وعمليات التصدير عند الحاجة، وجهز العام الدراسي التالي من دون فقدان السجل المفيد.",
        },
      ],
      cta: {
        heading: "هل تحتاج إلى مساعدة في قرار إعداد؟",
        text: "أخبرنا عن القسم الذي تعمل عليه في المدرسة والنتيجة التي تريد تحقيقها.",
        label: "تواصل مع الدعم",
        href: supportEmailHref,
        secondaryLabel: "دليل المعلم",
        secondaryHref: "/guides/teacher",
      },
    },
    teacherGuide: {
      pageTitle: "دليل المعلم | كلاس هيرو هب",
      metaDescription:
        "مقدمة عملية للصفوف والواجبات والسلوك والتقدير والتواصل في كلاس هيرو هب.",
      eyebrow: "دليل المعلم",
      heading: "ابدأ بصفوفك.",
      intro:
        "يبقي كلاس هيرو هب مهام التعليم الشائعة مع الصف والطلبة الذين تعمل معهم بالفعل.",
      highlights: ["الصفوف", "الواجبات", "التقدير", "التواصل"],
      sections: [
        {
          title: "افتح الصف الذي تعمل معه",
          text: "تعرض مساحة المعلم صفوفه الأساسية ومواده المكلف بها، لتمنحه نقطة بداية واضحة لليوم.",
        },
        {
          title: "سجل السلوك والتقدير",
          text: "أضف معلومات السلوك من الصف أو الطالب المناسب، واستخدم التقدير الإيجابي للاحتفاء بالجهد الحقيقي.",
        },
        {
          title: "حدد العمل والتذكيرات",
          text: "أنشئ الواجبات وعناصر المفكرة والمتطلبات وفعاليات التقويم بتواريخ وتعليمات تفهمها الأسر.",
        },
        {
          title: "شارك تحديثات مفيدة",
          text: "استخدم التنبيهات والتحديثات المدرسية والصور ومحادثات المدرسة لتواصل واضح وهادف.",
        },
        {
          title: "اسأل عندما لا تبدو المعلومات صحيحة",
          text: "إذا لم يطابق صف أو طالب أو أداة تكليفك، فتواصل مع مسؤول المدرسة قبل محاولة تجاوز المشكلة.",
        },
      ],
      cta: {
        heading: "هل تحتاج إلى مساعدة في مهمة للمعلم؟",
        text: "اذكر مدرستك وصفك وما كنت تحاول القيام به.",
        label: "تواصل مع الدعم",
        href: supportEmailHref,
        secondaryLabel: "السلامة والدعم",
        secondaryHref: "/safety-privacy",
      },
    },
    familyGuide: {
      pageTitle: "دليل الأسرة | كلاس هيرو هب",
      metaDescription:
        "تعرّف على المكان الذي يرى فيه أولياء الأمور معلومات المدرسة المشتركة من كلاس هيرو هب.",
      eyebrow: "دليل الأسرة",
      heading: "يرى أولياء الأمور معلومات المدرسة في Family Hero Hub.",
      intro:
        "إذا كانت مدرسة طفلك تستخدم كلاس هيرو هب، فستشرح المدرسة طريقة الربط والمعلومات المتاحة.",
      highlights: [
        "اتبع خطوات المدرسة",
        "استخدم Family Hero Hub",
        "اسأل فريق الدعم المناسب",
      ],
      sections: [
        {
          title: "اربط الحساب من خلال المدرسة",
          text: "اتبع خطوات الدعوة أو الربط التي تقدمها مدرسة طفلك. تواصل مع المدرسة إذا لم يبدُ سجل الطفل أو الصف أو المدرسة صحيحاً.",
        },
        {
          title: "شاهد تحديثات المدرسة في Family Hero Hub",
          text: "بحسب المدرسة، قد ترى الواجبات والتنبيهات والتحديثات ونقاط المدرسة وعناصر التقويم والاستبيانات ومحادثات المدرسة للطفل المرتبط.",
        },
        {
          title: "استخدم المكان المناسب للمساعدة",
          text: "المدرسة هي جهة الاتصال الأولى بشأن معلومات المدرسة. ويمكن لدعم Family Hero Hub المساعدة في حساب الأسرة وتجربتها.",
        },
      ],
      cta: {
        heading: "هل تبحث عن تجربة الأسرة؟",
        text: "افتح Family Hero Hub لاستخدام أدوات الأسرة ورؤية معلومات المدرسة المشتركة عن طفلك.",
        label: "افتح Family Hero Hub",
        href: "https://familyherohub.com/",
        secondaryLabel: "كيف يعمل الربط",
        secondaryHref: "/family-connection",
      },
    },
    safetyPrivacy: {
      pageTitle: "السلامة والخصوصية والدعم | كلاس هيرو هب",
      metaDescription:
        "معلومات مبسطة عن الوصول وسجلات المدرسة والسلوك وحماية الطلبة وتحديثات الأسر والدعم في كلاس هيرو هب.",
      eyebrow: "السلامة والخصوصية والدعم",
      heading: "وسائل عملية لحماية العمل المدرسي اليومي.",
      intro:
        "يحد كلاس هيرو هب من الوصول إلى معلومات المدرسة، ويحفظ العمل الحساس في مساحات مخصصة.",
      highlights: [
        "سجلات خاصة بكل مدرسة",
        "معلومات سلوك خاصة",
        "مراجعة مخصصة لحماية الطلبة",
      ],
      sections: [
        {
          title: "يرى الموظفون ما يحتاجونه",
          text: "يسجل كل شخص الدخول بحسابه ويرى فقط المدارس والصفوف والطلبة والأدوات التي يحتاجها في عمله.",
        },
        {
          title: "تبقى سجلات المدرسة مع المدرسة المعنية",
          text: "يمكن للمدرسة معرفة ما تغير ومتى في الإجراءات المهمة للموظفين والإدارة.",
        },
        {
          title: "يبقى السلوك الذي يحتاج إلى تحسين خاصاً",
          text: "لا ينشئ كلاس هيرو هب ترتيبات سلبية علنية أو أدوات لإحراج الطلبة. ويراجع موظفو المدرسة التقدير الإيجابي.",
        },
        {
          title: "مراجعة حماية الطلبة مستقلة",
          text: "يستخدم موظفو حماية الطلبة مساحة مخصصة تبقى منفصلة عن محادثات المدرسة العادية.",
        },
        {
          title: "تصل تحديثات الأسرة عبر Family Hero Hub",
          text: "يرى أولياء الأمور معلومات المدرسة المشتركة للطفل المرتبط في Family Hero Hub. وتبدأ الأسئلة عن السجل المدرسي مع المدرسة.",
        },
      ],
      notice: {
        title: "أبلغ عن المخاوف العاجلة عبر المسار المحلي الصحيح",
        text: "دعم كلاس هيرو هب ليس خدمة طوارئ. اتبع سياسة حماية الطلبة في مدرستك وتواصل مع خدمة الطوارئ أو حماية الطفل المحلية المناسبة إذا كان شخص ما معرضاً لخطر فوري.",
      },
      cta: {
        heading: "هل تحتاج إلى مساعدة في الوصول أو الخصوصية أو سلامة المنتج؟",
        text: "أرسل وصفاً قصيراً وغير حساس وسنساعدك على الوصول إلى جهة الدعم المناسبة.",
        label: "تواصل مع الدعم",
        href: supportEmailHref,
        secondaryLabel: "اقرأ سياسة الخصوصية",
        secondaryHref: "/privacy",
      },
    },
    privacy: {
      pageTitle: "سياسة الخصوصية | كلاس هيرو هب",
      metaDescription:
        "سياسة الخصوصية الأساسية لخدمة كلاس هيرو هب في مرحلتها التجريبية.",
      eyebrow: "سياسة الخصوصية",
      heading: "سياسة الخصوصية",
      intro:
        "توضح هذه السياسة بصورة عامة كيفية استخدام كلاس هيرو هب للمعلومات أثناء تقديم الخدمة التجريبية الحالية للمدارس.",
      highlights: [
        "سارية من 3 أغسطس 2026",
        "خدمة تجريبية",
        "معلومات المدرسة والموظفين",
        "نرحب بالأسئلة",
      ],
      sections: [
        {
          title: "1. ما الخدمة",
          text: "كلاس هيرو هب مساحة عمل مدرسية يستخدمها الموظفون المصرح لهم لتنظيم المدرسة والعمل التعليمي والتواصل وتحديثات الأسر والتقارير والإدارة ذات الصلة. وتقرر المدارس كيفية استخدام الخدمة وفق سياساتها واتفاقياتها.",
        },
        {
          title: "2. المعلومات التي تستخدمها الخدمة",
          text: "قد تشمل معلومات المدرسة والصفوف، وتفاصيل حسابات الموظفين، وسجلات الطلبة وأولياء الأمور التي تقدمها المدرسة، ومعلومات التعلم والسلوك، والرسائل والوسائط، وإجابات الاستبيانات، ومعلومات تسجيل الدخول والأجهزة، وسجلات الإجراءات المنفذة في الخدمة.",
        },
        {
          title: "3. أسباب استخدام المعلومات",
          text: "تُستخدم المعلومات لتقديم الميزات المطلوبة، وتشغيل الحسابات والسجلات المدرسية، وإيصال معلومات المدرسة إلى الأسر المرتبطة، ودعم المستخدمين، والمحافظة على أمان الخدمة، والتحقيق في المشكلات، والوفاء بالالتزامات المتفق عليها مع المدارس المشاركة.",
        },
        {
          title: "4. المدارس وكلاس هيرو هب",
          text: "تتحمل المدرسة مسؤولية المعلومات التي تقدمها والأشخاص الذين تسمح لهم بالاستخدام والسياسات المدرسية التي تطبقها. ويقدم كلاس هيرو هب الخدمة ويدعمها وفق اتفاق المدرسة المعمول به.",
        },
        {
          title: "5. مقدمو الخدمات الضروريون",
          text: "قد يعالج المعلومات مقدمو خدمات يساعدون في الاستضافة والبريد والمراقبة والنسخ الاحتياطي أو وظائف ضرورية أخرى. وينبغي ألا يتلقوا إلا ما يحتاجون إليه لعملهم وأن يخضعوا لالتزامات مناسبة بالسرية والأمان.",
        },
        {
          title: "6. الاحتفاظ والأمان",
          text: "تُحفظ المعلومات للمدة اللازمة للخدمة وتعليمات المدرسة والسلامة وحفظ السجلات والالتزامات المعمول بها. يستخدم كلاس هيرو هب إجراءات تقنية وتنظيمية تهدف إلى تقليل الوصول غير المصرح به والفقد وسوء الاستخدام، لكن لا تستطيع أي خدمة إلكترونية إزالة كل المخاطر.",
        },
        {
          title: "7. الطلبات والتصحيح والحذف",
          text: "تبدأ طلبات السجلات المدرسية عادة مع المدرسة. ويمكن إرسال أسئلة حسابات الموظفين أو الخدمة إلى دعم كلاس هيرو هب. قد يتطلب الطلب التحقق من الهوية والصلاحية، وقد يلزم الاحتفاظ ببعض السجلات لأسباب مدرسية أو تتعلق بالسلامة أو النسخ الاحتياطي أو المتطلبات القانونية.",
        },
        {
          title: "8. التغييرات والتواصل",
          text: "قد تُحدث هذه السياسة مع تطور الخدمة التجريبية أو تغير الاتفاقيات. وسيتم إبلاغ التغييرات المهمة عبر قناة مناسبة في الخدمة أو المدرسة. يمكن إرسال الأسئلة إلى support@classherohub.com.",
        },
      ],
      notice: {
        title: "اتفاقيات المدارس والقانون المحلي",
        text: "قد يضيف القانون المعمول به واتفاق المدرسة الموقع شروطاً أخرى أو شروطاً خاصة بالدولة. وتسري تلك الشروط بالأولوية حيث تنطبق.",
      },
      cta: {
        heading: "هل لديك سؤال عن الخصوصية أو البيانات؟",
        text: "استخدم دليل طلبات البيانات لمعرفة جهة الاتصال الأولى، أو راسل الدعم للمساعدة.",
        label: "طلبات البيانات والحساب",
        href: "/data-requests",
        secondaryLabel: "تواصل مع الدعم",
        secondaryHref: supportEmailHref,
      },
    },
    terms: {
      pageTitle: "شروط الخدمة | كلاس هيرو هب",
      metaDescription:
        "الشروط الأساسية للاستخدام المصرح به لخدمة كلاس هيرو هب التجريبية.",
      eyebrow: "شروط الخدمة",
      heading: "شروط الخدمة",
      intro:
        "تصف هذه الشروط الأساسية الاستخدام المصرح به لخدمة كلاس هيرو هب التجريبية الحالية. وقد يضيف اتفاق مدرسي موقع شروطاً أخرى أو يستبدل بعض هذه الشروط للمدرسة المشاركة.",
      highlights: [
        "سارية من 3 أغسطس 2026",
        "استخدام مدرسي مصرح به",
        "خدمة تجريبية",
        "استخدام محترم ومشروع",
      ],
      sections: [
        {
          title: "1. الخدمة",
          text: "يقدم كلاس هيرو هب ميزات تنظيم المدرسة والتعليم والتواصل وتحديثات الأسرة والتقارير وما يرتبط بها للمدارس المشاركة وموظفيها المصرح لهم.",
        },
        {
          title: "2. الحسابات المصرح بها",
          text: "يجب على المستخدم تسجيل الدخول بحسابه، وتقديم معلومات صحيحة، والمحافظة على أمان بيانات الدخول، واستخدام المدارس والصفوف والطلبة والميزات المسموح له بها فقط. ولا يجوز مشاركة الحسابات.",
        },
        {
          title: "3. مسؤوليات المدرسة",
          text: "تتحمل المدرسة مسؤولية تحديد من يستخدم الخدمة، والمحافظة على دقة معلومات الموظفين والطلبة، ووضع السياسات المناسبة، والحصول على الموافقات اللازمة، والرد على مجتمعها بشأن السجلات والقرارات المدرسية.",
        },
        {
          title: "4. الاستخدام المقبول",
          text: "لا يجوز استخدام الخدمة لمخالفة القانون أو إيذاء الآخرين أو مضايقتهم أو الوصول إلى معلومات من دون إذن أو تجاوز الأمان أو تحميل مواد ضارة أو تعطيل الخدمة أو إنشاء ترتيبات سلبية علنية للطلبة.",
        },
        {
          title: "5. المحتوى والتواصل",
          text: "تبقى المدرسة والمستخدمون مسؤولين عن المعلومات والمواد التي يضيفونها أو يشاركونها. وينبغي استخدام تواصل محترم ودقيق واتباع سياسة المدرسة بشأن معلومات الطلبة والصور والرسائل ومسائل حماية الطلبة.",
        },
        {
          title: "6. توفر الخدمة التجريبية",
          text: "قد تتغير ميزات البرنامج التجريبي أو تكون محدودة أو غير متاحة أحياناً أثناء تقييم الخدمة وتحسينها. نهدف إلى إبلاغ التغييرات المهمة ومعالجة أعطال الخدمة بصورة معقولة، لكننا لا نعد بتوفر متواصل بلا انقطاع.",
        },
        {
          title: "7. تعليق الوصول أو إنهاؤه",
          text: "قد يحد الوصول أو ينهى عند الحاجة إلى حماية الأشخاص أو الخدمة، أو الاستجابة لسوء الاستخدام، أو اتباع تعليمات المدرسة، أو معالجة عدم السداد بموجب اتفاق سارٍ، أو إنهاء برنامج تجريبي. وقد توضح اتفاقية المدرسة خطوات إضافية.",
        },
        {
          title: "8. التغييرات والتواصل",
          text: "قد تُحدث هذه الشروط مع تطور الخدمة، وسيتم إبلاغ التغييرات المهمة بطريقة مناسبة. يمكن إرسال الأسئلة عن الشروط إلى support@classherohub.com.",
        },
      ],
      notice: {
        title: "شروط مدرسية إضافية",
        text: "قد يضيف القانون المعمول به أو اتفاق المدرسة الموقع شروطاً خاصة بالدولة أو التجارة أو مستوى الخدمة أو المسؤولية. وتسري تلك الشروط بالأولوية حيث تنطبق.",
      },
      cta: {
        heading: "هل لديك سؤال عن استخدام الخدمة التجريبية؟",
        text: "تواصل مع الفريق أو راجع سياسة الخصوصية لمزيد من المعلومات عن استخدام البيانات.",
        label: "تواصل مع الدعم",
        href: supportEmailHref,
        secondaryLabel: "سياسة الخصوصية",
        secondaryHref: "/privacy",
      },
    },
    dataRequests: {
      pageTitle: "طلبات البيانات والحساب | كلاس هيرو هب",
      metaDescription:
        "اعثر على جهة الاتصال الأولى للسجلات المدرسية وحسابات موظفي كلاس هيرو هب وحسابات الأسرة في Family Hero Hub.",
      eyebrow: "طلبات البيانات والحساب",
      heading: "ابدأ بالفريق الذي يعرف السجل.",
      intro:
        "يعتمد الطريق الأسرع على ما إذا كان سؤالك عن سجل مدرسي أو حساب موظف أو حساب أسرة في Family Hero Hub.",
      highlights: [
        "سجل مدرسي ← المدرسة",
        "حساب موظف ← مسؤول المدرسة",
        "حساب أسرة ← Family Hero Hub",
      ],
      sections: [
        {
          title: "سجلات الطلبة أو أولياء الأمور أو المدرسة",
          text: "تواصل مع المدرسة التي أنشأت السجل أو تديره. تستطيع المدرسة التحقق من هويتك وتصحيح معلوماتها وتحديد كيفية معالجة الطلب.",
        },
        {
          title: "حسابات موظفي كلاس هيرو هب",
          text: "اطلب من مسؤول المدرسة التحقق من دورك وتكليفك بالصف أو حالة حسابك. تواصل مع دعم كلاس هيرو هب إذا أكدت المدرسة التفاصيل وما زلت لا تستطيع استخدام الخدمة.",
        },
        {
          title: "النسخ أو التصحيح أو الحذف",
          text: "صف السجل والنتيجة التي تطلبها. قد يلزم التحقق من الهوية والصلاحية. وقد يلزم الاحتفاظ ببعض المعلومات لأسباب تتعلق بتاريخ المدرسة أو السلامة أو النسخ الاحتياطي أو الالتزامات المعمول بها.",
        },
        {
          title: "حسابات Family Hero Hub",
          text: "استخدم دعم Family Hero Hub لأسئلة حساب ولي الأمر أو مقدم الرعاية أو لوحة الطفل أو الجهاز المرتبط. وتبقى المدرسة جهة الاتصال المناسبة بشأن المعلومات المدرسية المعروضة هناك.",
        },
      ],
      notice: {
        title: "اجعل الرسالة الأولى بسيطة",
        text: "اذكر اسمك ومدرستك ودورك وعنوان تواصل آمناً ونوع الطلب. لا ترسل كلمات المرور أو روابط الدخول أو ملفات الطلبة الكاملة أو الرسائل الخاصة أو إجابات الاستبيانات أو مواد حماية الطلبة عبر البريد.",
      },
      cta: {
        heading: "لست متأكداً من نقطة البداية؟",
        text: "أرسل ملخصاً قصيراً وغير حساس وسيساعدك الدعم على تحديد الطريق المناسب.",
        label: "راسل كلاس هيرو هب",
        href: supportEmailHref,
        secondaryLabel: "سياسة الخصوصية",
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
