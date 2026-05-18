<script lang="ts">
  import { CalendarDays, ChevronRight, Coins, HeartHandshake, HelpCircle, ShieldCheck, Sparkles, Star, Users } from 'lucide-svelte';

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
      label: 'Getting started',
      icon: Sparkles,
      description: 'Quick answers for parents who are new to Family Hero Hub.',
      items: [
        {
          question: 'What is Family Hero Hub?',
          answer: 'Family Hero Hub helps families track points, rewards, tasks, and school reminders in one place.'
        },
        {
          question: 'Who is it for?',
          answer: 'It is for parents and guardians who manage the family setup, and for children who use their own dashboard.'
        },
        {
          question: 'How do parents sign in?',
          answer: 'Parents sign in with Continue with Google and use the Google account that belongs to the parent or guardian.'
        },
        {
          question: 'What should I do first?',
          answer: 'Sign in, check or add your child profile, create one simple reward, and link the child device.'
        },
        {
          question: 'Can I use Family Hero Hub from a phone browser?',
          answer: 'Yes. Open it in your phone browser and use the same website.'
        },
        {
          question: 'What if my access has not been approved yet?',
          answer: 'Choose Request Access and submit your details. If you already requested access, wait for approval and try signing in again later.'
        }
      ]
    },
    {
      id: 'parent-access',
      label: 'Parent accounts and access',
      icon: ShieldCheck,
      description: 'How parent sign-in works and what approval means.',
      items: [
        {
          question: 'Why do I sign in with Google?',
          answer: 'Family Hero Hub uses Google to confirm who you are.'
        },
        {
          question: 'Do I type my Google password into Family Hero Hub?',
          answer: 'No. Google handles the secure sign-in screen, and Family Hero Hub only receives the sign-in result.'
        },
        {
          question: 'What does Request Access mean?',
          answer: 'It means your account is waiting to be approved before you can use the app.'
        },
        {
          question: 'Can another parent use the app too?',
          answer: 'Yes, if they have access to the family account and sign in with their own approved Google account.'
        },
        {
          question: 'Can children spend points without parent approval?',
          answer: 'No. Children can ask for rewards, but a parent still has to approve the request.'
        }
      ]
    },
    {
      id: 'children-devices',
      label: 'Children and child devices',
      icon: Users,
      description: 'How children open the dashboard and stay connected.',
      items: [
        {
          question: 'How do I add or check a child profile?',
          answer: 'Use the Children area on the parent dashboard to add a child or review an existing child card.'
        },
        {
          question: 'How does a child open their dashboard?',
          answer: 'The parent gives the child a link or QR code. The child opens it on their device and goes to their dashboard.'
        },
        {
          question: 'What is a child dashboard link?',
          answer: 'It is the link or QR code that opens the child dashboard on a child’s device.'
        },
        {
          question: 'What should I do if the child link expires?',
          answer: 'Generate a fresh child dashboard link from the parent dashboard and open the new one on the child device.'
        },
        {
          question: 'Does my child need a Google account?',
          answer: 'No. The child opens the dashboard with the link or QR code your parent provides.'
        }
      ]
    },
    {
      id: 'points-balances',
      label: 'Points and balances',
      icon: Coins,
      description: 'What points mean and why balances change.',
      items: [
        {
          question: 'What are points?',
          answer: 'Points are the family score children earn, save, use for rewards, or lose.'
        },
        {
          question: 'What are available points?',
          answer: 'It is the amount a child can use right now for rewards.'
        },
        {
          question: 'What is the saved balance?',
          answer: 'It is points set aside for later.'
        },
        {
          question: 'What are points on hold?',
          answer: 'They are points temporarily set aside while a reward request is waiting for a parent to decide. Points on hold are already removed from available points while a reward request waits for review.'
        },
        {
          question: 'What is the difference between available points, saved points, and points on hold?',
          answer: 'Available points can be used right now, saved points are set aside for later, and points on hold are waiting on a reward decision.'
        },
        {
          question: 'Why did my child’s points change?',
          answer: 'Points can change after points are added, points are removed, saved points change, or a reward request is made.'
        },
        {
          question: 'What are Add points, Remove points, and Custom actions?',
          answer: 'Add points gives points, Remove points takes points away, and Custom lets a parent enter a one-off point action.'
        }
      ]
    },
    {
      id: 'allowance',
      label: 'Allowance',
      icon: Coins,
      description: 'How allowance-linked points work when a family turns allowance on.',
      items: [
        {
          question: 'Can points be used for allowance?',
          answer: 'Yes. When allowance is enabled for a child, the child’s current points gain an allowance value and points are shown with a money equivalent beside them.'
        },
        {
          question: 'How does allowance work?',
          answer: 'You choose the allowance amount, point goal, and weekly or monthly period. The child’s current points have allowance value when allowance is enabled, and spending points reduces what is still available without rewriting earned history.'
        },
        {
          question: 'Does the app automatically pay allowance?',
          answer: 'No. Family Hero Hub does not automatically pay money.'
        },
        {
          question: 'Do reward requests reduce allowance?',
          answer: 'Yes. Reward requests, points on hold, approvals or rejections, and saved points reduce the available allowance balance while earned history stays visible.'
        },
        {
          question: 'What happens to points earned before allowance was turned on?',
          answer: 'They stay as points until allowance is enabled. When allowance is enabled, the child’s current points gain allowance value.'
        }
      ]
    },
    {
      id: 'rewards-requests',
      label: 'Rewards and requests',
      icon: HeartHandshake,
      description: 'How rewards work from setup to approval.',
      items: [
        {
          question: 'How do rewards work?',
          answer: 'Parents create rewards, and children can request them with points. When allowance is enabled, reward cards also show the money equivalent.'
        },
        {
          question: 'How do I create a reward?',
          answer: 'Open Manage Rewards, add a title, choose a point cost, and keep the reward visible if you want children to see it.'
        },
        {
          question: 'How does a child request a reward?',
          answer: 'The child opens Rewards, chooses a reward, and taps or clicks Request.'
        },
        {
          question: 'What does pending mean?',
          answer: 'Pending means the request has been sent and is waiting for a parent decision.'
        },
        {
          question: 'What happens when I approve a reward request?',
          answer: 'The reward is approved and the points stay spent for that reward.'
        },
        {
          question: 'What happens when I reject a reward request?',
          answer: 'The request is rejected and the points on hold go back to the child’s available points.'
        },
        {
          question: 'Where do I view pending requests?',
          answer: 'Use View pending requests or the reward requests area on the parent dashboard.'
        },
        {
          question: 'What does the reward requests area do?',
          answer: 'It is where you review reward requests and decide whether to approve or reject them.'
        }
      ]
    },
    {
      id: 'calendar-school',
      label: 'Calendar, School Prep, and School Bag',
      icon: CalendarDays,
      description: 'Family planning tools for tasks and school items.',
      items: [
        {
          question: 'What is the calendar for?',
          answer: 'It is for family tasks and events, including items that can reward points when completed and approved.'
        },
        {
          question: 'What is a rewardable task?',
          answer: 'A rewardable task is a calendar task that can be tied to points.'
        },
        {
          question: 'What is School Prep?',
          answer: 'School Prep is the parent view for today and tomorrow’s school items.'
        },
        {
          question: 'What is School Bag?',
          answer: 'School Bag is the child view that shows school items to remember.'
        },
        {
          question: 'What is the difference between School Prep and School Bag?',
          answer: 'School Prep is for parents. School Bag is for children.'
        },
        {
          question: 'What does “Pack for tomorrow” mean?',
          answer: 'It is a School Bag item that reminds the child to get ready for the next day.'
        },
        {
          question: 'What does “Needed today” mean?',
          answer: 'It shows school items that are needed for today.'
        },
        {
          question: 'What does “Check stationery” mean?',
          answer: 'It reminds the child to check school supplies such as pens, pencils, and other stationery.'
        },
        {
          question: 'What should I do if the wrong school items appear?',
          answer: 'Check the child, the weekday, and the school items entered in School Prep.'
        }
      ]
    },
    {
      id: 'child-dashboard',
      label: 'Child dashboard',
      icon: Star,
      description: 'What children see when they open their own page.',
      items: [
        {
          question: 'What can children see?',
          answer: 'Children can see points, rewards, My Day, School Bag, and their dragon progress if it is shown on their dashboard. When allowance is enabled, they also see the money equivalent beside their points.'
        },
        {
          question: 'What is My Day?',
          answer: 'My Day shows tasks or events for today.'
        },
        {
          question: 'What can children do with rewards?',
          answer: 'They can view available rewards and request one from their dashboard. If allowance is enabled, the reward cards show both points and allowance value.'
        },
        {
          question: 'What does the pet or dragon mean?',
          answer: 'It is a fun way to show progress as points grow.'
        },
        {
          question: 'What should a child do if they get stuck?',
          answer: 'Ask a parent or guardian for help.'
        }
      ]
    },
    {
      id: 'troubleshooting',
      label: 'Troubleshooting',
      icon: HelpCircle,
      description: 'Simple checks for the most common problems.',
      items: [
        {
          question: 'I cannot log in. What should I try?',
          answer: 'Use Continue with Google, confirm the correct Google account, and try again from the login page.'
        },
        {
          question: 'My access request is still pending. What should I do?',
          answer: 'Wait for approval, check that you used the right email, and try again later.'
        },
        {
          question: 'My child’s device will not open the dashboard. What should I try?',
          answer: 'Check the link or QR code, make sure the device has internet access, and ask for a fresh child link if needed.'
        },
        {
          question: 'A reward request is missing. What should I check?',
          answer: 'Check View pending requests, refresh the page, and confirm the child sent the request from the correct child device.'
        },
        {
          question: 'Points look wrong. What should I check?',
          answer: 'Review recent point actions, reward requests, approvals, and rejections to see what changed the balance.'
        },
        {
          question: 'A calendar item is missing. What should I check?',
          answer: 'Check the selected child, the date, and whether the item is active.'
        },
        {
          question: 'School Bag looks wrong. What should I check?',
          answer: 'Check the child, the weekday, and the school items entered in School Prep.'
        },
        {
          question: 'The page looks strange on my phone. What should I try?',
          answer: 'Refresh the page, try a different browser, or rotate your phone and try again.'
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
          <div class="absolute -top-24 -right-24 w-56 h-56 rounded-full bg-hero/10 blur-3xl"></div>
          <div class="absolute -bottom-24 -left-24 w-56 h-56 rounded-full bg-savings/10 blur-3xl"></div>

          <div class="relative z-10">
            <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-hero/10 text-hero text-sm font-black mb-6 border border-hero/20">
              <Sparkles size={16} />
              <span class="uppercase tracking-[0.14em]">Customer FAQ</span>
            </div>

            <h1 class="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter text-slate-900 leading-[0.95] mb-5">
              Clear answers for <span class="text-transparent bg-clip-text bg-gradient-to-r from-hero to-hero-dark text-hero">parents and children</span>.
            </h1>

            <p class="text-lg sm:text-xl text-slate-600 leading-relaxed max-w-2xl">
              Find quick help for sign-in, child devices, points, rewards, the calendar, and School Bag without digging through the manuals.
            </p>

            <div class="mt-8 flex flex-wrap gap-3">
              <a href="/login" class="btn-hero inline-flex items-center gap-2 px-5 py-4 rounded-2xl">
                Log in <ChevronRight size={18} />
              </a>
              <a href="/request-access" class="btn-secondary inline-flex items-center gap-2 px-5 py-4 rounded-2xl">
                Request access <ChevronRight size={18} />
              </a>
            </div>

            <p class="mt-6 text-xs font-black uppercase tracking-[0.2em] text-slate-400">Last reviewed: 2026-05-18</p>
          </div>
        </div>

        <div class="card p-6 sm:p-8 lg:p-10 !bg-slate-900 text-white relative overflow-hidden">
          <div class="absolute top-0 right-0 w-72 h-72 rounded-full bg-hero/10 blur-[120px]"></div>
          <div class="relative z-10">
            <h2 class="text-2xl sm:text-3xl font-black mb-4">Jump to a section</h2>
            <p class="text-slate-300 leading-relaxed mb-6">
              Use these quick links to move straight to the topic you need.
            </p>

            <div class="flex flex-wrap gap-3">
              {#each jumpLinks as link}
                <a
                  href={link.href}
                  class="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-bold text-white hover:bg-white/10 transition-colors"
                >
                  {link.label}
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
        <section id={section.id} class="card p-5 sm:p-6 lg:p-8 scroll-mt-28">
          <div class="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-5 mb-6">
            <div class={`w-14 h-14 sm:w-16 sm:h-16 rounded-3xl flex items-center justify-center shrink-0 shadow-lg ${
              index % 3 === 0 ? 'bg-hero/10 text-hero shadow-hero/10' : index % 3 === 1 ? 'bg-savings/10 text-savings shadow-savings/10' : 'bg-reward/10 text-reward shadow-reward/10'
            }`}>
              <svelte:component this={section.icon} size={28} />
            </div>
            <div class="min-w-0">
              <h2 class="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">{section.label}</h2>
              <p class="text-slate-600 mt-1 leading-relaxed max-w-3xl">{section.description}</p>
            </div>
          </div>

          <div class="grid gap-4 sm:gap-5">
            {#each section.items as item}
              <div class="rounded-3xl border border-slate-200 bg-slate-50/80 p-4 sm:p-5 shadow-sm">
                <h3 class="text-base sm:text-lg font-black text-slate-900 leading-snug">{item.question}</h3>
                <p class="mt-2 text-sm sm:text-base text-slate-600 leading-relaxed">{item.answer}</p>
              </div>
            {/each}
          </div>
        </section>
      {/each}
    </div>
  </section>
</div>
