// HTPI Admin Portal - Socket.IO Client
let socket = null;
let authToken = null;
let currentUser = null;

// Configuration
const GATEWAY_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:3000' 
    : 'https://htpi-gateway-service.railway.app';

// Debug mode
const DEBUG = true;

// Logger utility
const logger = {
    log: (message, data = null) => {
        if (DEBUG) {
            console.log(`[HTPI Admin] ${new Date().toISOString()} - ${message}`, data || '');
        }
    },
    error: (message, error = null) => {
        console.error(`[HTPI Admin ERROR] ${new Date().toISOString()} - ${message}`, error || '');
    },
    warn: (message, data = null) => {
        if (DEBUG) {
            console.warn(`[HTPI Admin WARN] ${new Date().toISOString()} - ${message}`, data || '');
        }
    }
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    logger.log('Initializing HTPI Admin Portal');
    logger.log('Gateway URL:', GATEWAY_URL);
    
    // Check for stored auth token
    authToken = localStorage.getItem('authToken');
    if (authToken) {
        logger.log('Found stored auth token, attempting to connect');
        connectSocket();
    } else {
        logger.log('No auth token found, showing login screen');
    }
});

// Socket.IO Connection
function connectSocket() {
    logger.log('Attempting to connect to gateway with auth token');
    
    socket = io(GATEWAY_URL, {
        auth: {
            token: authToken
        },
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        logger.log('Successfully connected to gateway', {
            socketId: socket.id,
            transport: socket.io.engine.transport.name
        });
        showMainApp();
        loadDashboard();
    });

    socket.on('disconnect', (reason) => {
        logger.warn('Disconnected from gateway', { reason });
    });

    socket.on('connect_error', (error) => {
        logger.error('Connection error', {
            message: error.message,
            type: error.type,
            data: error.data
        });
    });

    socket.on('error', (error) => {
        logger.error('Socket error', error);
        if (error.type === 'auth') {
            logger.warn('Authentication error, logging out');
            logout();
        }
    });

    // Event listeners for real-time updates
    socket.on('organization_created', (data) => {
        logger.log('Organization created event received', data);
        showNotification('New organization created', 'success');
        if (currentView === 'organizations') {
            loadOrganizations();
        }
    });

    socket.on('organization_updated', (data) => {
        logger.log('Organization updated event received', data);
        showNotification('Organization updated', 'info');
        if (currentView === 'organizations') {
            loadOrganizations();
        }
    });

    socket.on('stats_updated', (data) => {
        logger.log('Stats updated event received', data);
        if (currentView === 'dashboard') {
            updateDashboardStats(data);
        }
    });
}

// Authentication
function login(event) {
    event.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    logger.log('Attempting login', { email });
    
    // Connect to socket for login
    const tempSocket = io(GATEWAY_URL, {
        transports: ['websocket', 'polling']
    });

    tempSocket.on('connect', () => {
        logger.log('Temporary socket connected for login', {
            socketId: tempSocket.id,
            transport: tempSocket.io.engine.transport.name
        });
        
        logger.log('Emitting admin:login event');
        tempSocket.emit('admin:login', { email, password }, (response) => {
            logger.log('Login response received', {
                success: response.success,
                error: response.error,
                hasToken: !!response.data?.token,
                hasUser: !!response.data?.user
            });
            
            if (response.success) {
                authToken = response.data.token;
                currentUser = response.data.user;
                localStorage.setItem('authToken', authToken);
                logger.log('Login successful, storing token and connecting main socket');
                tempSocket.disconnect();
                connectSocket();
            } else {
                logger.error('Login failed', { error: response.error });
                showLoginError(response.error || 'Invalid credentials');
            }
        });
    });

    tempSocket.on('connect_error', (error) => {
        logger.error('Cannot connect to server for login', {
            message: error.message,
            type: error.type
        });
        showLoginError('Cannot connect to server');
    });
}

function logout() {
    logger.log('Logging out user');
    if (socket) {
        socket.disconnect();
    }
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    showLoginScreen();
}

// UI Functions
function showLoginScreen() {
    document.getElementById('loginScreen').classList.remove('hidden');
    document.getElementById('mainApp').classList.add('hidden');
}

function showMainApp() {
    document.getElementById('loginScreen').classList.add('hidden');
    document.getElementById('mainApp').classList.remove('hidden');
    if (currentUser) {
        document.getElementById('userName').textContent = 
            `${currentUser.first_name} ${currentUser.last_name}`;
    }
}

function showLoginError(message) {
    const errorDiv = document.getElementById('loginError');
    const errorText = document.getElementById('loginErrorText');
    errorText.textContent = message;
    errorDiv.classList.remove('hidden');
    setTimeout(() => errorDiv.classList.add('hidden'), 5000);
}

// View Management
let currentView = 'dashboard';

function showView(viewName) {
    logger.log('Switching to view:', viewName);
    
    // Hide all views
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    
    // Show selected view
    document.getElementById(viewName + 'View').classList.remove('hidden');
    
    // Update nav
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('border-indigo-500', 'text-gray-900');
        link.classList.add('border-transparent', 'text-gray-500');
    });
    event.target.classList.remove('border-transparent', 'text-gray-500');
    event.target.classList.add('border-indigo-500', 'text-gray-900');
    
    currentView = viewName;
    
    // Load view data
    switch(viewName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'organizations':
            loadOrganizations();
            break;
        case 'users':
            loadUsers();
            break;
        case 'services':
            loadServices();
            break;
    }
}

