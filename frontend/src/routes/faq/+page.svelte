<script lang="ts">
  import { _ } from 'svelte-i18n';
  import {
    Backpack,
    ChevronRight,
    Coins,
    HelpCircle,
    ShieldCheck,
    Sparkles,
    Star,
    Users
  } from 'lucide-svelte';

  type FaqItem = {
    question: string;
    answer: string;
  };

  type FaqSection = {
    id: string;
    label: string;
    icon: typeof Sparkles;
    description: string;
    items: FaqItem[];
  };

  const faqSections: FaqSection[] = [
    {
      id: 'getting-started',
      label: 'faq.sectionGettingStartedLabel',
      icon: Sparkles,
      description: 'faq.sectionGettingStartedDescription',
      items: [
        {
          question: 'faq.gettingStartedQuestion1',
          answer: 'faq.gettingStartedAnswer1'
        },
        {
          question: 'faq.gettingStartedQuestion2',
          answer: 'faq.gettingStartedAnswer2'
        },
        {
          question: 'faq.gettingStartedQuestion3',
          answer: 'faq.gettingStartedAnswer3'
        },
        {
          question: 'faq.gettingStartedQuestion4',
          answer: 'faq.gettingStartedAnswer4'
        },
        {
          question: 'faq.gettingStartedQuestion5',
          answer: 'faq.gettingStartedAnswer5'
        },
        {
          question: 'faq.gettingStartedQuestion6',
          answer: 'faq.gettingStartedAnswer6'
        }
      ]
    },
    {
      id: 'points-rewards',
      label: 'faq.sectionPointsRewardsLabel',
      icon: Coins,
      description: 'faq.sectionPointsRewardsDescription',
      items: [
        {
          question: 'faq.pointsRewardsQuestion1',
          answer: 'faq.pointsRewardsAnswer1'
        },
        {
          question: 'faq.pointsRewardsQuestion2',
          answer: 'faq.pointsRewardsAnswer2'
        },
        {
          question: 'faq.pointsRewardsQuestion3',
          answer: 'faq.pointsRewardsAnswer3'
        },
        {
          question: 'faq.pointsRewardsQuestion4',
          answer: 'faq.pointsRewardsAnswer4'
        },
        {
          question: 'faq.pointsRewardsQuestion5',
          answer: 'faq.pointsRewardsAnswer5'
        },
        {
          question: 'faq.pointsRewardsQuestion6',
          answer: 'faq.pointsRewardsAnswer6'
        },
        {
          question: 'faq.pointsRewardsQuestion7',
          answer: 'faq.pointsRewardsAnswer7'
        }
      ]
    },
    {
      id: 'savings-allowance',
      label: 'faq.sectionSavingsAllowanceLabel',
      icon: Star,
      description: 'faq.sectionSavingsAllowanceDescription',
      items: [
        {
          question: 'faq.savingsAllowanceQuestion1',
          answer: 'faq.savingsAllowanceAnswer1'
        },
        {
          question: 'faq.savingsAllowanceQuestion2',
          answer: 'faq.savingsAllowanceAnswer2'
        },
        {
          question: 'faq.savingsAllowanceQuestion3',
          answer: 'faq.savingsAllowanceAnswer3'
        },
        {
          question: 'faq.savingsAllowanceQuestion4',
          answer: 'faq.savingsAllowanceAnswer4'
        },
        {
          question: 'faq.savingsAllowanceQuestion5',
          answer: 'faq.savingsAllowanceAnswer5'
        },
        {
          question: 'faq.savingsAllowanceQuestion6',
          answer: 'faq.savingsAllowanceAnswer6'
        },
        {
          question: 'faq.savingsAllowanceQuestion7',
          answer: 'faq.savingsAllowanceAnswer7'
        }
      ]
    },
    {
      id: 'child-devices',
      label: 'faq.sectionChildDevicesLabel',
      icon: Backpack,
      description: 'faq.sectionChildDevicesDescription',
      items: [
        {
          question: 'Can my child use their own device?',
          answer: 'Yes. Parents can link a child dashboard to a child device.'
        },
        {
          question: 'How do linked child devices work?',
          answer: "A parent links a child dashboard to a device. That device then opens the child's own view of points, rewards, tasks, School Bag items, and progress."
        },
        {
          question: 'Can I unlink a child device?',
          answer: 'Yes. Parents can unlink a specific child device. This signs that device out without deleting the child profile or history.'
        },
        {
          question: 'What can children see?',
          answer: 'Children can see their own points, rewards, tasks, School Bag items, savings progress, and daily routines from a child-friendly dashboard.'
        },
        {
          question: 'Can children message each other?',
          answer: 'No. Family Hero Hub does not include child-to-child messaging.'
        }
      ]
    },
    {
      id: 'parents-caregivers',
      label: 'faq.sectionParentsCaregiversLabel',
      icon: Users,
      description: 'faq.sectionParentsCaregiversDescription',
      items: [
        {
          question: 'Can I invite another parent or caregiver?',
          answer: 'Yes. Parents & Caregivers lets families invite trusted grownups and remove access when needed.'
        },
        {
          question: 'Can I remove a caregiver?',
          answer: 'Yes, where the family access rules allow it. Removing a grownup removes their family access without deleting children, points, rewards, school bag items, calendar items, savings, allowance settings, or history.'
        },
        {
          question: 'Who controls family settings?',
          answer: 'Parents control family setup, points, rewards, caregiver access, and linked child devices.'
        }
      ]
    },
    {
      id: 'privacy-safety',
      label: 'faq.sectionPrivacySafetyLabel',
      icon: ShieldCheck,
      description: 'faq.sectionPrivacySafetyDescription',
      items: [
        {
          question: 'Is my family information private?',
          answer: 'Family Hero Hub is designed as a private, parent-led family space. Parents control the family setup and children only see their own linked dashboard.'
        },
        {
          question: 'Are there public child profiles?',
          answer: 'No. Family Hero Hub does not have public child profiles.'
        },
        {
          question: 'Is there a social feed?',
          answer: 'No. Family Hero Hub is a private family space, not a social network.'
        },
        {
          question: 'Are there ads for children?',
          answer: 'No. Family Hero Hub is not built around advertising to children.'
        },
        {
          question: 'How does Google sign-in work?',
          answer: 'Parents sign in with Google. Google handles the secure sign-in screen, and Family Hero Hub does not ask for the Google password.'
        },
        {
          question: 'What happens if I use a shared device?',
          answer: 'Parent sessions stay signed in for convenience. Always log out on shared devices or any device you do not control.'
        },
        {
          question: 'Does Family Hero Hub replace parenting decisions?',
          answer: 'No. Family Hero Hub helps organise routines, rewards, and expectations. Parents still decide what matters, what is fair, and how rewards work in real life.'
        }
      ]
    }
  ];

  const jumpLinks = faqSections.map((section) => ({
    href: `#${section.id}`,
    label: section.label
  }));
