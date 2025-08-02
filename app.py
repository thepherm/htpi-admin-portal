"""
HTPI Admin Portal - Flask Application with Socket.IO Server
"""
import os
import logging
import asyncio
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from functools import wraps
import nats
from nats.aio.client import Client as NATS
import json
import uuid
import requests
import concurrent.futures

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

# Initialize Socket.IO with async mode
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True, async_mode='threading')

# NATS configuration
NATS_URL = os.environ.get('NATS_URL', 'nats://localhost:4222')
STANDALONE_MODE = os.environ.get('STANDALONE_MODE', 'true').lower() == 'true'
nc = None  # NATS client will be initialized on startup

# Connected clients tracking
connected_clients = {}

# Log startup mode
if STANDALONE_MODE:
    logger.warning("Running in STANDALONE MODE - No NATS/microservices required")
    logger.warning("Set STANDALONE_MODE=false when NATS and services are deployed")
else:
    logger.info("Running in MICROSERVICES MODE - Connecting to NATS")

# NATS subjects mapping
NATS_SUBJECTS = {
    # Patient service
    'patient.create': 'htpi.patient.create',
    'patient.list': 'htpi.patient.list',
    'patient.get': 'htpi.patient.get',
    'patient.update': 'htpi.patient.update',
    'patient.delete': 'htpi.patient.delete',
    
    # Insurance service
    'insurance.create': 'htpi.insurance.create',
    'insurance.list': 'htpi.insurance.list',
    'insurance.eligibility.check': 'htpi.insurance.eligibility.check',
    
    # Claims service
    'claims.create': 'htpi.claims.create',
    'claims.list': 'htpi.claims.list',
    'claims.upload': 'htpi.claims.upload',
    'claims.status.check': 'htpi.claims.status.check',
    
    # Encounters service
    'encounters.create': 'htpi.encounters.create',
    'encounters.list': 'htpi.encounters.list',
    'encounters.update.status': 'htpi.encounters.update.status',
    
    # Tenant service
    'tenant.create': 'htpi.tenant.create',
    'tenant.list': 'htpi.tenant.list',
    'tenant.get': 'htpi.tenant.get',
    'tenant.switch': 'htpi.tenant.switch',
    
    # Auth service
    'auth.login': 'htpi.auth.login',
    'auth.verify': 'htpi.auth.verify'
}

def publish_to_nats(subject_key, data):
    """
    Publish message to NATS
    This is a placeholder for sync mode - in production this would be async
    """
    if not nc or not nc.is_connected:
        logger.warning(f"NATS not connected, cannot publish to {subject_key}")
        return None
    
    try:
        subject = NATS_SUBJECTS.get(subject_key)
        if not subject:
            logger.error(f"Unknown NATS subject key: {subject_key}")
            return None
        
        message = json.dumps(data).encode()
        logger.info(f"Publishing to NATS {subject}: {data}")
        
        # In production, this would be async
        # response = await nc.request(subject, message, timeout=30)
        # return json.loads(response.data.decode())
        
        return None  # Sync mode limitation
    except Exception as e:
        logger.error(f"Error publishing to NATS: {str(e)}")
        return None

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
    # Mock stats for development
    mock_stats = {
        'total_organizations': 2,
        'total_users': 17,
        'total_patients': 342,
        'total_claims': 1847,
        'pending_claims': 23,
        'approved_claims': 1798,
        'denied_claims': 26
    }
    
    return render_template('dashboard/index.html', 
                         user=session.get('user'),
                         stats=mock_stats)

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
    # Mock service status for development
    mock_services = {
        'gateway': {
            'healthy': True,
            'message': 'Handling API requests'
        },
        'admin': {
            'healthy': True,
            'message': 'Portal operational'
        },
        'patient': {
            'healthy': True,
            'message': 'Processing patient data'
        },
        'insurance': {
            'healthy': False,
            'message': 'Service unavailable'
        },
        'mongodb': {
            'healthy': True,
            'message': 'Database operational'
        },
        'nats': {
            'healthy': False,
            'message': 'Message broker offline'
        }
    }
    
    return render_template('services/index.html', 
                         user=session.get('user'),
                         services=mock_services)

@app.route('/patients')
@login_required
def patients():
    return render_template('patients/index.html',
                         user=session.get('user'))

@app.route('/patients/<patient_id>')
@login_required
def patient_detail(patient_id):
    return render_template('patients/detail.html',
                         user=session.get('user'),
                         patient_id=patient_id)

@app.route('/insurance')
@login_required
def insurance():
    return render_template('insurance/index.html',
                         user=session.get('user'))

@app.route('/claims')
@login_required
def claims():
    return render_template('claims/index.html',
                         user=session.get('user'))

@app.route('/encounters')
@login_required
def encounters():
    return render_template('encounters/index.html',
                         user=session.get('user'))

