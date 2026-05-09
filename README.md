# Family Hero Hub

Gamified family management system designed to build positive habits in children using points, rewards, and real-world incentives.

---

## 🚀 Overview

Family Hero Hub allows parents to:

- Track behaviour using points
- Create meaningful rewards
- Encourage consistency and responsibility
- Manage child calendar events, tasks, and rewardable tasks
- Configure school books/classes for each child by weekday

Children can:

- Earn points for positive behaviour
- View their progress on a kid-friendly dashboard
- Request rewards
- See today's tasks/events and school bag reminders
- Use their own device via QR login (no email required)

---

## 🌐 Live App

https://familyherohub.com

---

## 🧪 Dev/Test Environment

Development and testing run at https://dev.familyherohub.com on the Europe/France VPS.

Production remains at https://familyherohub.com on the US VPS.

## 🧭 Infrastructure Notes

- Production: US server only
- Dev and Hermes: Europe/France server (`dev.familyherohub.com`)
- Private site mesh: `10.250.50.0/24`
- Workflow: test in Europe, then commit/push there; US production pulls tested commits only

---

## 🔑 Core Features

### 👨‍👩‍👧‍👦 Parent System
- Google OAuth login
- Family-based account system
- Multiple children per family
- Mobile-first parent launcher with children first, House Points / Reward Requests summaries, and grouped Parent Tools
- Parent Tools access for rewards, family settings, behaviour presets, calendar, pending requests, adding children, and child device linking
- Behaviour presets (quick point assignment)
- Positive, negative, and custom one-off point actions
- Reward creation with custom point values
- Reward approval workflow
- Registration request approval flow
- Admin user and family access management

---

### 👶 Child System
- Child profiles linked to parent accounts
- QR-based device linking (no email required)
- Persistent child sessions (no shared parent login)
- Kid-friendly dashboard UI with mobile-safe reward, points log, My Day, and School Bag sections
- Reward request system

---

### 🎯 Rewards System
- Fully separate from behaviour presets
- Parent-defined rewards (e.g. "Happy Meal – 20 points")
- Children can request rewards
- Parents approve or reject requests

---

### 📅 Family Calendar
- Parent-facing calendar for child events and tasks
- Supports normal events, tasks, rewardable tasks, and simple recurrence
- Mobile-responsive week layout with compact day strip
- Child dashboard shows today's calendar tasks/events in My Day

---

### 🎒 School Bag / School Prep
- Dedicated school item storage separate from calendar events/tasks
- Parents configure books/classes per child and weekday
- Child dashboard shows Pack for tomorrow, Needed today, and Check stationery
- Today/tomorrow lookup uses the family timezone

---

### ⚡ Behaviour System
- Quick-tap behaviour presets
- Positive and negative point assignment
- Custom one-off point awards and penalties without creating presets
- Short positive/negative feedback sounds after successful point changes
- Designed for fast daily use by parents

---

### 🔐 Security Model
- Family-scoped data isolation
- Admin-only registration and access management
- Parent access can be revoked without deleting family data
- Family accounts can be suspended and restored without deleting children, rewards, points, calendar, or history
- Bootstrap admins are protected from revoke actions
- Child sessions separate from parent authentication
- QR invite tokens:
  - High entropy
  - Hashed in storage
  - Expiring and revocable
- Child accounts have restricted permissions (no admin actions)

---

## 🧱 Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** SvelteKit
- **Database:** SQLite
- **Infrastructure:** Docker + Caddy (HTTPS)

---

## ⚙️ Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with:
# - Google OAuth credentials
# - Bootstrap/root-admin emails only (`PARENT_EMAILS`)
# - Database settings
