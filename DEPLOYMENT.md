# HTPI Deployment Guide

## Current Issues

1. **No NATS service running** - This is why nothing is working
2. **MongoDB service can't connect to NATS** - Waiting for NATS
3. **Admin portal has no backend** - Just forwarding to non-existent NATS

## Required Services

You need to deploy ALL these services for the system to work:

### 1. NATS Message Broker (CRITICAL - Deploy First!)
```yaml
Service: nats
Image: nats:latest
Port: 4222
Command: -js  # Enable JetStream
```

### 2. MongoDB Database
```yaml
Service: mongodb
Image: mongo:latest
Port: 27017
Environment:
  MONGO_INITDB_ROOT_USERNAME: admin
  MONGO_INITDB_ROOT_PASSWORD: <secure-password>
```

### 3. HTPI Services (Deploy after NATS)

Each service needs these environment variables:
```
NATS_URL=nats://nats.railway.internal:4222
MONGODB_URL=mongodb://admin:password@mongodb.railway.internal:27017/htpi?authSource=admin
```

Services to deploy:
- **htpi-patient-service** - Handles patient CRUD
- **htpi-insurance-service** - Handles insurance/eligibility
- **htpi-claims-service** - Handles claims/ClaimMD
- **htpi-encounters-service** - Handles encounters
- **htpi-tenant-service** - Handles multi-tenancy
- **htpi-auth-service** - Handles authentication

## Quick Fix for Testing

Since you don't have the microservices yet, update the admin portal to work standalone:

### In app.py, add fallback mode:
```python
# At the top
STANDALONE_MODE = os.environ.get('STANDALONE_MODE', 'true').lower() == 'true'

# In each handler, check:
if STANDALONE_MODE:
    # Use mock data directly
    # Don't try to publish to NATS
else:
    # Normal NATS flow
```

## Proper Architecture Flow

```
1. Browser → Socket.IO → Admin Portal
2. Admin Portal → NATS → Microservice
3. Microservice → NATS → MongoDB Service
4. MongoDB Service → MongoDB Database
5. Response flows back the same way
```

## Environment Variables for Admin Portal

```
NATS_URL=nats://nats.railway.internal:4222
STANDALONE_MODE=false  # Set to true if no NATS/services
SECRET_KEY=<generate-secure-key>
PORT=8000
```

## Testing Without Full Stack

For now, set `STANDALONE_MODE=true` in Railway to use mock data until you deploy:
1. NATS service
2. All microservices
3. Set STANDALONE_MODE=false

This will at least let you see the UI working with fake data.