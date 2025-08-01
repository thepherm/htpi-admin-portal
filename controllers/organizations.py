"""
Organizations Controller
"""
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from models import db, Organization
from forms import OrganizationForm

logger = logging.getLogger(__name__)

organizations_bp = Blueprint('organizations', __name__, url_prefix='/organizations')

@organizations_bp.route('/')
@login_required
def index():
    """List organizations"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    
    organizations = []
    total = 0
    
    try:
        # Get organizations from admin service via NATS
        nats = current_app.nats
        response = nats.request('admin.organizations.list', {
            'page': page,
            'limit': per_page
        })
        
        if response.get('success'):
            data = response.get('data', {})
            organizations = data.get('organizations', [])
            total = data.get('total', 0)
            
            # Cache organizations locally
            for org_data in organizations:
                org = Organization.query.get(org_data['id'])
                if not org:
                    org = Organization(id=org_data['id'])
                
                org.name = org_data['name']
                org.type = org_data['type']
                org.status = org_data['status']
                db.session.add(org)
            
            db.session.commit()
            logger.info(f"Retrieved {len(organizations)} organizations")
        else:
            logger.error(f"Failed to get organizations: {response.get('error')}")
            flash('Failed to load organizations', 'error')
            
    except Exception as e:
        logger.error(f"Error fetching organizations: {e}")
        # Fallback to cached data
        orgs_query = Organization.query.paginate(page=page, per_page=per_page)
        organizations = [{'id': o.id, 'name': o.name, 'type': o.type, 'status': o.status} 
                        for o in orgs_query.items]
        total = orgs_query.total
    
    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('organizations/index.html', 
                         organizations=organizations,
                         page=page,
                         total_pages=total_pages,
                         total=total)

@organizations_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Create new organization"""
    form = OrganizationForm()
    
    if form.validate_on_submit():
        try:
            # Create organization via NATS
            nats = current_app.nats
            response = nats.request('admin.organizations.create', {
                'name': form.name.data,
                'type': form.type.data,
                'contact_email': form.contact_email.data,
                'contact_phone': form.contact_phone.data,
                'address': form.address.data
            })
            
            if response.get('success'):
                flash('Organization created successfully', 'success')
                logger.info(f"Created organization: {form.name.data}")
                return redirect(url_for('organizations.index'))
            else:
                flash(f"Failed to create organization: {response.get('error')}", 'error')
                
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            flash('Failed to create organization', 'error')
    
    return render_template('organizations/form.html', form=form, title="New Organization")

@organizations_bp.route('/<org_id>')
@login_required
def view(org_id):
    """View organization details"""
    organization = None
    
    try:
        # Get organization details via NATS
        nats = current_app.nats
        response = nats.request('admin.organizations.get', {
            'organization_id': org_id
        })
        
        if response.get('success'):
            organization = response.get('data')
        else:
            logger.error(f"Failed to get organization {org_id}: {response.get('error')}")
            flash('Organization not found', 'error')
            return redirect(url_for('organizations.index'))
            
    except Exception as e:
        logger.error(f"Error fetching organization {org_id}: {e}")
        # Try cached data
        org = Organization.query.get(org_id)
        if org:
            organization = {
                'id': org.id,
                'name': org.name,
                'type': org.type,
                'status': org.status,
                'created_at': org.created_at
            }
        else:
            flash('Organization not found', 'error')
            return redirect(url_for('organizations.index'))
    
    return render_template('organizations/view.html', organization=organization)