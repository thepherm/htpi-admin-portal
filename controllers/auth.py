"""
Authentication Controller
"""
import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse

from models import db, User
from forms import LoginForm

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Try to authenticate via NATS first
        try:
            nats = current_app.nats
            response = nats.request('admin.auth.login', {
                'email': form.email.data,
                'password': form.password.data
            })
            
            if response.get('success'):
                # Update or create local user
                user = User.query.filter_by(email=form.email.data).first()
                if not user:
                    user = User(
                        email=form.email.data,
                        name=response['data']['user']['name'],
                        role=response['data']['user']['role']
                    )
                    db.session.add(user)
                
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                login_user(user, remember=form.remember_me.data)
                logger.info(f"User {user.email} logged in successfully")
                
                next_page = request.args.get('next')
                if not next_page or url_parse(next_page).netloc != '':
                    next_page = url_for('dashboard.index')
                return redirect(next_page)
            else:
                flash('Invalid email or password', 'error')
                logger.warning(f"Failed login attempt for {form.email.data}")
                
        except Exception as e:
            logger.error(f"NATS authentication error: {e}")
            # Fallback to local authentication
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                login_user(user, remember=form.remember_me.data)
                logger.info(f"User {user.email} logged in via local auth")
                
                next_page = request.args.get('next')
                if not next_page or url_parse(next_page).netloc != '':
                    next_page = url_for('dashboard.index')
                return redirect(next_page)
            else:
                flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logger.info(f"User {current_user.email} logged out")
    
    # Notify NATS about logout
    try:
        nats = current_app.nats
        nats.publish('admin.auth.logout', {
            'user_id': current_user.id,
            'email': current_user.email
        })
    except Exception as e:
        logger.error(f"Failed to notify NATS about logout: {e}")
    
    logout_user()
    return redirect(url_for('auth.login'))