@app.route('/tenants/switch')
@login_required
def switch_tenant():
    return render_template('tenants/switch.html',
                         user=session.get('user'))

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    health_status = {
        'status': 'healthy',
        'service': 'htpi-admin-portal',
        'timestamp': datetime.utcnow().isoformat(),
        'nats_connected': nc.is_connected if nc else False,
        'standalone_mode': STANDALONE_MODE
    }
    return jsonify(health_status), 200

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
def handle_login(data):
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
            
            # Request-reply pattern with NATS (synchronous for now)
            # In production, this would be handled by an async task queue
            logger.info("NATS auth not implemented in sync mode")
            emit('auth:login:response', {
                'success': False,
                'error': 'Authentication service not available'
            })
        else:
            # Fallback authentication for development/testing when NATS is not available
            logger.warning("NATS not connected - using fallback authentication")
            
            # Check for default admin credentials (ONLY for development)
            if email == 'admin@htpi.com' and password == 'changeme123':
                # Create mock admin user
                user_data = {
                    'id': 'admin-001',
                    'email': email,
                    'name': 'System Admin',
                    'role': 'admin'
                }
                token = 'dev-token-' + os.urandom(16).hex()
                
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
                
                logger.warning(f"Admin authenticated via fallback: {email}")
            else:
                emit('auth:login:response', {
                    'success': False,
                    'error': 'Invalid credentials'
                })
    except Exception as e:
        logger.error(f"Admin login error: {str(e)}")
        emit('auth:login:response', {
            'success': False,
            'error': 'Authentication failed'
        })

# Admin-specific Socket.IO event handlers
@socketio.on('admin:tenants:subscribe')
def handle_tenants_subscribe():
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
            # NATS operations would need to be handled differently in sync mode
            logger.info("NATS operations not available in sync mode")
            # Fall through to mock data
            pass
        else:
            # Fallback mock data when NATS is not available
            logger.warning("Using mock tenant data - NATS not connected")
            mock_tenants = [
                {
                    'id': 'tenant-001',
                    'name': 'Demo Clinic',
                    'domain': 'demo.htpi.com',
                    'status': 'Active',
                    'userCount': 5,
                    'claimMDAccounts': 2,
                    'createdAt': '2024-01-15T10:00:00Z'
                },
                {
                    'id': 'tenant-002',
                    'name': 'Test Hospital',
                    'domain': 'test.htpi.com',
                    'status': 'Active',
                    'userCount': 12,
                    'claimMDAccounts': 3,
                    'createdAt': '2024-02-01T14:30:00Z'
                }
            ]
            emit('admin:tenants:list', mock_tenants)
            logger.info(f"Admin subscribed to tenants with mock data")
    except Exception as e:
        logger.error(f"Error subscribing to tenants: {str(e)}")
        emit('error', {'message': 'Failed to load tenants'})

@socketio.on('admin:tenants:create')
def handle_create_tenant(data):
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
            # NATS operations would need to be handled differently in sync mode
            logger.info("NATS operations not available in sync mode")
            result = {'success': False, 'error': 'NATS not available in sync mode'}
            
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
def handle_tenant_subscribe(data):
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
            # NATS operations would need to be handled differently in sync mode
            logger.info("NATS operations not available in sync mode")
            # Fall through to mock data
            pass
        else:
            # Fallback mock data when NATS is not available
            logger.warning(f"Using mock data for tenant {tenant_id} - NATS not connected")
            
            mock_data = {
                'tenant-001': {
                    'tenant': {
                        'id': 'tenant-001',
                        'name': 'Demo Clinic',
                        'domain': 'demo.htpi.com',
                        'status': 'Active',
                        'createdAt': '2024-01-15T10:00:00Z'
                    },
                    'users': [
                        {
                            'id': 'user-001',
                            'name': 'John Doe',
                            'email': 'john@demo.htpi.com',
                            'role': 'admin',
                            'status': 'active',
                            'lastLogin': '2024-03-15T09:30:00Z'
                        },
                        {
                            'id': 'user-002',
                            'name': 'Jane Smith',
                            'email': 'jane@demo.htpi.com',
                            'role': 'user',
                            'status': 'active',
                            'lastLogin': '2024-03-14T14:15:00Z'
                        }
                    ],
                    'claimMDAccounts': [
                        {
                            'id': 'claimmd-001',
                            'accountName': 'Main Office',
                            'apiKey': 'demo-key-xxxx-xxxx',
                            'environment': 'production',
                            'status': 'active',
                            'createdAt': '2024-01-20T11:00:00Z'
                        }
                    ]
                },
                'tenant-002': {
                    'tenant': {
                        'id': 'tenant-002',
                        'name': 'Test Hospital',
                        'domain': 'test.htpi.com',
                        'status': 'Active',
                        'createdAt': '2024-02-01T14:30:00Z'
                    },
                    'users': [
                        {
                            'id': 'user-003',
                            'name': 'Admin User',
                            'email': 'admin@test.htpi.com',
                            'role': 'admin',
                            'status': 'active',
                            'lastLogin': '2024-03-15T08:00:00Z'
                        }
                    ],
                    'claimMDAccounts': []
                }
            }
            
            tenant_data = mock_data.get(tenant_id, {
                'tenant': {'id': tenant_id, 'name': 'Unknown Tenant', 'status': 'Active'},
                'users': [],
                'claimMDAccounts': []
            })
            
            emit('admin:tenant:data', tenant_data)
            logger.info(f"Admin subscribed to tenant {tenant_id} with mock data")
    except Exception as e:
        logger.error(f"Error subscribing to tenant: {str(e)}")
        emit('error', {'message': 'Failed to load tenant data'})

