from flask import Flask
from flask_pymongo import PyMongo
from datetime import datetime

mongo = PyMongo()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('config.py')
    
    mongo.init_app(app)
    
    # Initialize default styles if none exist
    with app.app_context():
        if not mongo.db.style_settings.find_one():
            mongo.db.style_settings.insert_one({
                'primary_color': '#3498db',
                'background_color': '#f8f9fa',
                'font_family': 'Arial'
            })
    
    return app