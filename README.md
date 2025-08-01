# HTPI Admin Portal

Flask-based admin portal for the HTPI healthcare platform with MVC architecture.

## Architecture

```
[Admin Portal (Flask MVC)]
         |
       NATS
         |
[Microservices]
```

## Features

- Flask MVC architecture with proper separation of concerns
- Controllers communicate directly with NATS
- Local SQLite database for caching and session management
- Server-side rendered templates with Tailwind CSS
- Secure authentication with Flask-Login
- Real-time NATS integration for all service communication

## Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Run the application
python app.py
```

Then open http://localhost:5000

## Configuration

See `.env.example` for all configuration options:
- `NATS_URL` - NATS server URL
- `NATS_USER` - NATS username
- `NATS_PASSWORD` - NATS password
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - Flask secret key

## NATS Communication

The admin portal communicates with backend services via NATS:

### Authentication
- `admin.auth.login` - Authenticate admin user
- `admin.auth.logout` - Log out admin user

### Dashboard
- `admin.stats.dashboard` - Get dashboard statistics

### Organizations
- `admin.organizations.list` - List all organizations
- `admin.organizations.create` - Create new organization
- `admin.organizations.get` - Get organization details

### Services
- `admin.services.status` - Get health status of all services

## MVC Structure

- **Models** (`models.py`) - Database models for User and Organization
- **Views** (`templates/`) - Jinja2 templates with Tailwind CSS
- **Controllers** (`controllers/`) - Request handlers that communicate with NATS
- **Services** (`services/`) - NATS client service for messaging

## Default Admin Credentials

- Email: `admin@htpi.com`
- Password: `changeme123`

## Deployment

The portal is deployed on Railway as a Flask application with Gunicorn.