@socketio.on('admin:tenant:user:add')
def handle_add_user_to_tenant(data):
    """Add user to tenant"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Send to service via NATS
        if nc and nc.is_connected:
            # NATS operations would need to be handled differently in sync mode
            logger.info("NATS operations not available in sync mode")
            result = {'success': False, 'error': 'NATS not available in sync mode'}
            
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
def handle_add_claimmd(data):
    """Add ClaimMD account to tenant"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Send to service via NATS
        if nc and nc.is_connected:
            # NATS operations would need to be handled differently in sync mode
            logger.info("NATS operations not available in sync mode")
            result = {'success': False, 'error': 'NATS not available in sync mode'}
            
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

@socketio.on('admin:patients:subscribe')
def handle_patients_subscribe(data):
    """Subscribe to patient updates - forward to NATS or use standalone mode"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    tenant_id = data.get('tenantId')
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Join Socket.IO room for this tenant's patients
        room = f"admin:patients:{tenant_id}"
        join_room(room)
        
        if STANDALONE_MODE:
            # Standalone mode - return mock data
            mock_patients = [
                {
                    'id': 'pat-001',
                    'patientId': 'P001234',
                    'firstName': 'John',
                    'lastName': 'Doe',
                    'dateOfBirth': '1985-03-15',
                    'gender': 'M',
                    'ssn': 'XXX-XX-1234',
                    'phone': '(555) 123-4567',
                    'email': 'john.doe@email.com',
                    'address': '123 Main St',
                    'city': 'Springfield',
                    'state': 'IL',
                    'zipCode': '62701',
                    'insuranceCount': 2,
                    'tenantId': tenant_id
                },
                {
                    'id': 'pat-002',
                    'patientId': 'P001235',
                    'firstName': 'Jane',
                    'lastName': 'Smith',
                    'dateOfBirth': '1990-07-22',
                    'gender': 'F',
                    'ssn': 'XXX-XX-5678',
                    'phone': '(555) 987-6543',
                    'email': 'jane.smith@email.com',
                    'address': '456 Oak Ave',
                    'city': 'Springfield',
                    'state': 'IL',
                    'zipCode': '62702',
                    'insuranceCount': 1,
                    'tenantId': tenant_id
                }
            ]
            
            emit('admin:patients:list', {'patients': mock_patients})
            logger.info(f"[STANDALONE] Admin subscribed to patients for tenant {tenant_id}")
            
        else:
            # Production mode - use NATS
            nats_message = {
                'tenantId': tenant_id,
                'userId': client['user']['id'],
                'requestType': 'subscribe',
                'responseChannel': f"admin.patients.response.{client_id}"
            }
            
            result = publish_to_nats('patient.list', nats_message)
            
            if result:
                emit('admin:patients:list', result)
            else:
                emit('admin:patients:list', {'patients': [], 'error': 'Service temporarily unavailable'})
        
        logger.info(f"Admin {client['user']['id']} subscribed to patients for tenant {tenant_id}")
        
    except Exception as e:
        logger.error(f"Error in patients subscribe: {str(e)}")
        emit('error', {'message': 'Failed to subscribe to patients'})

@socketio.on('admin:patients:create')
def handle_create_patient(data):
    """Forward patient creation request to NATS or handle in standalone mode"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        if STANDALONE_MODE:
            # Standalone mode - create mock patient
            import random
            patient_id = f"P{str(random.randint(100000, 999999))}"
            
            new_patient = {
                'id': f"pat-{random.randint(1000, 9999)}",
                'patientId': patient_id,
                **data,
                'insuranceCount': 0,
                'createdBy': client['user']['id'],
                'createdAt': datetime.utcnow().isoformat()
            }
            
            # Send success response
            emit(f"admin:patients:create:response:{data.get('requestId')}", {
                'success': True,
                'patient': new_patient
            })
            
            # Broadcast to all admins watching this tenant
            socketio.emit('admin:patients:created', new_patient, 
                        room=f"admin:patients:{data['tenantId']}")
            
            logger.info(f"[STANDALONE] Patient created: {patient_id}")
            
        else:
            # Production mode - forward to NATS
            nats_message = {
                **data,
                'createdBy': client['user']['id'],
                'createdByName': client['user']['name'],
                'requestId': data.get('requestId'),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if nc and nc.is_connected:
                logger.info(f"Publishing patient.create to NATS: {nats_message}")
                result = publish_to_nats('patient.create', nats_message)
                
                if not result:
                    emit(f"admin:patients:create:response:{data.get('requestId')}", {
                        'success': False,
                        'error': 'Service temporarily unavailable'
                    })
            else:
                emit(f"admin:patients:create:response:{data.get('requestId')}", {
                    'success': False,
                    'error': 'Message broker offline'
                })
        
    except Exception as e:
        logger.error(f"Error in patient create: {str(e)}")
        emit(f"admin:patients:create:response:{data.get('requestId')}", {
            'success': False,
            'error': 'Failed to process request'
        })

@socketio.on('admin:patients:list:simple')
def handle_patients_list_simple(data):
    """Get simple patient list for dropdowns"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    tenant_id = data.get('tenantId')
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Send mock patient data for development
        mock_patients = [
            {
                'id': 'pat-001',
                'patientId': 'P001234',
                'firstName': 'John',
                'lastName': 'Doe'
            },
            {
                'id': 'pat-002',
                'patientId': 'P001235',
                'firstName': 'Jane',
                'lastName': 'Smith'
            }
        ]
        
        emit('admin:patients:list:simple', {'patients': mock_patients})
        
    except Exception as e:
        logger.error(f"Error getting patient list: {str(e)}")
        emit('error', {'message': 'Failed to load patients'})

@socketio.on('admin:encounters:subscribe')
def handle_encounters_subscribe(data):
    """Subscribe to encounters updates"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    tenant_id = data.get('tenantId')
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Join encounters room
        room = f"admin:encounters:{tenant_id}"
        join_room(room)
        
        # Send mock encounter data for development
        mock_encounters = [
            {
                'id': 'enc-001',
                'encounterId': 'ENC20240315001',
                'patientId': 'P001234',
                'patientName': 'Doe, John',
                'providerId': 'prov-001',
                'providerName': 'Dr. John Smith, MD',
                'providerNPI': '1234567890',
                'encounterDate': '2024-03-15T09:00:00',
                'encounterType': 'office',
                'chiefComplaint': 'Annual Physical Exam',
                'status': 'completed',
                'duration': 30,
                'vitals': {
                    'bp': '120/80',
                    'pulse': '72',
                    'temp': '98.6',
                    'weight': '180'
                },
                'billed': False,
                'tenantId': tenant_id
            },
            {
                'id': 'enc-002',
                'encounterId': 'ENC20240315002',
                'patientId': 'P001235',
                'patientName': 'Smith, Jane',
                'providerId': 'prov-002',
                'providerName': 'Dr. Jane Wilson, MD',
                'providerNPI': '0987654321',
                'encounterDate': '2024-03-15T14:30:00',
                'encounterType': 'follow-up',
                'chiefComplaint': 'Follow-up for Hypertension',
                'status': 'scheduled',
                'duration': None,
                'tenantId': tenant_id
            }
        ]
        
        emit('admin:encounters:list', {'encounters': mock_encounters})
        logger.info(f"Admin subscribed to encounters for tenant {tenant_id}")
        
    except Exception as e:
        logger.error(f"Error subscribing to encounters: {str(e)}")
        emit('error', {'message': 'Failed to load encounters'})

@socketio.on('admin:encounters:create')
def handle_create_encounter(data):
    """Create a new encounter"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Generate encounter ID
        import random
        encounter_id = f"ENC{str(random.randint(100000000, 999999999))}"
        
        # Get patient info (in production from DB)
        patient_map = {
            'pat-001': {'name': 'Doe, John', 'id': 'P001234'},
            'pat-002': {'name': 'Smith, Jane', 'id': 'P001235'}
        }
        patient_info = patient_map.get(data['patientId'], {'name': 'Unknown', 'id': 'Unknown'})
        
        # Get provider info
        provider_map = {
            'prov-001': {'name': 'Dr. John Smith, MD', 'npi': '1234567890'},
            'prov-002': {'name': 'Dr. Jane Wilson, MD', 'npi': '0987654321'},
            'prov-003': {'name': 'Dr. Robert Brown, DO', 'npi': '1122334455'}
        }
        provider_info = provider_map.get(data['providerId'], {'name': 'Unknown', 'npi': 'Unknown'})
        
        # Create encounter object
        new_encounter = {
            'id': f"enc-{random.randint(1000, 9999)}",
            'encounterId': encounter_id,
            'patientId': patient_info['id'],
            'patientName': patient_info['name'],
            'providerId': data['providerId'],
            'providerName': provider_info['name'],
            'providerNPI': provider_info['npi'],
            'encounterDate': data['encounterDate'],
            'encounterType': data['encounterType'],
            'chiefComplaint': data['chiefComplaint'],
            'reasonForVisit': data.get('reasonForVisit'),
            'status': data['status'],
            'vitals': data.get('vitals'),
            'duration': None,
            'billed': False,
            'createdBy': client['user']['id'],
            'createdAt': '2024-03-15T10:00:00Z',
            'tenantId': data['tenantId']
        }
        
        # In production, this would be sent to NATS
        # For now, broadcast to admins watching this tenant
        socketio.emit('admin:encounters:created', new_encounter, 
                    room=f"admin:encounters:{data['tenantId']}")
        
        # Send success response
        emit(f"admin:encounters:create:response:{data.get('requestId')}", {
            'success': True,
            'encounter': new_encounter
        })
        
        logger.info(f"Encounter created: {encounter_id}")
        
    except Exception as e:
        logger.error(f"Error creating encounter: {str(e)}")
        emit(f"admin:encounters:create:response:{data.get('requestId')}", {
            'success': False,
            'error': 'Failed to create encounter'
        })

@socketio.on('admin:encounters:update:status')
def handle_update_encounter_status(data):
    """Update encounter status"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        encounter_id = data.get('encounterId')
        new_status = data.get('status')
        tenant_id = data.get('tenantId')
        
        # In production, this would update via NATS/DB
        # For now, broadcast the update
        socketio.emit('admin:encounters:update', {
            'encounter': {
                'id': encounter_id,
                'status': new_status
            }
        }, room=f"admin:encounters:{tenant_id}")
        
        logger.info(f"Encounter {encounter_id} status updated to {new_status}")
        
    except Exception as e:
        logger.error(f"Error updating encounter status: {str(e)}")
        emit('error', {'message': 'Failed to update encounter'})

@socketio.on('admin:insurance:subscribe')
def handle_insurance_subscribe(data):
    """Subscribe to insurance updates"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    tenant_id = data.get('tenantId')
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Join insurance room
        room = f"admin:insurance:{tenant_id}"
        join_room(room)
        
        # Send mock insurance data for development
        mock_policies = [
            {
                'id': 'ins-001',
                'patientId': 'P001234',
                'patientName': 'Doe, John',
                'payerId': '87726',
                'payerName': 'United Healthcare',
                'payerOrder': 'Primary',
                'policyNumber': 'UHC123456789',
                'groupNumber': '12345',
                'effectiveDate': '2024-01-01',
                'status': 'Active'
            },
            {
                'id': 'ins-002',
                'patientId': 'P001235',
                'patientName': 'Smith, Jane',
                'payerId': '04402',
                'payerName': 'Medicare',
                'payerOrder': 'Primary',
                'policyNumber': '1EG4TE5MK73',
                'groupNumber': None,
                'effectiveDate': '2023-06-01',
                'status': 'Active'
            }
        ]
        
        emit('admin:insurance:list', {'policies': mock_policies})
        logger.info(f"Admin subscribed to insurance for tenant {tenant_id}")
        
    except Exception as e:
        logger.error(f"Error subscribing to insurance: {str(e)}")
        emit('error', {'message': 'Failed to load insurance'})

@socketio.on('admin:insurance:create')
def handle_create_insurance(data):
    """Create a new insurance policy"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Generate insurance ID
        import random
        insurance_id = f"ins-{random.randint(1000, 9999)}"
        
        # Get patient info (in production from DB)
        patient_map = {
            'pat-001': {'name': 'Doe, John', 'id': 'P001234'},
            'pat-002': {'name': 'Smith, Jane', 'id': 'P001235'}
        }
        patient_info = patient_map.get(data['patientId'], {'name': 'Unknown', 'id': 'Unknown'})
        
        # Get payer info
        payer_map = {
            '87726': 'United Healthcare',
            '22099': 'Blue Cross Blue Shield',
            '60054': 'Aetna',
            '62308': 'Cigna',
            '04402': 'Medicare',
            '86916': 'Medicaid'
        }
        
        # Create insurance object
        new_insurance = {
            'id': insurance_id,
            'patientId': patient_info['id'],
            'patientName': patient_info['name'],
            'payerId': data['payerId'],
            'payerName': payer_map.get(data['payerId'], 'Unknown Payer'),
            'payerOrder': data['payerOrder'],
            'policyNumber': data['policyNumber'],
            'groupNumber': data.get('groupNumber'),
            'effectiveDate': data['effectiveDate'],
            'terminationDate': data.get('terminationDate'),
            'subscriberRelation': data['subscriberRelation'],
            'subscriberDOB': data.get('subscriberDOB'),
            'subscriberFirstName': data.get('subscriberFirstName'),
            'subscriberLastName': data.get('subscriberLastName'),
            'copayAmount': data.get('copayAmount'),
            'deductible': data.get('deductible'),
            'status': 'Active',
            'createdBy': client['user']['id'],
            'createdAt': '2024-03-15T10:00:00Z',
            'tenantId': data['tenantId']
        }
        
        # In production, this would be sent to NATS
        # For now, broadcast to admins watching this tenant
        socketio.emit('admin:insurance:created', new_insurance, 
                    room=f"admin:insurance:{data['tenantId']}")
        
        # Send success response
        emit(f"admin:insurance:create:response:{data.get('requestId')}", {
            'success': True,
            'insurance': new_insurance
        })
        
        logger.info(f"Insurance created: {insurance_id}")
        
    except Exception as e:
        logger.error(f"Error creating insurance: {str(e)}")
        emit(f"admin:insurance:create:response:{data.get('requestId')}", {
            'success': False,
            'error': 'Failed to create insurance'
        })

@socketio.on('admin:insurance:eligibility:check')
def handle_eligibility_check(data):
    """Check insurance eligibility via ClaimMD"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        request_id = data.get('requestId')
        
        # Mock eligibility response for development
        # In production, this would call ClaimMD API
        mock_response = {
            'requestId': request_id,
            'success': True,
            'memberName': 'John Doe',
            'memberId': data.get('policyNumber', 'UHC123456789'),
            'groupNumber': data.get('groupNumber', '12345'),
            'planName': 'PPO Standard',
            'benefits': [
                {'description': 'Office Visit', 'coverage': '$20 copay'},
                {'description': 'Specialist Visit', 'coverage': '$40 copay'},
                {'description': 'Annual Deductible', 'coverage': '$1,500'},
                {'description': 'Out of Pocket Max', 'coverage': '$5,000'}
            ]
        }
        
        # Send response
        emit('admin:insurance:eligibility:response', mock_response)
        logger.info(f"Eligibility check performed for request {request_id}")
        
    except Exception as e:
        logger.error(f"Error checking eligibility: {str(e)}")
        emit('admin:insurance:eligibility:response', {
            'requestId': data.get('requestId'),
            'success': False,
            'error': 'Failed to check eligibility'
        })

@socketio.on('admin:claims:subscribe')
def handle_claims_subscribe(data):
    """Subscribe to claims updates"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    tenant_id = data.get('tenantId')
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Join claims room
        room = f"admin:claims:{tenant_id}"
        join_room(room)
        
        # Send mock claims data for development
        mock_claims = [
            {
                'id': 'clm-001',
                'claimId': 'CLM20240315001',
                'pcn': '151068-1',
                'patientName': 'Doe, John',
                'serviceDate': '2024-03-15',
                'payerName': 'Blue Cross Blue Shield',
                'totalCharge': '165.00',
                'status': 'Acknowledged',
                'claimMdId': '396891541'
            },
            {
                'id': 'clm-002',
                'claimId': 'CLM20240315002',
                'pcn': '107026-1',
                'patientName': 'Smith, Jane',
                'serviceDate': '2024-03-14',
                'payerName': 'Aetna',
                'totalCharge': '75.00',
                'status': 'Paid',
                'claimMdId': '396891542'
            }
        ]
        
        emit('admin:claims:list', {'claims': mock_claims})
        logger.info(f"Admin subscribed to claims for tenant {tenant_id}")
        
    except Exception as e:
        logger.error(f"Error subscribing to claims: {str(e)}")
        emit('error', {'message': 'Failed to load claims'})

@socketio.on('admin:claims:create')
def handle_create_claim(data):
    """Create a new claim and submit to ClaimMD"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # Generate claim ID
        import random
        claim_id = f"CLM{str(random.randint(100000000, 999999999))}"
        pcn = f"{random.randint(100000, 999999)}-1"
        
        # Mock ClaimMD submission response
        # In production, this would submit to ClaimMD API
        claimmd_id = str(random.randint(396000000, 396999999))
        
        # Send success response
        emit(f"admin:claims:create:response:{data.get('requestId')}", {
            'success': True,
            'claimMdId': claimmd_id,
            'claimId': claim_id,
            'pcn': pcn
        })
        
        logger.info(f"Claim created and submitted to ClaimMD: {claim_id}")
        
    except Exception as e:
        logger.error(f"Error creating claim: {str(e)}")
        emit(f"admin:claims:create:response:{data.get('requestId')}", {
            'success': False,
            'error': 'Failed to create claim'
        })

@socketio.on('admin:tenant:switch')
def handle_tenant_switch(data):
    """Switch the active tenant for the admin user"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        tenant_id = data.get('tenantId')
        request_id = data.get('requestId')
        
        if tenant_id:
            # Mock tenant lookup for development
            tenant_map = {
                'tenant-001': {'id': 'tenant-001', 'name': 'Demo Clinic'},
                'tenant-002': {'id': 'tenant-002', 'name': 'Test Hospital'},
                'tenant-003': {'id': 'tenant-003', 'name': 'Sample Medical Center'}
            }
            
            tenant = tenant_map.get(tenant_id)
            if tenant:
                # Update client's current tenant
                connected_clients[client_id]['current_tenant'] = tenant
                
                # In production, this would update the session via Flask
                emit(f"admin:tenant:switch:response:{request_id}", {
                    'success': True,
                    'tenant': tenant
                })
                
                logger.info(f"Admin {client['user']['email']} switched to tenant {tenant['name']}")
            else:
                emit(f"admin:tenant:switch:response:{request_id}", {
                    'success': False,
                    'error': 'Tenant not found'
                })
        else:
            # Clear tenant selection
            connected_clients[client_id]['current_tenant'] = None
            
            emit(f"admin:tenant:switch:response:{request_id}", {
                'success': True,
                'tenant': None
            })
            
            logger.info(f"Admin {client['user']['email']} cleared tenant selection")
            
    except Exception as e:
        logger.error(f"Error switching tenant: {str(e)}")
        emit(f"admin:tenant:switch:response:{data.get('requestId')}", {
            'success': False,
            'error': 'Failed to switch tenant'
        })

# Service monitoring handlers
@socketio.on('services:status:check')
def handle_service_status_check():
    """Check status of all services via NATS"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        # List of services to check
        services_to_check = [
            'htpi-admin-portal',
            'htpi-customer-portal', 
            'htpi-gateway-service',
            'htpi-admin-service',
            'htpi-auth-service',
            'htpi-tenant-service',
            'htpi-patients-service',
            'htpi-insurance-service',
            'htpi-dashboard-service',
            'htpi-encounters-service',
            'htpi-mongodb-service',
            'htpi-nats'
        ]
        
        service_status = {}
        
        if STANDALONE_MODE or not nc or not nc.is_connected:
            # Mock status when NATS not available
            for service_id in services_to_check:
                service_status[service_id] = {
                    'id': service_id,
                    'status': 'healthy' if service_id in ['htpi-admin-portal', 'htpi-gateway-service', 'htpi-auth-service'] else 'down',
                    'message': 'Mock status - NATS not connected',
                    'lastChecked': datetime.utcnow().isoformat()
                }
        else:
            # Send health check request via NATS to each service
            health_check_request = {
                'requestId': str(uuid.uuid4()),
                'clientId': client_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Publish health check requests
            for service_id in services_to_check:
                subject = f"htpi.health.{service_id.replace('-', '.')}"
                
                # For NATS itself, check differently
                if service_id == 'htpi-nats':
                    service_status[service_id] = {
                        'id': service_id,
                        'status': 'healthy' if nc.is_connected else 'down',
                        'message': 'NATS Server' if nc.is_connected else 'Not connected',
                        'lastChecked': datetime.utcnow().isoformat()
                    }
                else:
                    # Send health check request
                    if publish_to_nats(subject, health_check_request):
                        # Store as pending
                        service_status[service_id] = {
                            'id': service_id,
                            'status': 'checking',
                            'message': 'Health check sent',
                            'lastChecked': datetime.utcnow().isoformat()
                        }
                    else:
                        service_status[service_id] = {
                            'id': service_id,
                            'status': 'unknown',
                            'message': 'Failed to send health check',
                            'lastChecked': datetime.utcnow().isoformat()
                        }
        
        # Special handling for MongoDB
        service_status['mongodb'] = {
            'status': 'healthy' if service_status.get('htpi-mongodb-service', {}).get('status') in ['healthy', 'checking'] else 'down',
            'message': 'Database operational',
            'lastChecked': datetime.utcnow().isoformat()
        }
        
        # Store health check request ID for tracking responses
        if 'health_checks' not in connected_clients[client_id]:
            connected_clients[client_id]['health_checks'] = {}
        connected_clients[client_id]['health_checks'][health_check_request['requestId']] = {
            'status': service_status,
            'pending': len([s for s in service_status.values() if s.get('status') == 'checking']),
            'timestamp': datetime.utcnow()
        }
        
        emit('services:status:response', {
            'success': True,
            'status': service_status,
            'requestId': health_check_request['requestId']
        })
        
        # Set timeout to finalize status after 5 seconds
        def finalize_health_status():
            try:
                if client_id in connected_clients and health_check_request['requestId'] in connected_clients[client_id].get('health_checks', {}):
                    current_status = connected_clients[client_id]['health_checks'][health_check_request['requestId']]['status']
                    
                    # Mark any still-checking services as down
                    for service_id, status in current_status.items():
                        if status.get('status') == 'checking':
                            status['status'] = 'down'
                            status['message'] = 'No response received'
                    
                    # Emit final status
                    socketio.emit('services:status:update', {
                        'requestId': health_check_request['requestId'],
                        'status': current_status
                    }, room=client_id)
                    
                    # Clean up
                    del connected_clients[client_id]['health_checks'][health_check_request['requestId']]
                    
            except Exception as e:
                logger.error(f"Error finalizing health status: {str(e)}")
        
        # Schedule finalization
        from threading import Timer
        timer = Timer(5.0, finalize_health_status)
        timer.start()
        
    except Exception as e:
        logger.error(f"Error checking service status: {str(e)}")
        emit('services:status:response', {
            'success': False,
            'error': str(e)
        })

@socketio.on('services:nats:monitor')
def handle_nats_monitor():
    """Get NATS monitoring data"""
    client_id = request.sid
    client = connected_clients.get(client_id)
    
    if not client or not client.get('authenticated') or client.get('role') != 'admin':
        emit('error', {'message': 'Admin access required'})
        return
    
    try:
        import requests
        
        if STANDALONE_MODE:
            # Mock NATS metrics
            mock_metrics = {
                'connections': 12,
                'in_msgs': 1524367,
                'out_msgs': 1523891,
                'subscriptions': 148,
                'connz': {
                    'connections': [
                        {
                            'cid': 1,
                            'name': 'htpi-admin-portal',
                            'subscriptions': 24,
                            'pending_bytes': 0,
                            'in_msgs': 125431,
                            'out_msgs': 125098
                        },
                        {
                            'cid': 2,
                            'name': 'htpi-patients-service',
                            'subscriptions': 18,
                            'pending_bytes': 0,
                            'in_msgs': 98234,
                            'out_msgs': 98156
                        },
                        {
                            'cid': 3,
                            'name': 'htpi-gateway-service',
                            'subscriptions': 32,
                            'pending_bytes': 0,
                            'in_msgs': 234567,
                            'out_msgs': 234123
                        }
                    ]
                }
            }
            
            emit('services:nats:monitor:response', {
                'success': True,
                'metrics': mock_metrics
            })
            return
        
        # Get NATS monitoring URL
        nats_monitor_url = 'http://localhost:8222'
        if os.environ.get('ENV') == 'production':
            nats_monitor_url = 'http://htpi-nats.railway.internal:8222'
        
        # Fetch varz (general stats)
        varz_response = requests.get(f'{nats_monitor_url}/varz', timeout=5)
        varz = varz_response.json() if varz_response.status_code == 200 else {}
        
        # Fetch connz (connection details)
        connz_response = requests.get(f'{nats_monitor_url}/connz', timeout=5)
        connz = connz_response.json() if connz_response.status_code == 200 else {}
        
        metrics = {
            'connections': varz.get('connections', 0),
            'in_msgs': varz.get('in_msgs', 0),
            'out_msgs': varz.get('out_msgs', 0),
            'subscriptions': varz.get('subscriptions', 0),
            'connz': connz
        }
        
        emit('services:nats:monitor:response', {
            'success': True,
            'metrics': metrics
        })
        
    except Exception as e:
        logger.error(f"Error fetching NATS monitoring data: {str(e)}")
        emit('services:nats:monitor:response', {
            'success': False,
            'error': str(e)
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

# NATS Response Handlers
async def handle_patient_response(msg):
    """Handle patient service responses from NATS"""
    try:
        data = json.loads(msg.data.decode())
        response_type = data.get('responseType')
        client_id = data.get('clientId')
        
        if response_type == 'list':
            # Broadcast to all admins in the tenant room
            socketio.emit('admin:patients:list', {
                'patients': data.get('patients', [])
            }, room=f"admin:patients:{data['tenantId']}")
            
        elif response_type == 'created':
            # Notify specific client and broadcast to room
            socketio.emit(f"admin:patients:create:response:{data['requestId']}", {
                'success': True,
                'patient': data['patient']
            }, room=client_id)
            
            # Broadcast to all admins watching this tenant
            socketio.emit('admin:patients:created', data['patient'], 
                        room=f"admin:patients:{data['tenantId']}")
            
    except Exception as e:
        logger.error(f"Error handling patient response: {str(e)}")

async def handle_insurance_response(msg):
    """Handle insurance service responses from NATS"""
    try:
        data = json.loads(msg.data.decode())
        response_type = data.get('responseType')
        
        if response_type == 'eligibility':
            # Send eligibility results to requesting client
            socketio.emit('admin:insurance:eligibility:response', data, 
                        room=data.get('clientId'))
                        
    except Exception as e:
        logger.error(f"Error handling insurance response: {str(e)}")

async def handle_claims_response(msg):
    """Handle claims service responses from NATS"""
    try:
        data = json.loads(msg.data.decode())
        response_type = data.get('responseType')
        
        if response_type == 'status_update':
            # Broadcast claim status update
            socketio.emit('admin:claims:status:update', {
                'claimMdId': data['claimMdId'],
                'status': data['status'],
                'message': data.get('message')
            }, room=f"admin:claims:{data['tenantId']}")
            
    except Exception as e:
        logger.error(f"Error handling claims response: {str(e)}")

async def handle_health_response(msg):
    """Handle health check responses from services"""
    try:
        data = json.loads(msg.data.decode())
        service_id = data.get('serviceId')
        request_id = data.get('requestId')
        client_id = data.get('clientId')
        
        # Find the client and update their health check status
        if client_id in connected_clients:
            health_checks = connected_clients[client_id].get('health_checks', {})
            
            if request_id in health_checks:
                # Update service status
                if service_id in health_checks[request_id]['status']:
                    health_checks[request_id]['status'][service_id] = {
                        'id': service_id,
                        'status': data.get('status', 'healthy'),
                        'message': data.get('message', 'Service operational'),
                        'version': data.get('version', 'unknown'),
                        'uptime': data.get('uptime', 'unknown'),
                        'lastChecked': datetime.utcnow().isoformat()
                    }
                    
                    # Emit update to client
                    socketio.emit('services:status:update', {
                        'requestId': request_id,
                        'serviceId': service_id,
                        'status': health_checks[request_id]['status'][service_id]
                    }, room=client_id)
                    
        logger.info(f"Received health response from {service_id}")
        
    except Exception as e:
        logger.error(f"Error handling health response: {str(e)}")

# Initialize NATS connection
async def init_nats():
    """Initialize NATS connection and subscriptions"""
    global nc
    
    try:
        nc = await nats.connect(NATS_URL)
        logger.info(f"Connected to NATS at {NATS_URL}")
        
        # Subscribe to response channels from services
        await nc.subscribe("admin.patients.response.*", cb=handle_patient_response)
        await nc.subscribe("admin.insurance.response.*", cb=handle_insurance_response)
        await nc.subscribe("admin.claims.response.*", cb=handle_claims_response)
        await nc.subscribe("admin.tenants.updates", cb=handle_tenant_update)
        
        # Subscribe to health check responses
        await nc.subscribe("admin.health.response.*", cb=handle_health_response)
        
        # Subscribe to broadcast channels
        await nc.subscribe("admin.broadcast.patients.*", cb=handle_patient_response)
        await nc.subscribe("admin.broadcast.claims.*", cb=handle_claims_response)
        
        logger.info("Admin NATS subscriptions established")
    except Exception as e:
        logger.error(f"Failed to connect to NATS: {str(e)}")
        logger.warning("Running without NATS - services unavailable")

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Only initialize NATS if not in standalone mode
    if not STANDALONE_MODE:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(init_nats())
        except Exception as e:
            logger.error(f"NATS initialization failed: {str(e)}")
            logger.warning("Starting without NATS connection")
    else:
        logger.info("Skipping NATS initialization in STANDALONE MODE")
    
    # Start Flask-SocketIO server
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"Starting admin portal on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, 
                 debug=os.environ.get('ENV') != 'production')