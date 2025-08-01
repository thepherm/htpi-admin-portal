"""
HTPI Admin Portal - Flask Application with Socket.IO Server
"""
import os
import logging
import asyncio
from datetime import timedelta
from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from functools import wraps
import nats
from nats.aio.client import Client as NATS
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.environ.get('ENV') == 'development' else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('ENV', 'development') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Enable CORS
CORS(app, supports_credentials=True)

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# NATS configuration
NATS_URL = os.environ.get('NATS_URL', 'nats://localhost:4222')
nc = None  # NATS client will be initialized on startup

# Connected clients tracking
connected_clients = {}

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))
        # Check if user is admin
        if session.get('user', {}).get('role') != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes - Only serve pages
@app.route('/')
def index():
    if 'user' in session and session['user'].get('role') == 'admin':
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if 'user' in session and session['user'].get('role') == 'admin':
        return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard/index.html', 
                         user=session.get('user'))

@app.route('/tenants')
@login_required
def tenants():
    return render_template('tenants/index.html', 
                         user=session.get('user'))

@app.route('/tenants/<tenant_id>')
@login_required
def tenant_detail(tenant_id):
    return render_template('tenants/detail.html', 
                         user=session.get('user'),
                         tenant_id=tenant_id)

@app.route('/users')
@login_required
def users():
    return render_template('users/index.html', 
                         user=session.get('user'))

@app.route('/services')
@login_required
def services():
    return render_template('services/index.html', 
                         user=session.get('user'))

