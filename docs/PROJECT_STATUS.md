# Project Status: Family Hero Hub

**Date:** May 2, 2026
**Status:** Active Development (Phase: Core Features)

## Project Overview
Family Hero Hub is a parent/kids rewards, responsibility, allowance, chores, and gamified behaviour app. It aims to be the "family command center" where household responsibility feels like a shared adventure.

## Tech Stack
- **Frontend:** SvelteKit (TypeScript, TailwindCSS)
- **Backend:** FastAPI (Python)
- **Database:** SQLite
- **Infrastructure:** Docker Compose
- **Deployment:** Custom deploy script (`/usr/local/bin/family-hero-deploy`)
- **Gateway:** Hermes/Zeus Telegram gateway

## Current Database Schema (SQLite)
**Location:** `/opt/apps/family-hero-hub/data/family_hero_hub.sqlite`

### Tables
- `parent_users`: Parent account information.
- `children`: Child profiles linked to parents.
- `ledger_transactions`: The source of truth for all point movements.
  - `id`, `child_id`, `jar`, `transaction_type`, `points`, `description`, `locked_until`, `created_by_parent_id`, `created_at`
- `redemption_requests`: Tracks child requests to spend points.
- `pet_progress`: Data for the gamified avatar/pet system.

## Recently Completed Work
1.  **Logo & Branding:**
    - Logo asset integrated at `/opt/apps/family-hero-hub/frontend/static/family-hero-hub-logo.png`.
    - Branding applied to header, footer, and login page.
2.  **Footer Update:**
    - Tagline updated to: "Empowering the next generation with the responsibility they need to thrive."
3.  **Point Summary & Recent Activity:**
    - Period filtering (Day/Week/Month) added to child ledger.
    - Summary cards implemented (gained, lost, spent, net, saved, etc.).
    - Backend endpoints extended and verified with tests.
4.  **Redemption Logic Decision:**
    - Option B selected: `redemption_hold` is the single deduction. Approval updates status only to avoid double-counting.

## Known Configuration
- **App Path:** `/opt/apps/family-hero-hub`
- **Server User:** `administrator`
- **GitHub:** `https://github.com/itsdominoman/family-hero-hub`
