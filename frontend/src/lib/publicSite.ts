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
    workflowEyebrow: string;
    workflowHeading: string;
    workflowIntro: string;
    workflow: Array<{ title: string; text: string }>;
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
      "Class Hero Hub is a shared workspace for school leaders, administrators and teachers. It brings school organisation, classroom workflows, communication, family updates and reporting into one place.",
  },
  {
    question: "Who uses Class Hero Hub?",
    answer:
      "School staff use Class Hero Hub. Each person sees the schools, classes and tools that match their responsibilities.",
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
    question: "Can we bring across records from our current system?",
    answer:
      "Yes. Class Hero Hub supports checked CSV imports for core school records. We can look at your current export format as part of a demonstration or pilot conversation.",
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
      "Staff can record positive and needs-work behaviour in the right class context. Needs-work information stays private, while positive recognition can celebrate effort without turning children into a public ranking.",
  },
  {
    question: "How are safeguarding concerns handled?",
    answer:
      "Safeguarding review has its own restricted workflow and activity history. It is kept separate from ordinary School Chats and their read or delivery status.",
  },
  {
    question: "How can our school try Class Hero Hub?",
    answer:
      "Request a conversation and tell us what you would most like to improve. We can show the relevant parts of the product and agree whether a focused pilot is the right next step.",
  },
];

