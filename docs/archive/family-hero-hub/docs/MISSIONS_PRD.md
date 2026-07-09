> Historical note: This document was inherited from Family Hero Hub and is preserved as historical context for the Class Hero Hub fork. It may describe old domains, paths, product assumptions, or infrastructure that are not current.

# Product Requirements Document (PRD): Missions

## Overview
Missions are positive challenges assigned by parents to one or more children. They are designed to encourage positive habits, teamwork, and longer-term goals.

## Goals
- Provide a structured way for parents to set goals for children.
- Motivate children through rewards and a sense of accomplishment.
- Automated reward distribution upon successful completion and approval.

## Requirements

### Parent Capabilities
- **Creation:** Create a mission with Title, Description, and Reward Points.
- **Assignment:** Assign a mission to one or multiple children.
- **Scheduling:** Optional due date/time.
- **Review:** Approve or reject completion requests from children.

### Child Capabilities
- **Discovery:** View a list of active missions assigned to them.
- **Submission:** Mark a mission as complete (triggers a request to parent).
- **History:** View completed missions.

### Automation & Logic
- **Rewards:** Approved missions must automatically create a `ledger_transactions` entry for the reward amount for each child involved.
- **Status Tracking:** Missions should have statuses: `active`, `pending_approval`, `completed`, `expired`.

## User Stories
1. *As a parent*, I want to set a "No Tech Tuesday" mission for both my kids so they play together.
2. *As a child*, I want to see how many points I will get for finishing my "Clean the Garage" mission.
3. *As a parent*, I want to be notified when a mission is marked as complete so I can check it and award the points.

## Success Metrics
- Number of missions created per week.
- Completion rate of missions.
- Time from completion request to parent approval.
