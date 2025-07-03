"""
Middleware for the Flask application
"""
from flask import request, Flask
import logManager

logging = logManager.logger.get_logger(__name__)


def register_middleware(app: Flask) -> None:
    """Register middleware with the Flask app"""
    
    @app.before_request
    def log_request_info():
        """Log incoming requests"""
        logging.debug(f"Request: {request.method} {request.url} from {request.remote_addr}")
    
    @app.after_request
    def log_response_info(response):
        """Log outgoing responses and add CORS headers"""
        logging.debug(f"Response: {response.status_code} for {request.method} {request.url}")
        
        # Add CORS headers
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    @app.errorhandler(400)
    def bad_request(error):
        from flask import jsonify
        return jsonify({"error": "Bad request", "message": str(error)}), 400
    
    @app.errorhandler(404)
    def not_found(error):
        from flask import jsonify
        return jsonify({"error": "Not found", "message": str(error)}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import jsonify
        return jsonify({"error": "Internal server error"}), 500
