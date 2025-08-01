"""
HTPI Admin Portal - Flask Application
"""
import os
import asyncio
import json
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
import nats
from dotenv import load_dotenv

from forms import LoginForm, OrganizationForm, UserForm
from models import User

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# NATS configuration
NATS_URL = os.getenv('NATS_URL', 'nats://localhost:4222')
NATS_USER = os.getenv('NATS_USER', 'admin')
NATS_PASS = os.getenv('NATS_PASS', 'htpi_nats_dev')

# Global NATS connection
nc = None

async def get_nats_connection():
    """Get or create NATS connection"""
    global nc
    if nc is None or nc.is_closed:
        nc = await nats.connect(
            servers=[NATS_URL],
            user=NATS_USER,
            password=NATS_PASS
        )
    return nc

def nats_request(subject, data):
    """Make a synchronous NATS request"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_nats_request(subject, data))
    finally:
        loop.close()

async def _nats_request(subject, data):
    """Make an async NATS request"""
    nc = await get_nats_connection()
    try:
        response = await nc.request(subject, json.dumps(data).encode(), timeout=5.0)
        return json.loads(response.data.decode())
    except Exception as e:
        print(f"NATS request error: {e}")
        return {"error": str(e)}

@login_manager.user_loader
def load_user(user_id):
    """Load user from session"""
    # In production, this would query the database via NATS
    if 'user_data' in session:
        return User(session['user_data'])
    return None

def admin_required(f):
    """Decorator for admin-only routes"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    """Redirect to dashboard"""
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Authenticate via NATS
        response = nats_request('admin.auth.login', {
            'email': form.email.data,
            'password': form.password.data
        })
        
        if response.get('success'):
            user_data = response.get('user')
            user = User(user_data)
            session['user_data'] = user_data
            login_user(user, remember=form.remember_me.data)
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    # Get stats via NATS
    stats = nats_request('admin.stats.get', {
        'org_id': current_user.org_id if not current_user.is_super_admin else None
    })
    
    return render_template('dashboard.html', stats=stats.get('data', {}))

@app.route('/organizations')
@login_required
@admin_required
def organizations():
    """Organizations list"""
    # Get organizations via NATS
    response = nats_request('admin.organizations.list', {
        'page': request.args.get('page', 1, type=int),
        'limit': 20
    })
    
    orgs = response.get('data', {}).get('organizations', [])
    pagination = response.get('data', {}).get('pagination', {})
    
    return render_template('organizations.html', organizations=orgs, pagination=pagination)

@app.route('/organizations/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_organization():
    """Add new organization"""
    form = OrganizationForm()
    
    if form.validate_on_submit():
        response = nats_request('admin.organizations.create', {
            'name': form.name.data,
            'type': form.type.data,
            'contact_email': form.contact_email.data,
            'contact_name': form.contact_name.data,
            'contact_phone': form.contact_phone.data,
            'address': {
                'line1': form.address_line1.data,
                'line2': form.address_line2.data,
                'city': form.city.data,
                'state': form.state.data,
                'zip': form.zip_code.data
            }
        })
        
        if response.get('success'):
            flash('Organization created successfully', 'success')
            return redirect(url_for('organizations'))
        else:
            flash(response.get('error', 'Failed to create organization'), 'error')
    
    return render_template('organization_form.html', form=form)

@app.route('/organizations/<org_id>')
@login_required
@admin_required
def view_organization(org_id):
    """View organization details"""
    response = nats_request('admin.organizations.get', {'org_id': org_id})
    
    if response.get('success'):
        org = response.get('data')
        return render_template('organization_detail.html', organization=org)
    else:
        flash('Organization not found', 'error')
        return redirect(url_for('organizations'))

@app.route('/users')
@login_required
@admin_required
def users():
    """Admin users list"""
    response = nats_request('admin.users.list', {
        'page': request.args.get('page', 1, type=int),
        'limit': 20
    })
    
    users = response.get('data', {}).get('users', [])
    pagination = response.get('data', {}).get('pagination', {})
    
    return render_template('users.html', users=users, pagination=pagination)

@app.route('/services')
@login_required
@admin_required
def services():
    """Service status page"""
    response = nats_request('admin.services.status', {})
    services = response.get('data', {}).get('services', [])
    
    return render_template('services.html', services=services)

@app.route('/audit')
@login_required
@admin_required
def audit_logs():
    """Audit logs"""
    response = nats_request('admin.audit.list', {
        'page': request.args.get('page', 1, type=int),
        'limit': 50
    })
    
    logs = response.get('data', {}).get('logs', [])
    pagination = response.get('data', {}).get('pagination', {})
    
    return render_template('audit_logs.html', logs=logs, pagination=pagination)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)