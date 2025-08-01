"""
Services Controller
"""
import logging
from flask import Blueprint, render_template, current_app
from flask_login import login_required

logger = logging.getLogger(__name__)

services_bp = Blueprint('services', __name__, url_prefix='/services')

@services_bp.route('/')
@login_required
def index():
    """Services status page"""
    services = {}
    
    try:
        # Get service status via NATS
        nats = current_app.nats
        response = nats.request('admin.services.status', {})
        
        if response.get('success'):
            services = response.get('data', {})
            logger.info("Service status retrieved successfully")
        else:
            logger.error(f"Failed to get service status: {response.get('error')}")
            
    except Exception as e:
        logger.error(f"Error fetching service status: {e}")
        # Default service list
        services = {
            'gateway': {'healthy': False, 'message': 'Unable to connect'},
            'admin': {'healthy': False, 'message': 'Unable to connect'},
            'patient': {'healthy': False, 'message': 'Unable to connect'},
            'insurance': {'healthy': False, 'message': 'Unable to connect'},
            'form': {'healthy': False, 'message': 'Unable to connect'},
            'claim': {'healthy': False, 'message': 'Unable to connect'}
        }
    
    return render_template('services/index.html', services=services)