// Dashboard
function loadDashboard() {
    logger.log('Loading dashboard stats');
    socket.emit('admin:stats:get', {}, (response) => {
        logger.log('Dashboard stats response', {
            success: response.success,
            data: response.data,
            error: response.error
        });
        if (response.success) {
            updateDashboardStats(response.data);
        } else {
            logger.error('Failed to load dashboard stats', { error: response.error });
        }
    });
}

function updateDashboardStats(stats) {
    logger.log('Updating dashboard stats', stats);
    document.getElementById('totalOrgs').textContent = stats.totalOrganizations || stats.total_organizations || 0;
    document.getElementById('activeUsers').textContent = stats.totalUsers || stats.active_users || 0;
    document.getElementById('claimsToday').textContent = stats.totalClaims || stats.claims_today || 0;
    
    const statusEl = document.getElementById('systemStatus');
    statusEl.textContent = (stats.system_health || 'Unknown').toUpperCase();
    statusEl.className = stats.system_health === 'healthy' 
        ? 'text-lg font-medium text-green-600' 
        : 'text-lg font-medium text-red-600';
}

// Organizations
function loadOrganizations() {
    logger.log('Loading organizations list');
    socket.emit('admin:organizations:list', { page: 1, limit: 20 }, (response) => {
        logger.log('Organizations response', {
            success: response.success,
            count: response.data?.organizations?.length,
            error: response.error
        });
        if (response.success) {
            displayOrganizations(response.data.organizations);
        } else {
            logger.error('Failed to load organizations', { error: response.error });
        }
    });
}

function displayOrganizations(orgs) {
    logger.log('Displaying organizations', { count: orgs.length });
    const tbody = document.getElementById('orgsTableBody');
    tbody.innerHTML = '';
    
    if (orgs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                    No organizations found.
                </td>
            </tr>
        `;
        return;
    }
    
    orgs.forEach(org => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                ${org.name}
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                ${org.type.replace('_', ' ').charAt(0).toUpperCase() + org.type.slice(1)}
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium 
                    ${org.status === 'active' ? 'bg-green-100 text-green-800' : 
                      org.status === 'suspended' ? 'bg-red-100 text-red-800' : 
                      'bg-gray-100 text-gray-800'}">
                    ${org.status.charAt(0).toUpperCase() + org.status.slice(1)}
                </span>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                ${org.current_users || 0} / ${org.max_users || '∞'}
            </td>
            <td class="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                <a href="#" onclick="viewOrganization('${org.id}')" class="text-indigo-600 hover:text-indigo-900">View</a>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Users
function loadUsers() {
    socket.emit('admin:users:list', { page: 1, limit: 20 }, (response) => {
        if (response.success) {
            displayUsers(response.data.users);
        }
    });
}

function displayUsers(users) {
    const content = document.getElementById('usersContent');
    content.innerHTML = '<div class="text-gray-500">Loading users...</div>';
    // Implementation similar to organizations
}

// Services
function loadServices() {
    logger.log('Loading services status');
    socket.emit('admin:services:status', {}, (response) => {
        logger.log('Services status response', {
            success: response.success,
            data: response.data,
            error: response.error
        });
        if (response.success) {
            displayServices(response.data);
        } else {
            logger.error('Failed to load services', { error: response.error });
        }
    });
}

function displayServices(services) {
    logger.log('Displaying services', services);
    const content = document.getElementById('servicesContent');
    content.innerHTML = '';
    
    const defaultServices = [
        { name: 'Gateway', status: 'unknown' },
        { name: 'NATS', status: 'unknown' },
        { name: 'MongoDB', status: 'unknown' },
        { name: 'Patients Service', status: 'unknown' },
        { name: 'Insurance Service', status: 'unknown' },
        { name: 'Forms Service', status: 'unknown' }
    ];
    
    const servicesMap = {};
    services.forEach(s => servicesMap[s.name] = s);
    
    defaultServices.forEach(defaultService => {
        const service = servicesMap[defaultService.name] || defaultService;
        const card = document.createElement('div');
        card.className = 'bg-white overflow-hidden shadow rounded-lg p-6';
        card.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <h3 class="text-lg font-medium text-gray-900">${service.name}</h3>
                    <p class="mt-1 text-sm text-gray-500">${service.description || 'Service'}</p>
                </div>
                <div class="flex-shrink-0">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${service.status === 'healthy' ? 'bg-green-100 text-green-800' :
                          service.status === 'degraded' ? 'bg-yellow-100 text-yellow-800' :
                          service.status === 'down' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'}">
                        ${service.status.toUpperCase()}
                    </span>
                </div>
            </div>
            ${service.last_check ? `
                <p class="mt-2 text-xs text-gray-500">
                    Last checked: ${new Date(service.last_check).toLocaleString()}
                </p>
            ` : ''}
        `;
        content.appendChild(card);
    });
}

// Utility Functions
function showNotification(message, type = 'info') {
    // Simple notification - could be enhanced with a toast library
    logger.log(`Notification: ${message}`, { type });
}

// Subscribe to updates when connected
function subscribeToUpdates() {
    socket.emit('admin:subscribe', {
        events: ['organization_updates', 'user_updates', 'system_updates']
    });
}