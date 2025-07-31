# HTPI Admin Portal

Administrative portal for managing the HTPI healthcare insurance claim processing system.

## Overview

The HTPI Admin Portal provides system administrators with comprehensive tools to:

- Manage organizations and their settings
- Monitor system health and performance
- Review audit logs and security events
- Manage admin users and permissions
- View detailed analytics and reports
- Handle billing and subscription management

## Features

- **Multi-level Admin Roles**: Super admin, org admin, billing admin, etc.
- **Real-time Dashboard**: System metrics and health monitoring
- **Organization Management**: Create, edit, suspend organizations
- **User Management**: Manage users across all organizations
- **Audit Trail**: Complete audit logging of all admin actions
- **Billing Management**: Handle plans, limits, and usage
- **System Monitoring**: Service health and performance metrics

## Tech Stack

- React 18 with TypeScript
- Material-UI v5 for UI components
- React Query for data fetching
- React Router v6 for navigation
- Recharts for data visualization
- Axios for API communication

## Prerequisites

- Node.js 16+
- npm or yarn
- HTPI Admin Service running

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/htpi-admin-portal.git
cd htpi-admin-portal
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.example .env
```

4. Update `.env` with your configuration:
```env
REACT_APP_API_URL=http://localhost:8080
```

## Development

Start the development server:
```bash
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000)

## Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build` folder.

## Default Credentials

For initial setup, use the super admin credentials configured in the admin service:
- Email: `admin@htpi.com`
- Password: `changeme123`

**Important**: Change these credentials immediately after first login!

## Admin Roles

### Super Admin
- Full system access
- Can create/manage other admins
- Access to all organizations
- System configuration

### Organization Admin
- Manage specific organizations
- User management within orgs
- View organization reports

### Billing Admin
- View/update billing information
- Handle subscriptions
- Export financial reports

### Clinical Admin
- View clinical data
- Audit healthcare operations
- Generate compliance reports

### Support Admin
- Read-only access
- Monitor system health
- Assist with troubleshooting

## Project Structure

```
src/
├── components/       # Reusable UI components
├── contexts/        # React contexts (Auth)
├── pages/           # Page components
├── services/        # API service layer
├── types/           # TypeScript type definitions
├── utils/           # Utility functions
├── App.tsx          # Main app component
└── index.tsx        # Entry point
```

## Available Pages

- **/login** - Admin authentication
- **/dashboard** - System overview and metrics
- **/organizations** - Organization management
- **/organizations/:id** - Organization details
- **/users** - User management across orgs
- **/admins** - Admin user management
- **/reports** - Analytics and reporting
- **/audit-logs** - Security audit trail
- **/system-health** - Service monitoring
- **/settings** - System configuration

## Security Features

- JWT-based authentication
- Role-based access control (RBAC)
- Audit logging of all actions
- Session management
- IP tracking
- Failed login protection

## API Integration

The portal communicates with the HTPI Admin Service for all operations:

```typescript
// Example API call
const response = await api.getOrganizations({
  status: 'active',
  limit: 50
});
```

## State Management

- **React Query**: Server state and caching
- **React Context**: Authentication state
- **Local Storage**: Auth tokens only

## Performance

- Code splitting for faster loads
- Lazy loading of routes
- Optimized re-renders
- Efficient data fetching
- Response caching

## Monitoring

The admin portal provides:
- Real-time system metrics
- Service health status
- Active user monitoring
- Claim processing stats
- Organization usage tracking

## Deployment

### Deploy to Vercel
```bash
npm install -g vercel
vercel
```

### Deploy to Netlify
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=build
```

### Deploy to Railway
```bash
railway login
railway link
railway up
```

## Environment Variables

- `REACT_APP_API_URL` - Admin service API endpoint

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Troubleshooting

### Login Issues
- Verify admin service is running
- Check API_URL configuration
- Ensure correct credentials

### Permission Errors
- Verify admin role and permissions
- Check organization access
- Review audit logs

### API Connection
- Check CORS settings
- Verify network connectivity
- Check service health

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create pull request

## License

MIT
