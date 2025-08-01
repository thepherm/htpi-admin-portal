"""
HTPI Admin Portal - Flask Application
"""
import os
import logging
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import db, User
from controllers import auth_bp, dashboard_bp, organizations_bp, services_bp
from services.nats_service import NATSService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    csrf = CSRFProtect(app)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Initialize NATS service
    nats_service = NATSService(app)
    app.nats = nats_service
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(services_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default admin user if it doesn't exist
        admin = User.query.filter_by(email='admin@htpi.com').first()
        if not admin:
            admin = User(
                email='admin@htpi.com',
                name='System Administrator',
                role='admin'
            )
            admin.set_password('changeme123')
            db.session.add(admin)
            db.session.commit()
            logger.info("Created default admin user")
    
    @app.before_request
    def before_request():
        """Connect to NATS before each request"""
        if not hasattr(app, 'nats') or not app.nats.is_connected():
            try:
                app.nats.connect()
            except Exception as e:
                logger.error(f"Failed to connect to NATS: {e}")
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)