</script>

<svelte:head>
  <title>FAQ | Family Hero Hub</title>
</svelte:head>

<div class="relative overflow-hidden bg-hero-pattern">
  <section class="px-3 sm:px-4 py-10 sm:py-14 lg:py-16">
    <div class="max-w-7xl mx-auto">
      <div class="grid lg:grid-cols-[1.1fr_0.9fr] gap-6 sm:gap-8 items-stretch">
        <div class="card p-6 sm:p-8 lg:p-10 relative overflow-hidden">
          <div class="relative z-10">
            <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-hero/10 text-hero text-sm font-black mb-6 border border-hero/20">
              <HelpCircle size={16} />
              <span class="uppercase tracking-[0.14em]">{$_('faq.heroEyebrow')}</span>
            </div>

            <h1 class="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 leading-[0.95] mb-5">
              {$_('faq.heroHeading')}
            </h1>

            <p class="text-lg sm:text-xl text-slate-600 leading-relaxed max-w-2xl">
              {$_('faq.heroIntro')}
            </p>

            <div class="mt-8 flex flex-wrap gap-3">
              <a href="/login" class="btn-hero inline-flex items-center gap-2 px-5 py-4 rounded-2xl">
                {$_('faq.heroLoginCta')} <ChevronRight size={18} />
              </a>
              <a href="/request-access" class="btn-secondary inline-flex items-center gap-2 px-5 py-4 rounded-2xl">
                {$_('faq.heroRequestAccessCta')} <ChevronRight size={18} />
              </a>
            </div>

            <p class="mt-6 text-xs font-black uppercase tracking-[0.2em] text-slate-400">{$_('faq.heroLastReviewed')}</p>
          </div>
        </div>

        <div class="card p-6 sm:p-8 lg:p-10 !bg-slate-900 text-white relative overflow-hidden">
          <div class="relative z-10">
            <h2 class="text-2xl sm:text-3xl font-black mb-4">{$_('faq.jumpHeading')}</h2>
            <p class="text-slate-300 leading-relaxed mb-6">
              {$_('faq.jumpIntro')}
            </p>

            <div class="flex flex-wrap gap-3">
              {#each jumpLinks as link}
                <a
                  href={link.href}
                  class="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-bold text-white hover:bg-white/10 transition-colors"
                >
                  {$_(link.label)}
                </a>
              {/each}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="px-3 sm:px-4 pb-12 sm:pb-16 lg:pb-20">
    <div class="max-w-7xl mx-auto space-y-6 sm:space-y-8">
      {#each faqSections as section, index}
        {@const SectionIcon = section.icon}
        <section id={section.id} class="card p-5 sm:p-6 lg:p-8 scroll-mt-28">
          <div class="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-5 mb-6">
            <div class={`w-14 h-14 sm:w-16 sm:h-16 rounded-3xl flex items-center justify-center shrink-0 shadow-lg ${
              index % 3 === 0 ? 'bg-hero/10 text-hero shadow-hero/10' : index % 3 === 1 ? 'bg-savings/10 text-savings shadow-savings/10' : 'bg-reward/10 text-reward shadow-reward/10'
            }`}>
              <SectionIcon size={28} />
            </div>
            <div class="min-w-0">
              <h2 class="text-2xl sm:text-3xl font-black text-slate-900">{$_(section.label)}</h2>
              <p class="text-slate-600 mt-1 leading-relaxed max-w-3xl">{$_(section.description)}</p>
            </div>
          </div>

          <div class="grid gap-4 sm:gap-5">
            {#each section.items as item}
              <div class="rounded-3xl border border-slate-200 bg-slate-50/80 p-4 sm:p-5 shadow-sm">
                <h3 class="text-base sm:text-lg font-black text-slate-900 leading-snug">{item.question.startsWith('faq.') ? $_(item.question) : item.question}</h3>
                <p class="mt-2 text-sm sm:text-base text-slate-600 leading-relaxed">{item.answer.startsWith('faq.') ? $_(item.answer) : item.answer}</p>
              </div>
            {/each}
          </div>
        </section>
      {/each}
    </div>
  </section>
</div>