const arabicFaq: FaqItem[] = [
  {
    question: "ما كلاس هيرو هب؟",
    answer:
      "كلاس هيرو هب مساحة عمل مشتركة لقادة المدارس والمسؤولين والمعلمين. تجمع تنظيم المدرسة والعمل اليومي في الصف والتواصل مع الأسر والتقارير في مكان واحد.",
  },
  {
    question: "من يستخدم كلاس هيرو هب؟",
    answer:
      "يستخدم موظفو المدرسة كلاس هيرو هب، ويرى كل شخص المدارس والصفوف والأدوات التي تناسب مسؤولياته.",
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
    question: "هل يمكننا نقل السجلات من نظامنا الحالي؟",
    answer:
      "نعم. يدعم كلاس هيرو هب استيراد السجلات المدرسية الأساسية من ملفات CSV بعد مراجعتها. ويمكننا الاطلاع على صيغة التصدير الحالية لديكم خلال العرض أو مناقشة البرنامج التجريبي.",
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
      "يمكن للموظفين تسجيل السلوك الإيجابي والسلوك الذي يحتاج إلى تحسين ضمن الصف المناسب. تبقى المعلومات التي تحتاج إلى تحسين خاصة، بينما يتيح التقدير الإيجابي الاحتفاء بالجهد من دون تحويل الأطفال إلى ترتيب علني.",
  },
  {
    question: "كيف تُعالج مخاوف حماية الطلبة؟",
    answer:
      "لمراجعة مخاوف حماية الطلبة مسار خاص بصلاحيات محدودة وسجل للإجراءات. ويظل منفصلاً عن محادثات المدرسة العادية وحالات القراءة أو التسليم.",
  },
  {
    question: "كيف يمكن لمدرستنا تجربة كلاس هيرو هب؟",
    answer:
      "اطلبوا محادثة وأخبرونا بما ترغبون في تحسينه أولاً. سنعرض الأجزاء المناسبة من المنتج ونتفق معاً إن كان برنامج تجريبي محدد هو الخطوة التالية المناسبة.",
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
      "Class Hero Hub brings school organisation, teaching workflows, communication and family updates together in one staff workspace.",
    tagline: "School life, clearly connected.",
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
    pageTitle: "Class Hero Hub | A clearer way to run the school day",
    metaDescription:
      "One connected workspace for school teams, teaching, communication, family updates and insight.",
    eyebrow: "School life, made simpler",
    heading: "Give staff one clear place to keep school life moving.",
    intro:
      "Class Hero Hub brings the everyday work of a school together, so staff spend less time switching systems and more time supporting students, colleagues and families.",
    primaryCta: "Request a pilot",
    secondaryCta: "Explore the product",
    strapline:
      "For school leaders, administrators and teachers · English and Arabic",
    schoolWorkspaceLabel: "Your school workspace",
    schoolWorkspaceTitle: "Start the day knowing what needs attention.",
    schoolWorkspaceText:
      "Keep classes, staff, learning updates, communication and reporting close at hand.",
    familyDeliveryLabel: "Family updates",
    familyDeliveryTitle: "Keep families in the picture.",
    familyDeliveryText:
      "Share the information families need through Family Hero Hub.",
    boundaryLabel: "Made for school teams",
    boundaryText:
      "Leaders, administrators and teachers see the tools that fit their work.",
    benefitsEyebrow: "Built around the school day",
    benefitsHeading: "Less chasing. Fewer gaps. A calmer way to work.",
    benefitsIntro:
      "The useful part is not having more software. It is having the right school work connected in ways people can understand.",
    benefits: [
      {
        title: "Keep the school organised",
        text: "Bring years, classes, rosters, staff and student records into a dependable shared structure.",
      },
      {
        title: "Make teacher tasks quicker",
        text: "Move from a class to homework, notices, behaviour, recognition or messages without losing context.",
      },
      {
        title: "Help families stay informed",
        text: "Send useful school information to the family experience in Family Hero Hub.",
      },
      {
        title: "See what needs attention",
        text: "Use reports, activity history and clear follow-up tools to spot patterns and respond sooner.",
      },
    ],
    workflowEyebrow: "How it works",
    workflowHeading: "Start with the essentials. Grow from there.",
    workflowIntro:
      "Set up the school once, give staff a workspace that follows their day, then share the right updates with families.",
    workflow: [
      {
        title: "Set up the school",
        text: "Bring together the academic year, classes, subjects, staff and student lists your team needs.",
      },
      {
        title: "Work from the right context",
        text: "Staff open their assigned school or class and get straight to the work in front of them.",
      },
      {
        title: "Keep families up to date",
        text: "Parents see the school information shared for their child in Family Hero Hub.",
      },
    ],
    featureEyebrow: "What schools can do",
    featureHeading: "Useful tools, connected around real school work.",
    featureIntro:
      "Choose the parts that solve a current problem. A school does not need to introduce everything at once.",
    featureGroups: [
      {
        title: "Organise the school",
        text: "Create a reliable base for the year and keep it usable as people and classes change.",
        items: [
          "Academic years, grades, classes and subjects",
          "Staff assignments and student rosters",
          "Checked CSV imports and annual updates",
          "School records and supported exports",
        ],
      },
      {
        title: "Support teaching and communication",
        text: "Give staff quicker ways to record, share and follow up from the class they are working with.",
        items: [
          "Homework, diary items and calendar events",
          "Notices, updates and school photos",
          "Positive recognition and private behaviour records",
          "School Chats, surveys and polls",
        ],
      },
      {
        title: "Lead with a clearer picture",
        text: "Help school teams understand activity, check what happened and focus their next action.",
        items: [
          "Reports and behaviour trends",
          "Delivery and read information",
          "Activity history for important actions",
          "A dedicated safeguarding review area",
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
        src: "/product/school-overview.png",
        alt: "Class Hero Hub school setup screen for a demonstration school",
        eyebrow: "School overview",
        title: "A shared view of school setup",
        text: "Administrators can see what is ready, what still needs attention and where to continue.",
      },
      {
        src: "/product/teacher-workflow.png",
        alt: "Class Hero Hub teacher screen showing demonstration classes",
        eyebrow: "Teacher workspace",
        title: "Classes and everyday actions in reach",
        text: "Teachers can move from their classes to students, notices and the calendar without hunting through menus.",
      },
    ],
    familyEyebrow: "Class Hero Hub + Family Hero Hub",
    familyHeading: "One school experience, carried through to home.",
    familyIntro:
      "School staff work in Class Hero Hub. Parents see the school information shared with them in Family Hero Hub.",
    schoolSideTitle: "1 · Staff work in Class Hero Hub",
    schoolSideText:
      "The school organises its records, teaching workflows, communication and family updates.",
    connectionTitle: "2 · The school shares an update",
    connectionText:
      "Enabled information is made available to the family linked to the student.",
    familySideTitle: "3 · Parents see it in Family Hero Hub",
    familySideText:
      "Homework, notices, calendar items, school points, surveys or chats appear alongside the family’s own tools.",
    familyBoundary:
      "Parents do not need another school app or a staff login. Their school view stays in Family Hero Hub.",
    familyCta: "See the family connection",
    trustEyebrow: "Trust in everyday use",
    trustHeading: "Thoughtful where school work needs care.",
    trustIntro:
      "Class Hero Hub is designed to help schools give people appropriate access, keep sensitive work private and understand important actions later.",
    trustItems: [
      {
        title: "Access that follows responsibility",
        text: "Staff see the schools, classes, students and tools connected to their work.",
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
    faqHeading: "Clear answers before you take the next step.",
    faqIntro:
      "Learn who uses Class Hero Hub, how families receive updates and what a pilot can look like.",
    faqCta: "Read all questions",
    finalHeading: "Could Class Hero Hub make your school day easier?",
    finalText:
      "Tell us what currently takes too much time, falls between systems or leaves families unsure. We will show you the parts that matter most.",
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
        "See how a school moves from setup to everyday staff work and family updates.",
      eyebrow: "How it works",
      heading: "A simpler route from school setup to everyday use.",
      intro:
        "Class Hero Hub starts with the school structure your team already understands, then keeps daily work and family communication connected to it.",
      highlights: [
        "Set up once",
        "Work from the class",
        "Share through Family Hero Hub",
      ],
      sections: [
        {
          title: "Bring the school together",
          text: "Create the academic year, classes, subjects and staff assignments, then add or import the student records needed for the term.",
          bullets: [
            "Review imports before they are applied",
            "Keep class and subject assignments easy to update",
          ],
        },
        {
          title: "Give staff a clear starting point",
          text: "Administrators open the area they manage. Teachers begin with their classes and move directly to students, homework, notices, behaviour, recognition, calendars or messages.",
        },
        {
          title: "Carry useful information home",
          text: "When the school shares family-facing information, parents see it in Family Hero Hub for their linked child. The school team continues to work in Class Hero Hub.",
          bullets: [
            "Families use one familiar family experience",
            "Schools decide which features to introduce",
          ],
        },
      ],
      cta: {
        heading: "See the flow with your own school in mind.",
        text: "A short demonstration can focus on the setup and workflows that matter most to your team.",
        label: "Request a demonstration",
        href: "/pilot",
        secondaryLabel: "Explore the product",
        secondaryHref: "/features",
      },
    },
    features: {
      pageTitle: "Class Hero Hub product overview",
      metaDescription:
        "Explore the school organisation, teaching, communication, reporting and family features in Class Hero Hub.",
      eyebrow: "Product overview",
      heading: "The tools schools need, without the usual maze.",
      intro:
        "Class Hero Hub connects core school work around the people, classes and moments it belongs to. Start with a focused need and add more when the school is ready.",
      highlights: [
        "School organisation",
        "Teaching and communication",
        "Family updates",
        "Reports and follow-up",
      ],
      sections: [
        {
          title: "A dependable school foundation",
          text: "Keep academic years, campuses, grades, classes, subjects, staff assignments and student rosters organised in one shared structure.",
          bullets: [
            "Checked CSV imports",
            "Annual updates and history",
            "Supported record exports",
          ],
        },
        {
          title: "Everyday teaching workflows",
          text: "Help teachers move quickly between their classes and the work they do most often.",
          bullets: [
            "Homework, diary items and required items",
            "Private behaviour records and positive recognition",
            "Notices, updates, calendars and photos",
          ],
        },
        {
          title: "Communication that has context",
          text: "Keep school communication connected to the right class or student, with clear delivery information and school contact-hour settings.",
          bullets: [
            "School Chats with text, photos and voice notes",
            "Notices, surveys and polls",
            "Family delivery through Family Hero Hub",
          ],
        },
        {
          title: "Insight for better follow-up",
          text: "Use reports, trends and activity history to understand what happened, recognise progress and decide what deserves attention next.",
          bullets: [
            "Behaviour and engagement trends",
            "Operational and delivery checks",
            "A dedicated safeguarding review area",
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
      heading: "Built around the people who keep a school running.",
      intro:
        "A useful school platform should make daily work clearer for the whole team, not create another layer of administration.",
      highlights: [
        "School leaders",
        "Administrators",
        "Teachers",
        "Bilingual teams",
      ],
      sections: [
        {
          title: "For school leaders",
          text: "See how communication, behaviour, recognition and engagement are moving across the school, with enough detail to ask better questions.",
        },
        {
          title: "For administrators",
          text: "Keep school structure, rosters, staff assignments, family links and year-to-year updates organised without rebuilding the picture in separate files.",
        },
        {
          title: "For teachers",
          text: "Begin with assigned classes and keep common actions nearby, so recording and sharing useful information takes less time.",
        },
        {
          title: "For English and Arabic communities",
          text: "Use the interface in English or Arabic while keeping the school’s own names and written content exactly as entered.",
        },
      ],
      cta: {
        heading: "Show us where the school day feels fragmented.",
        text: "We will focus the conversation on the people and workflows that would benefit most.",
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
      heading:
        "School updates meet families where family life already happens.",
      intro:
        "Staff use Class Hero Hub for school work. Parents see the information the school shares for their child in Family Hero Hub.",
      highlights: [
        "One staff workspace",
        "One family experience",
        "Clear school-to-home updates",
      ],
      sections: [
        {
          title: "The school works in Class Hero Hub",
          text: "Staff organise school records, teaching workflows, communication and the information that should be shared with families.",
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
        heading: "Want to explain the connection to your school community?",
        text: "We can help your team understand what staff use, what families see and how to introduce the experience clearly.",
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
        "Tell us what is working, what takes too much effort and where you would most value a clearer experience. We will keep the next step simple and relevant.",
      highlights: [
        "A focused conversation",
        "A relevant demonstration",
        "A sensible next step",
      ],
      sections: [
        {
          title: "We understand the school",
          text: "We begin with your school context, current systems and the work you would most like to improve.",
        },
        {
          title: "We show what matters",
          text: "Your demonstration focuses on the parts of Class Hero Hub that are relevant to your team and priorities.",
        },
        {
          title: "We agree the next step",
          text: "If there is a good fit, we agree a manageable way to explore the product with the right people from your school.",
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
        "Whether you are exploring the product or already working with Class Hero Hub, start with a short note and the team will direct it to the right place.",
      highlights: ["Pilot enquiries", "School support", "Family guidance"],
      sections: [
        {
          title: "Product and pilot conversations",
          text: "Tell us about your school, your role and the workflow you would most like to improve.",
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
        text: "We will help you find the right next step without asking for sensitive information by email.",
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
        "A clear structure at the beginning makes every teacher, student, class and family workflow easier later.",
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
          title: "Introduce the workflows you need",
          text: "Set up behaviour categories, family features, communication choices and other school settings in a manageable order.",
        },
        {
          title: "Review before sharing",
          text: "Check the audience, class and timing before publishing notices, updates, calendar events or family information.",
        },
        {
          title: "Keep the picture current",
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
      heading: "Start with your classes. Keep the next action close.",
      intro:
        "Class Hero Hub is designed to keep everyday teaching work connected to the class and students you are already thinking about.",
      highlights: ["Classes", "Homework", "Recognition", "Communication"],
      sections: [
        {
          title: "Open the class you are working with",
          text: "Your teacher workspace shows assigned home-room classes and subjects, giving you a clear starting point for the day.",
        },
        {
          title: "Record and recognise in context",
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
        heading: "Need help with a teacher workflow?",
        text: "Include your school, class context and the action you were trying to complete.",
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
        "Plain-language information about access, school records, behaviour, safeguarding, family delivery and support in Class Hero Hub.",
      eyebrow: "Safety, privacy and support",
      heading: "Practical safeguards for everyday school work.",
      intro:
        "Class Hero Hub combines careful access, clear activity history and dedicated handling for sensitive school work.",
      highlights: [
        "School-specific records",
        "Private behaviour information",
        "Dedicated safeguarding review",
      ],
      sections: [
        {
          title: "Access follows school responsibilities",
          text: "People sign in as themselves and see the schools, classes, students and tools connected to their current work.",
        },
        {
          title: "School records stay with the right school",
          text: "Records and actions are tied to the relevant school, with activity history available for important administrative and staff actions.",
        },
        {
          title: "Needs-work behaviour stays private",
          text: "Class Hero Hub does not create public negative rankings or student-shaming features. Positive recognition is reviewed by school staff.",
        },
        {
          title: "Safeguarding review is separate",
          text: "Safeguarding staff use a dedicated review area. Opening a review does not make the reviewer part of an ordinary conversation or change its read status.",
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
      "يجمع كلاس هيرو هب تنظيم المدرسة والعمل التعليمي والتواصل وتحديثات الأسرة في مساحة عمل واحدة للموظفين.",
    tagline: "حياة مدرسية مترابطة بوضوح.",
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
    pageTitle: "كلاس هيرو هب | طريقة أوضح لإدارة اليوم المدرسي",
    metaDescription:
      "مساحة عمل واحدة مترابطة لفرق المدرسة والتعليم والتواصل وتحديثات الأسرة والرؤى.",
    eyebrow: "حياة مدرسية أكثر سهولة",
    heading: "مكان واحد واضح يساعد الموظفين على إبقاء المدرسة في حركة.",
    intro:
      "يجمع كلاس هيرو هب العمل اليومي في المدرسة، ليقضي الموظفون وقتاً أقل في التنقل بين الأنظمة ووقتاً أطول في دعم الطلبة والزملاء والأسر.",
    primaryCta: "اطلب برنامجاً تجريبياً",
    secondaryCta: "استكشف المنتج",
    strapline: "لقادة المدارس والمسؤولين والمعلمين · العربية والإنجليزية",
    schoolWorkspaceLabel: "مساحة عمل مدرستك",
    schoolWorkspaceTitle: "ابدأ يومك وأنت تعرف ما يحتاج إلى اهتمام.",
    schoolWorkspaceText:
      "اجعل الصفوف والموظفين وتحديثات التعلم والتواصل والتقارير في متناول يدك.",
    familyDeliveryLabel: "تحديثات الأسرة",
    familyDeliveryTitle: "أبقِ الأسر على اطلاع.",
    familyDeliveryText:
      "شارك المعلومات التي تحتاج إليها الأسر عبر Family Hero Hub.",
    boundaryLabel: "صُمم لفرق المدارس",
    boundaryText: "يرى القادة والمسؤولون والمعلمون الأدوات التي تناسب عملهم.",
    benefitsEyebrow: "مصمم حول اليوم المدرسي",
    benefitsHeading: "متابعة أقل. فجوات أقل. طريقة عمل أكثر هدوءاً.",
    benefitsIntro:
      "القيمة ليست في إضافة برنامج جديد، بل في ربط العمل المدرسي المناسب بطريقة يفهمها الجميع.",
    benefits: [
      {
        title: "حافظ على تنظيم المدرسة",
        text: "اجمع السنوات والصفوف والقوائم والموظفين وسجلات الطلبة ضمن هيكل مشترك يمكن الاعتماد عليه.",
      },
      {
        title: "سهّل مهام المعلم اليومية",
        text: "انتقل من الصف إلى الواجبات والتنبيهات والسلوك والتقدير والرسائل من دون فقدان السياق.",
      },
      {
        title: "ساعد الأسر على البقاء على اطلاع",
        text: "أرسل المعلومات المدرسية المفيدة إلى تجربة الأسرة في Family Hero Hub.",
      },
      {
        title: "اعرف ما يحتاج إلى اهتمام",
        text: "استخدم التقارير وسجل الأنشطة وأدوات المتابعة الواضحة لاكتشاف الأنماط والاستجابة مبكراً.",
      },
    ],
    workflowEyebrow: "كيف يعمل",
    workflowHeading: "ابدأ بالأساسيات، ثم توسع عندما تكون المدرسة مستعدة.",
    workflowIntro:
      "أنشئ هيكل المدرسة مرة واحدة، وامنح الموظفين مساحة تناسب يومهم، ثم شارك التحديثات المناسبة مع الأسر.",
    workflow: [
      {
        title: "جهّز المدرسة",
        text: "اجمع العام الدراسي والصفوف والمواد والموظفين وقوائم الطلبة التي يحتاج إليها فريقك.",
      },
      {
        title: "اعمل ضمن المكان المناسب",
        text: "يفتح الموظف المدرسة أو الصف المكلف به ويبدأ مباشرة بالعمل المطلوب.",
      },
      {
        title: "أبقِ الأسر على اطلاع",
        text: "يرى أولياء الأمور المعلومات التي تشاركها المدرسة عن طفلهم في Family Hero Hub.",
      },
    ],
    featureEyebrow: "ما الذي تستطيع المدارس إنجازه",
    featureHeading: "أدوات مفيدة مترابطة حول العمل المدرسي الحقيقي.",
    featureIntro:
      "اختر الأجزاء التي تحل مشكلة حالية. لا تحتاج المدرسة إلى تقديم كل شيء دفعة واحدة.",
    featureGroups: [
      {
        title: "نظّم المدرسة",
        text: "أنشئ أساساً موثوقاً للعام الدراسي وحافظ على سهولة تحديثه مع تغير الأشخاص والصفوف.",
        items: [
          "الأعوام الدراسية والصفوف والمواد",
          "تكليفات الموظفين وقوائم الطلبة",
          "استيراد ملفات CSV بعد مراجعتها والتحديثات السنوية",
          "السجلات المدرسية وعمليات التصدير المدعومة",
        ],
      },
      {
        title: "ادعم التعليم والتواصل",
        text: "امنح الموظفين طرقاً أسرع للتسجيل والمشاركة والمتابعة من الصف الذي يعملون معه.",
        items: [
          "الواجبات وعناصر المفكرة وفعاليات التقويم",
          "التنبيهات والتحديثات والصور المدرسية",
          "التقدير الإيجابي وسجلات السلوك الخاصة",
          "محادثات المدرسة والاستبيانات والتصويتات",
        ],
      },
      {
        title: "قد المدرسة بصورة أوضح",
        text: "ساعد فرق المدرسة على فهم النشاط ومراجعة ما حدث وتحديد الخطوة التالية.",
        items: [
          "التقارير واتجاهات السلوك",
          "معلومات التسليم والقراءة",
          "سجل الإجراءات المهمة",
          "مساحة مستقلة لمراجعة حماية الطلبة",
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
        src: "/product/school-overview.png",
        alt: "شاشة إعداد المدرسة في كلاس هيرو هب لمدرسة توضيحية",
        eyebrow: "نظرة عامة على المدرسة",
        title: "صورة مشتركة لإعداد المدرسة",
        text: "يرى المسؤولون ما اكتمل وما يزال يحتاج إلى اهتمام ومن أين يواصلون العمل.",
      },
      {
        src: "/product/teacher-workflow.png",
        alt: "شاشة المعلم في كلاس هيرو هب تعرض صفوفاً توضيحية",
        eyebrow: "مساحة عمل المعلم",
        title: "الصفوف والإجراءات اليومية في متناول اليد",
        text: "ينتقل المعلم من صفوفه إلى الطلبة والتنبيهات والتقويم من دون البحث بين قوائم كثيرة.",
      },
    ],
    familyEyebrow: "كلاس هيرو هب + Family Hero Hub",
    familyHeading: "تجربة مدرسية واحدة تمتد بوضوح إلى المنزل.",
    familyIntro:
      "يعمل موظفو المدرسة في كلاس هيرو هب. ويرى أولياء الأمور المعلومات التي تشاركها المدرسة معهم في Family Hero Hub.",
    schoolSideTitle: "1 · يعمل الموظفون في كلاس هيرو هب",
    schoolSideText:
      "تنظم المدرسة سجلاتها وعملها التعليمي وتواصلها وتحديثات الأسرة.",
    connectionTitle: "2 · تشارك المدرسة تحديثاً",
    connectionText: "تصبح المعلومات المفعلة متاحة للأسرة المرتبطة بالطالب.",
    familySideTitle: "3 · يراه ولي الأمر في Family Hero Hub",
    familySideText:
      "تظهر الواجبات والتنبيهات وعناصر التقويم ونقاط المدرسة والاستبيانات أو المحادثات إلى جانب أدوات الأسرة.",
    familyBoundary:
      "لا يحتاج أولياء الأمور إلى تطبيق مدرسي آخر أو بيانات دخول الموظفين. تبقى تجربتهم المدرسية داخل Family Hero Hub.",
    familyCta: "تعرّف على الربط مع الأسرة",
    trustEyebrow: "الثقة في الاستخدام اليومي",
    trustHeading: "عناية خاصة حيث يحتاج العمل المدرسي إلى ذلك.",
    trustIntro:
      "صُمم كلاس هيرو هب ليساعد المدارس على منح الوصول المناسب، والحفاظ على خصوصية العمل الحساس، وفهم الإجراءات المهمة لاحقاً.",
    trustItems: [
      {
        title: "وصول يناسب المسؤولية",
        text: "يرى الموظف المدارس والصفوف والطلبة والأدوات المرتبطة بعمله.",
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
    faqHeading: "إجابات واضحة قبل اتخاذ الخطوة التالية.",
    faqIntro:
      "تعرّف على من يستخدم كلاس هيرو هب، وكيف تصل التحديثات إلى الأسر، وكيف يمكن أن يبدأ البرنامج التجريبي.",
    faqCta: "اقرأ جميع الأسئلة",
    finalHeading: "هل يمكن لكلاس هيرو هب أن يجعل يوم مدرستك أسهل؟",
    finalText:
      "أخبرنا بما يستغرق وقتاً أطول من اللازم، أو يتشتت بين الأنظمة، أو يترك الأسر من دون صورة واضحة. سنعرض الأجزاء الأكثر فائدة لكم.",
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
        "تعرّف على انتقال المدرسة من الإعداد إلى عمل الموظفين اليومي وتحديثات الأسرة.",
      eyebrow: "كيف يعمل",
      heading: "طريق أبسط من إعداد المدرسة إلى الاستخدام اليومي.",
      intro:
        "يبدأ كلاس هيرو هب من هيكل المدرسة الذي يعرفه فريقك، ثم يربط به العمل اليومي والتواصل مع الأسر.",
      highlights: [
        "إعداد واحد",
        "العمل من الصف",
        "المشاركة عبر Family Hero Hub",
      ],
      sections: [
        {
          title: "اجمع عناصر المدرسة",
          text: "أنشئ العام الدراسي والصفوف والمواد وتكليفات الموظفين، ثم أضف أو استورد سجلات الطلبة المطلوبة للفصل الدراسي.",
          bullets: [
            "راجع الملفات قبل تطبيق الاستيراد",
            "حدّث تكليفات الصفوف والمواد بسهولة",
          ],
        },
        {
          title: "امنح الموظفين نقطة بداية واضحة",
          text: "يفتح المسؤول القسم الذي يديره. ويبدأ المعلم من صفوفه وينتقل مباشرة إلى الطلبة والواجبات والتنبيهات والسلوك والتقدير والتقويم أو الرسائل.",
        },
        {
          title: "انقل المعلومات المفيدة إلى المنزل",
          text: "عندما تشارك المدرسة معلومات موجهة للأسرة، يراها ولي الأمر في Family Hero Hub للطفل المرتبط. ويواصل فريق المدرسة عمله في كلاس هيرو هب.",
          bullets: [
            "تستخدم الأسرة تجربة واحدة مألوفة",
            "تختار المدرسة الميزات التي تبدأ بها",
          ],
        },
      ],
      cta: {
        heading: "شاهد سير العمل بما يناسب مدرستك.",
        text: "يمكن للعرض القصير أن يركز على الإعداد والعمل الأكثر أهمية لفريقك.",
        label: "اطلب عرضاً توضيحياً",
        href: "/pilot",
        secondaryLabel: "استكشف المنتج",
        secondaryHref: "/features",
      },
    },
    features: {
      pageTitle: "نظرة عامة على كلاس هيرو هب",
      metaDescription:
        "استكشف ميزات تنظيم المدرسة والتعليم والتواصل والتقارير وربط الأسرة في كلاس هيرو هب.",
      eyebrow: "نظرة عامة على المنتج",
      heading: "الأدوات التي تحتاجها المدارس، من دون متاهة الأنظمة المعتادة.",
      intro:
        "يربط كلاس هيرو هب العمل المدرسي الأساسي بالأشخاص والصفوف والمواقف التي تخصه. ابدأ بحاجة محددة ثم أضف المزيد عندما تكون المدرسة مستعدة.",
      highlights: [
        "تنظيم المدرسة",
        "التعليم والتواصل",
        "تحديثات الأسرة",
        "التقارير والمتابعة",
      ],
      sections: [
        {
          title: "أساس مدرسي يمكن الاعتماد عليه",
          text: "حافظ على تنظيم الأعوام الدراسية والفروع والصفوف والمواد وتكليفات الموظفين وقوائم الطلبة ضمن هيكل مشترك.",
          bullets: [
            "استيراد ملفات CSV بعد مراجعتها",
            "تحديثات سنوية مع حفظ السجل",
            "تصدير السجلات المدعومة",
          ],
        },
        {
          title: "عمل المعلم اليومي",
          text: "ساعد المعلمين على الانتقال بسرعة بين صفوفهم والمهام التي ينفذونها أكثر من غيرها.",
          bullets: [
            "الواجبات وعناصر المفكرة والمتطلبات",
            "سجلات السلوك الخاصة والتقدير الإيجابي",
            "التنبيهات والتحديثات والتقويم والصور",
          ],
        },
        {
          title: "تواصل يحتفظ بسياقه",
          text: "اجعل التواصل المدرسي مرتبطاً بالصف أو الطالب المناسب، مع معلومات واضحة عن التسليم وأوقات التواصل التي تحددها المدرسة.",
          bullets: [
            "محادثات مدرسية بالنص والصور والملاحظات الصوتية",
            "التنبيهات والاستبيانات والتصويتات",
            "وصول المعلومات إلى الأسرة عبر Family Hero Hub",
          ],
        },
        {
          title: "رؤية أوضح لمتابعة أفضل",
          text: "استخدم التقارير والاتجاهات وسجل الأنشطة لفهم ما حدث والاحتفاء بالتقدم وتحديد ما يستحق الاهتمام بعد ذلك.",
          bullets: [
            "اتجاهات السلوك والمشاركة",
            "فحوصات التشغيل والتسليم",
            "مساحة مستقلة لمراجعة حماية الطلبة",
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
      heading: "مصمم حول الأشخاص الذين يحافظون على سير المدرسة.",
      intro:
        "ينبغي للمنصة المدرسية المفيدة أن توضح العمل اليومي للفريق كله، لا أن تضيف طبقة جديدة من الإدارة.",
      highlights: [
        "قادة المدارس",
        "المسؤولون",
        "المعلمون",
        "الفرق ثنائية اللغة",
      ],
      sections: [
        {
          title: "لقادة المدارس",
          text: "تابع حركة التواصل والسلوك والتقدير والمشاركة في المدرسة بتفاصيل كافية لطرح أسئلة أفضل.",
        },
        {
          title: "للمسؤولين",
          text: "حافظ على تنظيم هيكل المدرسة والقوائم وتكليفات الموظفين وروابط الأسر والتحديثات السنوية من دون إعادة بناء الصورة في ملفات منفصلة.",
        },
        {
          title: "للمعلمين",
          text: "ابدأ من الصفوف المكلف بها واجعل الإجراءات المتكررة قريبة، ليستغرق تسجيل المعلومات المفيدة ومشاركتها وقتاً أقل.",
        },
        {
          title: "للمجتمعات العربية والإنجليزية",
          text: "استخدم الواجهة بالعربية أو الإنجليزية مع إبقاء أسماء المدرسة ومحتواها المكتوب كما أُدخل تماماً.",
        },
      ],
      cta: {
        heading: "أرنا أين يتشتت العمل في يومكم المدرسي.",
        text: "سنركز الحوار على الأشخاص والأعمال التي ستستفيد أكثر.",
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
      heading:
        "تصل تحديثات المدرسة إلى الأسر في المكان الذي يديرون فيه حياتهم العائلية.",
      intro:
        "يستخدم الموظفون كلاس هيرو هب للعمل المدرسي. ويرى أولياء الأمور المعلومات التي تشاركها المدرسة عن طفلهم في Family Hero Hub.",
      highlights: [
        "مساحة واحدة للموظفين",
        "تجربة واحدة للأسرة",
        "تحديثات واضحة بين المدرسة والمنزل",
      ],
      sections: [
        {
          title: "تعمل المدرسة في كلاس هيرو هب",
          text: "ينظم الموظفون سجلات المدرسة والعمل التعليمي والتواصل والمعلومات التي ينبغي مشاركتها مع الأسر.",
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
        heading: "هل تريد شرح الربط لمجتمع مدرستك؟",
        text: "يمكننا مساعدة فريقك على فهم ما يستخدمه الموظفون وما تراه الأسر وكيفية تقديم التجربة بوضوح.",
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
        "أخبرنا بما يعمل جيداً، وما يتطلب جهداً أكبر من اللازم، وأين ترغب في تجربة أوضح. سنجعل الخطوة التالية بسيطة وذات صلة.",
      highlights: ["محادثة مركزة", "عرض مناسب", "خطوة تالية معقولة"],
      sections: [
        {
          title: "نفهم المدرسة",
          text: "نبدأ بسياق مدرستك وأنظمتها الحالية والعمل الذي ترغب في تحسينه أولاً.",
        },
        {
          title: "نعرض ما يهم",
          text: "يركز العرض على أجزاء كلاس هيرو هب المرتبطة بفريقك وأولوياتك.",
        },
        {
          title: "نتفق على الخطوة التالية",
          text: "إذا كان المنتج مناسباً، نتفق على طريقة عملية لاستكشافه مع الأشخاص المناسبين في المدرسة.",
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
        "سواء كنت تستكشف المنتج أو تعمل حالياً مع كلاس هيرو هب، ابدأ برسالة قصيرة وسيوجهها الفريق إلى المكان المناسب.",
      highlights: ["البرامج التجريبية", "دعم المدارس", "إرشاد الأسر"],
      sections: [
        {
          title: "محادثات المنتج والبرامج التجريبية",
          text: "أخبرنا عن مدرستك ودورك والعمل الذي ترغب في تحسينه أكثر من غيره.",
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
        text: "سنساعدك على إيجاد الخطوة التالية من دون طلب معلومات حساسة عبر البريد.",
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
        "يسهّل الهيكل الواضح منذ البداية كل ما يأتي لاحقاً للمعلم والطالب والصف والأسرة.",
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
          title: "قدم الأعمال التي تحتاجها المدرسة",
          text: "جهّز فئات السلوك وميزات الأسرة وخيارات التواصل وإعدادات المدرسة الأخرى بترتيب عملي.",
        },
        {
          title: "راجع قبل المشاركة",
          text: "تحقق من الجمهور والصف والتوقيت قبل نشر التنبيهات أو التحديثات أو فعاليات التقويم أو معلومات الأسرة.",
        },
        {
          title: "حافظ على حداثة الصورة",
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
      heading: "ابدأ بصفوفك واجعل الخطوة التالية قريبة.",
      intro:
        "صُمم كلاس هيرو هب ليبقي العمل التعليمي اليومي مرتبطاً بالصف والطلبة الذين تعمل معهم بالفعل.",
      highlights: ["الصفوف", "الواجبات", "التقدير", "التواصل"],
      sections: [
        {
          title: "افتح الصف الذي تعمل معه",
          text: "تعرض مساحة المعلم صفوفه الأساسية ومواده المكلف بها، لتمنحه نقطة بداية واضحة لليوم.",
        },
        {
          title: "سجل وقدّر ضمن السياق",
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
        heading: "هل تحتاج إلى مساعدة في عمل المعلم؟",
        text: "اذكر مدرستك وسياق الصف والإجراء الذي كنت تحاول إكماله.",
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
        "معلومات مبسطة عن الوصول وسجلات المدرسة والسلوك وحماية الطلبة ووصول المعلومات إلى الأسرة والدعم في كلاس هيرو هب.",
      eyebrow: "السلامة والخصوصية والدعم",
      heading: "وسائل عملية لحماية العمل المدرسي اليومي.",
      intro:
        "يجمع كلاس هيرو هب بين الوصول المدروس وسجل الإجراءات الواضح والمعالجة المخصصة للعمل المدرسي الحساس.",
      highlights: [
        "سجلات خاصة بكل مدرسة",
        "معلومات سلوك خاصة",
        "مراجعة مخصصة لحماية الطلبة",
      ],
      sections: [
        {
          title: "يتناسب الوصول مع مسؤوليات المدرسة",
          text: "يسجل كل شخص الدخول بحسابه ويرى المدارس والصفوف والطلبة والأدوات المرتبطة بعمله الحالي.",
        },
        {
          title: "تبقى سجلات المدرسة مع المدرسة المعنية",
          text: "ترتبط السجلات والإجراءات بالمدرسة المناسبة، مع توفر سجل للأنشطة الإدارية والمهنية المهمة.",
        },
        {
          title: "يبقى السلوك الذي يحتاج إلى تحسين خاصاً",
          text: "لا ينشئ كلاس هيرو هب ترتيبات سلبية علنية أو أدوات لإحراج الطلبة. ويراجع موظفو المدرسة التقدير الإيجابي.",
        },
        {
          title: "مراجعة حماية الطلبة مستقلة",
          text: "يستخدم موظفو حماية الطلبة مساحة مراجعة مخصصة. ولا يجعل فتح المراجعة صاحبها جزءاً من محادثة عادية ولا يغير حالة قراءتها.",
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
