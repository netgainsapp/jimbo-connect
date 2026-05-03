# Jimbo Connect

**Post-Event Connection Platform for High-Value Networking**

---

## Overview

Jimbo Connect is a lightweight, event-based platform that helps networking event attendees stay connected after the event ends. Instead of losing valuable connections to forgotten business cards and fading memories, attendees can browse everyone from their event, save contacts, and add private notes for follow-up.

---

## Features

### For Attendees
- **Event Directory** - Browse all attendees from your events in a searchable directory
- **Smart Search & Filters** - Find people by name, company, role, industry, or table/cohort
- **Save Contacts** - Bookmark interesting people and never forget who you met
- **Private Notes** - Add personal notes to remember conversation context
- **Quick Copy** - Instantly copy email, phone, or LinkedIn for follow-up
- **Profile Management** - Create a profile with your photo, bio, and what you're looking for

### For Event Hosts (Admin)
- **Event Creation** - Create events with name, date, location, and industry tags
- **Unique Join Links** - Generate shareable codes for attendees to join
- **Attendee Management** - View all attendees and engagement stats
- **Analytics Dashboard** - Track total users, events, and connections made

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Tailwind CSS, Shadcn/UI |
| Backend | FastAPI (Python) |
| Database | MongoDB |
| Auth | JWT with httpOnly cookies |
| Storage | Emergent Object Storage (for profile photos) |

---

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- MongoDB

### Installation

**Backend:**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Configure your environment variables
python -m uvicorn server:app --reload --port 8001
```

**Frontend:**
```bash
cd frontend
yarn install
cp .env.example .env  # Set REACT_APP_BACKEND_URL
yarn start
```

### Environment Variables

**Backend (.env):**
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=jimbo_connect
JWT_SECRET=your-secret-key-here
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-admin-password
FRONTEND_URL=http://localhost:3000
```

**Frontend (.env):**
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| POST | `/api/auth/logout` | Logout user |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/forgot-password` | Request password reset |
| POST | `/api/auth/reset-password` | Reset password with token |

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profile` | Get own profile |
| PUT | `/api/profile` | Update profile |
| POST | `/api/profile/photo` | Upload profile photo |
| GET | `/api/profile/{user_id}` | Get user profile |

### Events
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/events` | Create event (admin) |
| GET | `/api/events` | List all events (admin) |
| GET | `/api/events/{id}` | Get event details |
| PUT | `/api/events/{id}` | Update event (admin) |
| DELETE | `/api/events/{id}` | Delete event (admin) |
| POST | `/api/events/join/{code}` | Join event by code |
| GET | `/api/events/{id}/attendees` | Get event attendees |
| GET | `/api/my-events` | Get user's joined events |

### Contacts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/contacts/save` | Save a contact |
| DELETE | `/api/contacts/{id}` | Remove saved contact |
| GET | `/api/contacts` | Get all saved contacts |
| PUT | `/api/contacts/{id}/note` | Update contact note |
| GET | `/api/contacts/{id}/is-saved` | Check if contact is saved |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/stats` | Get platform statistics |

---

## User Flows

### Attendee Flow
1. Receive event join link from host
2. Click link → Register/Login
3. Complete profile (name, role, company, photo, etc.)
4. Browse event directory
5. Search/filter to find relevant people
6. Save contacts and add notes
7. Copy contact info for follow-up

### Host Flow
1. Login as admin
2. Create new event with details
3. Copy join link
4. Share link with attendees
5. Monitor attendee signups
6. View engagement stats

---

## Design System

### Colors
- **Light Mode**: White background (#FFFFFF), Blue primary (#2563EB)
- **Dark Mode**: Navy background (#0F172A), Blue primary (#3B82F6)

### Typography
- **Font Family**: Calibri, Segoe UI, system fonts
- **Headings**: Semi-bold (600)
- **Body**: Regular (400)

### Components
- Built on Shadcn/UI component library
- Phosphor Icons (duotone weight)
- Responsive design (mobile-first)

---

## Deployment

The application is configured for deployment on Emergent platform:

- Backend runs on port 8001
- Frontend runs on port 3000
- All API routes prefixed with `/api`
- CORS configured for production URLs

---

## Test Credentials

For development/testing:
- **Admin**: admin@jimboconnect.com / admin123

---

## License

MIT License - See LICENSE file for details.

---

## Support

For questions or issues, contact the Jimbo Connect team.
