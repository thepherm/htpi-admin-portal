# HTPI Admin Portal

A lightweight Socket.IO-based admin portal for the HTPI healthcare platform.

## Architecture

```
[Admin Portal (Browser)]
         |
    Socket.IO
         |
[Gateway Service]
         |
       NATS
         |
[Microservices]
```

## Features

- Pure client-side application (no backend)
- All communication via Socket.IO to the Gateway Service
- Real-time updates for all data changes
- JWT-based authentication
- Responsive design with Tailwind CSS

## Local Development

```bash
npm install
npm run dev
```

Then open http://localhost:3001

## Configuration

The portal automatically connects to:
- Local development: `http://localhost:3000` (Gateway Service)
- Production: `https://htpi-gateway-service.railway.app`

## Socket.IO Events

### Authentication
- `admin:login` - Login with email/password
- Response includes JWT token

### Admin Operations
- `admin:stats:get` - Get dashboard statistics
- `admin:organizations:list` - List organizations
- `admin:organizations:create` - Create new organization
- `admin:organizations:get` - Get organization details
- `admin:users:list` - List admin users
- `admin:services:status` - Get service health status

### Real-time Events
- `organization_created` - New organization created
- `organization_updated` - Organization updated
- `stats_updated` - Dashboard stats updated

## Deployment

The portal is deployed as a static site on Railway and connects to the Gateway Service via WebSocket.