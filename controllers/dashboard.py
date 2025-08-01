"""
Dashboard Controller
"""
import logging
from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Dashboard page"""
    stats = {
        'total_organizations': 0,
        'total_users': 0,
        'total_patients': 0,
        'total_claims': 0,
        'pending_claims': 0,
        'approved_claims': 0,
        'denied_claims': 0
    }
    
    try:
        # Get stats from admin service via NATS
        nats = current_app.nats
        response = nats.request('admin.stats.dashboard', {})
        
        if response.get('success'):
            stats.update(response.get('data', {}))
            logger.info("Dashboard stats retrieved successfully")
        else:
            logger.error(f"Failed to get dashboard stats: {response.get('error')}")
            
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        # Use default values or cached data
    
    return render_template('dashboard/index.html', stats=stats, user=current_user)