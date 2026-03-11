from flask import Blueprint, request, jsonify
from app.utils.style_generator import generate_css
from app.utils.file_upload import handle_upload
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/save-styles', methods=['POST'])
def save_styles():
    data = request.get_json()
    mongo.db.style_settings.update_one({}, {'$set': {
        **data,
        'last_updated': datetime.now(timezone.utc)
    }})
    generate_css()  # Regenerate CSS
    return jsonify({'status': 'success'})

@admin_bp.route('/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
        
    result = handle_upload(request.files['file'])
    return jsonify(result)
from flask import Blueprint, request, jsonify, current_app
import os
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/update-site-style', methods=['POST'])
def update_site_style():
    """Main endpoint for style updates"""
    if not verify_admin():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    
    # Save to database
    current_app.mongo.db.style_settings.update_one(
        {}, 
        {'$set': {
            'colors': data.get('colors'),
            'fonts': data.get('fonts'),
            'last_updated': datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    # Regenerate CSS file
    generate_global_css(data)
    
    return jsonify({"status": "success", "css_url": url_for('static', filename='css/global.css?v=' + datetime.now().timestamp())})

@admin_bp.route('/get-current-styles', methods=['GET'])
def get_current_styles():
    """For loading existing styles into editor"""
    styles = current_app.mongo.db.style_settings.find_one() or {}
    return jsonify(styles)