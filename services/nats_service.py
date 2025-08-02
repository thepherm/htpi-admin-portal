"""
NATS Service for Flask Application
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional
import nats
from nats.errors import TimeoutError as NATSTimeoutError

logger = logging.getLogger(__name__)

class NATSService:
    """NATS client service for Flask"""
    
    def __init__(self, app=None):
        self.app = app
        self.nc = None
        self.loop = None
        self._connected = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        self.nats_url = app.config.get('NATS_URL', 'nats://localhost:4222')
        self.nats_user = app.config.get('NATS_USER', 'admin')
        self.nats_password = app.config.get('NATS_PASS', 'htpi_nats_dev')
        
    def connect(self):
        """Connect to NATS server"""
        if self._connected:
            return
            
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Run connection in the loop
            self.loop.run_until_complete(self._connect())
            self._connected = True
            logger.info(f"Connected to NATS at {self.nats_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self._connected = False
            raise
    
    async def _connect(self):
        """Async connection to NATS"""
        self.nc = await nats.connect(
            servers=[self.nats_url],
            user=self.nats_user,
            password=self.nats_password,
            reconnect_time_wait=2,
            max_reconnect_attempts=10
        )
    
    def disconnect(self):
        """Disconnect from NATS"""
        if self.nc and self._connected:
            self.loop.run_until_complete(self.nc.close())
            self._connected = False
            logger.info("Disconnected from NATS")
    
    def is_connected(self):
        """Check if connected to NATS"""
        return self._connected and self.nc and not self.nc.is_closed
    
    def request(self, subject: str, data: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
        """Send request to NATS and wait for response"""
        if not self.is_connected():
            raise RuntimeError("Not connected to NATS")
            
        try:
            # Run async request in event loop
            response = self.loop.run_until_complete(
                self._request(subject, data, timeout)
            )
            return response
            
        except NATSTimeoutError:
            logger.error(f"NATS request timeout for subject: {subject}")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"NATS request failed for {subject}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _request(self, subject: str, data: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        """Async NATS request"""
        message = json.dumps(data).encode()
        
        try:
            response = await self.nc.request(subject, message, timeout=timeout)
            return json.loads(response.data.decode())
        except Exception as e:
            logger.error(f"Error in NATS request: {e}")
            raise
    
    def publish(self, subject: str, data: Dict[str, Any]):
        """Publish message to NATS"""
        if not self.is_connected():
            raise RuntimeError("Not connected to NATS")
            
        try:
            self.loop.run_until_complete(self._publish(subject, data))
        except Exception as e:
            logger.error(f"NATS publish failed for {subject}: {e}")
            raise
    
    async def _publish(self, subject: str, data: Dict[str, Any]):
        """Async NATS publish"""
        message = json.dumps(data).encode()
        await self.nc.publish(subject, message)
        logger.debug(f"Published to {subject}")
    
    def __del__(self):
        """Cleanup on deletion"""
        if self._connected:
            self.disconnect()