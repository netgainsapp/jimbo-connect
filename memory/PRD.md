# Jimbo Connect - Product Requirements Document

## Original Problem Statement
Build a post-event connection platform for high-value networking that allows attendees to:
- View all participants from a specific event
- Quickly identify who they met and who they missed
- Search and filter by profession, needs, and interests
- Save contacts and add private notes for follow-up
- Instantly copy contact information for outreach

## User Personas
1. **Event Host (Admin)** - Creates and manages networking events, generates invite codes
2. **Event Attendee (User)** - Joins events, browses attendees, saves contacts, takes notes

## Core Requirements
- JWT-based authentication with httpOnly cookies
- Admin panel for event creation and management
- Full profile with photo upload (via Emergent object storage)
- Event-based attendee directory with search/filter
- Save/bookmark contacts with private notes
- Copy contact info for follow-up

## What's Been Implemented (Jan 2026)

### Backend (FastAPI + MongoDB)
- ✅ JWT auth with brute force protection
- ✅ User registration, login, logout, token refresh
- ✅ Password reset flow (logged to console)
- ✅ Profile CRUD with all fields
- ✅ Photo upload via Emergent object storage
- ✅ Event CRUD (admin only)
- ✅ Event join via unique code
- ✅ Attendee directory with search/filter
- ✅ Save/unsave contacts
- ✅ Private notes per contact
- ✅ Admin stats dashboard

### Frontend (React + Tailwind + Shadcn)
- ✅ Landing page with luxury dark theme
- ✅ Login/Register pages
- ✅ Admin dashboard with stats and event management
- ✅ My Events page with join dialog
- ✅ Event directory with search, industry filter, table filter
- ✅ Attendee cards with save, copy email buttons
- ✅ User profile page with full details
- ✅ Saved contacts page with notes
- ✅ Profile edit page with photo upload

## Design System
- Theme: "Jewel & Luxury" dark theme
- Colors: Midnight Blue (#0A0D14) + Champagne Gold (#D4AF37)
- Typography: Playfair Display (headings), Outfit (body)
- Icons: Phosphor Icons (Duotone weight)

## Test Credentials
- Admin: admin@jimboconnect.com / admin123

## Prioritized Backlog

### P0 (Done)
- ✅ Core auth flow
- ✅ Event creation/management
- ✅ Attendee directory
- ✅ Contact saving/notes

### P1 (Future)
- Email notifications for password reset
- Event invitation via email
- Export contacts to CSV
- Profile photo cropping

### P2 (Future)
- Analytics dashboard for hosts
- Premium features (advanced filters)
- Email reminders for follow-up
- Integration with LinkedIn

## Next Tasks
1. Add email service for password reset and invitations
2. Implement event analytics for hosts
3. Add contact export functionality
4. Consider premium tier features