# Session management endpoint
@app.route('/auth/session', methods=['POST'])
def set_session():
    try:
        data = request.get_json()
        if data.get('authenticated') and data.get('user', {}).get('role') == 'admin':
            session['user'] = data.get('user')
            session['token'] = data.get('token')
            session.permanent = True
            logger.info(f"Admin session created for user: {session['user'].get('email')}")
            return jsonify({'success': True})
        else:
            session.clear()
            return jsonify({'success': False, 'error': 'Admin access required'}), 401
    except Exception as e:
        logger.error(f"Session error: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    logger.info(f"Admin client connected: {client_id}")
    connected_clients[client_id] = {
        'sid': client_id,
        'authenticated': False
    }
    emit('connected', {'message': 'Connected to admin portal'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    logger.info(f"Admin client disconnected: {client_id}")
    if client_id in connected_clients:
        del connected_clients[client_id]

@socketio.on('auth:login')
async def handle_login(data):
    """Handle admin login authentication"""
    client_id = request.sid
    email = data.get('email')
    password = data.get('password')
    
    logger.info(f"Admin login attempt for email: {email}")
    
    try:
        # Send authentication request to auth service via NATS
        if nc and nc.is_connected:
            auth_request = {
                'email': email,
                'password': password,
                'portal': 'admin',
                'require_role': 'admin'
            }
            
            # Request-reply pattern with NATS
            response = await nc.request('auth.login', json.dumps(auth_request).encode(), timeout=5)
            auth_result = json.loads(response.data.decode())
            
            if auth_result.get('success') and auth_result.get('user', {}).get('role') == 'admin':
                user_data = auth_result.get('user')
                token = auth_result.get('token')
                
                # Update connected client info
                connected_clients[client_id]['authenticated'] = True
                connected_clients[client_id]['user'] = user_data
                connected_clients[client_id]['token'] = token
                connected_clients[client_id]['role'] = 'admin'
                
                # Join admin room
                join_room('admin')
                join_room(f"admin:{user_data['id']}")
                
                emit('auth:login:response', {
                    'success': True,
                    'user': user_data,
                    'token': token
                })
                
                logger.info(f"Admin authenticated: {email}")
            else:
                emit('auth:login:response', {
                    'success': False,
                    'error': 'Admin access required'
                })
                logger.warning(f"Non-admin login attempt for: {email}")
        else:
            logger.error("NATS not connected")
            emit('auth:login:response', {
                'success': False,
                'error': 'Authentication service unavailable'
            })
    except Exception as e:
        logger.error(f"Admin login error: {str(e)}")
        emit('auth:login:response', {
            'success': False,
            'error': 'Authentication failed'
        })

# Admin-specific Socket.IO event handlers
@socketio.on('admin:tenants:subscribe')
async def handle_tenants_subscribe():
    """Subscribe to tenant updates"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Join tenants room
        join_room('admin:tenants')
        
        # Request tenant list via NATS
        if nc and nc.is_connected:
            response = await nc.request('tenants.list_all', b'{}', timeout=5)
            tenants = json.loads(response.data.decode())
            
            emit('admin:tenants:list', tenants.get('tenants', []))
            
            logger.info(f"Admin subscribed to tenants")
    except Exception as e:
        logger.error(f"Error subscribing to tenants: {str(e)}")
        emit('error', {'message': 'Failed to load tenants'})

@socketio.on('admin:tenants:create')
async def handle_create_tenant(data):
    """Create a new tenant"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Add admin context to tenant data
        tenant_data = {
            **data,
            'created_by': client['user']['id'],
            'created_by_name': client['user']['name']
        }
        
        # Send to tenant service via NATS
        if nc and nc.is_connected:
            response = await nc.request('tenants.create', 
                                      json.dumps(tenant_data).encode(), 
                                      timeout=5)
            result = json.loads(response.data.decode())
            
            if result.get('success'):
                # Broadcast to all admins
                socketio.emit('admin:tenants:created', result['tenant'], 
                            room='admin:tenants')
                
                # Return response with request ID
                emit(f"admin:tenants:create:response:{data.get('requestId')}", {
                    'success': True,
                    'tenant': result['tenant']
                })
            else:
                emit(f"admin:tenants:create:response:{data.get('requestId')}", {
                    'success': False,
                    'error': result.get('error', 'Failed to create tenant')
                })
    except Exception as e:
        logger.error(f"Error creating tenant: {str(e)}")
        emit(f"admin:tenants:create:response:{data.get('requestId')}", {
            'success': False,
            'error': 'Failed to create tenant'
        })

@socketio.on('admin:tenant:subscribe')
async def handle_tenant_subscribe(data):
    """Subscribe to specific tenant updates"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    tenant_id = data.get('tenantId')
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Join tenant-specific admin room
        room = f"admin:tenant:{tenant_id}"
        join_room(room)
        
        # Request tenant details via NATS
        if nc and nc.is_connected:
            # Get tenant info
            tenant_response = await nc.request('tenants.get', 
                                             json.dumps({'tenant_id': tenant_id}).encode(), 
                                             timeout=5)
            tenant_data = json.loads(tenant_response.data.decode())
            
            # Get users for tenant
            users_response = await nc.request('tenants.list_users', 
                                            json.dumps({'tenant_id': tenant_id}).encode(), 
                                            timeout=5)
            users_data = json.loads(users_response.data.decode())
            
            # Get ClaimMD accounts
            claimmd_response = await nc.request('tenants.list_claimmd', 
                                              json.dumps({'tenant_id': tenant_id}).encode(), 
                                              timeout=5)
            claimmd_data = json.loads(claimmd_response.data.decode())
            
            emit('admin:tenant:data', {
                'tenant': tenant_data.get('tenant'),
                'users': users_data.get('users', []),
                'claimMDAccounts': claimmd_data.get('accounts', [])
            })
            
            logger.info(f"Admin subscribed to tenant {tenant_id}")
    except Exception as e:
        logger.error(f"Error subscribing to tenant: {str(e)}")
        emit('error', {'message': 'Failed to load tenant data'})

@socketio.on('admin:tenant:user:add')
async def handle_add_user_to_tenant(data):
    """Add user to tenant"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Send to service via NATS
        if nc and nc.is_connected:
            request_data = {
                **data,
                'admin_id': client['user']['id']
            }
            
            response = await nc.request('tenants.add_user', 
                                      json.dumps(request_data).encode(), 
                                      timeout=5)
            result = json.loads(response.data.decode())
            
            if result.get('success'):
                # Broadcast to admins watching this tenant
                socketio.emit('admin:tenant:user:added', result['user'], 
                            room=f"admin:tenant:{data['tenantId']}")
                
                emit(f"admin:tenant:user:add:response:{data.get('requestId')}", {
                    'success': True
                })
            else:
                emit(f"admin:tenant:user:add:response:{data.get('requestId')}", {
                    'success': False,
                    'error': result.get('error')
                })
    except Exception as e:
        logger.error(f"Error adding user to tenant: {str(e)}")
        emit(f"admin:tenant:user:add:response:{data.get('requestId')}", {
            'success': False,
            'error': 'Failed to add user'
        })

@socketio.on('admin:tenant:claimmd:add')
async def handle_add_claimmd(data):
    """Add ClaimMD account to tenant"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Send to service via NATS
        if nc and nc.is_connected:
            request_data = {
                **data,
                'admin_id': client['user']['id']
            }
            
            response = await nc.request('tenants.add_claimmd', 
                                      json.dumps(request_data).encode(), 
                                      timeout=5)
            result = json.loads(response.data.decode())
            
            if result.get('success'):
                # Broadcast to admins watching this tenant
                socketio.emit('admin:tenant:claimmd:added', result['account'], 
                            room=f"admin:tenant:{data['tenantId']}")
                
                emit(f"admin:tenant:claimmd:add:response:{data.get('requestId')}", {
                    'success': True
                })
            else:
                emit(f"admin:tenant:claimmd:add:response:{data.get('requestId')}", {
                    'success': False,
                    'error': result.get('error')
                })
    except Exception as e:
        logger.error(f"Error adding ClaimMD account: {str(e)}")
        emit(f"admin:tenant:claimmd:add:response:{data.get('requestId')}", {
            'success': False,
            'error': 'Failed to add ClaimMD account'
        })

# NATS message handlers for admin updates
async def handle_tenant_update(msg):
    """Handle tenant updates from NATS"""
    try:
        data = json.loads(msg.data.decode())
        update_type = data.get('type')
        
        if update_type == 'created':
            socketio.emit('admin:tenants:created', data['tenant'], 
                        room='admin:tenants')
        elif update_type == 'updated':
            socketio.emit('admin:tenants:update', data['tenant'], 
                        room='admin:tenants')
            socketio.emit('admin:tenant:update', data['tenant'], 
                        room=f"admin:tenant:{data['tenant']['id']}")
    except Exception as e:
        logger.error(f"Error handling tenant update: {str(e)}")

# Initialize NATS connection
async def init_nats():
    """Initialize NATS connection and subscriptions"""
    global nc
    
    try:
        nc = await nats.connect(NATS_URL)
        logger.info(f"Connected to NATS at {NATS_URL}")
        
        # Subscribe to admin-specific topics
        await nc.subscribe("admin.tenants.updates", cb=handle_tenant_update)
        
        logger.info("Admin NATS subscriptions established")
    except Exception as e:
        logger.error(f"Failed to connect to NATS: {str(e)}")

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Run NATS initialization in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_nats())
    
    # Start Flask-SocketIO server
    port = int(os.environ.get('PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, 
                 debug=os.environ.get('ENV') != 'production')