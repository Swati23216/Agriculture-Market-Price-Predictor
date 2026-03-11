from flask import send_from_directory
from flask_socketio import SocketIO, emit, join_room
from flask import Flask, render_template, request, redirect, flash, session, url_for, jsonify, abort, make_response
from flask_pymongo import PyMongo
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from bson import ObjectId
from werkzeug.utils import secure_filename
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer
import uuid
from datetime import datetime, timezone
from datetime import datetime, timedelta, timezone  # Update this line
app = Flask(__name__, template_folder='app/templates')
app.secret_key = 'supersecretkey'
app.config.from_object(Config)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

mongo = PyMongo(app)
socketio = SocketIO(app, async_mode='eventlet')
# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls','mp3','mp4','m4a','mkv','avi','webm','wav','ogg','aac'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Email configuration
# Email configuration - update this in your Config class or directly
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'janawadeswati@gmail.com'  # Your Gmail
app.config['MAIL_PASSWORD'] = 'uvkh yhua unon hrqu'  # Use App Password, not regular password
app.config['MAIL_DEFAULT_SENDER'] = 'janawadeswati@gmail.com'
# Password reset token serializer
app.config['SECURITY_PASSWORD_SALT'] = 'super-secret-salt'  # Replace with a random salt
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Add this near the top with other configurations
if not mongo.db.email_settings.find_one():
    mongo.db.email_settings.insert_one({
        'admin_email': 'janawadeswati@gmail.com',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_username': 'janawadeswati@gmail.com',
        'smtp_password': 'uvkh yhua unon hrqu',  # Same as above
        'use_tls': True,
        'last_updated': datetime.now(timezone.utc)
    })


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data
        self.id = str(user_data['_id'])
        self.name = user_data.get('name', '')
        self.email = user_data.get('email', '')
        self.role = user_data.get('role', 'user')
        self.created_at = user_data.get('created_at',datetime.now(timezone.utc))
        self.profile_pic = user_data.get('profile_pic', '')
        self.phone = user_data.get('phone', '')
        self.bio = user_data.get('bio', '')
    
    def get_id(self):
        return self.id

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None
    
@app.route('/admin/email-settings', methods=['GET', 'POST'])
@login_required
def email_settings():
    if current_user.role != 'admin':
        abort(403)
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
                
            update_data = {
                'admin_email': data.get('admin_email'),
                'last_updated': datetime.now(timezone.utc)
            }
            
            # Only update password if provided (not blank)
            if data.get('smtp_password'):
                update_data['smtp_password'] = data.get('smtp_password')
            
            # Update database
            mongo.db.email_settings.update_one({}, {'$set': update_data}, upsert=True)
            
            # Update app config for current session
            app.config['MAIL_DEFAULT_SENDER'] = update_data['admin_email']
            if 'smtp_password' in update_data:
                app.config['MAIL_PASSWORD'] = update_data['smtp_password']
            
            return jsonify({
                'success': True, 
                'message': 'Email settings updated successfully'
            })
        except Exception as e:
            return jsonify({
                'success': False, 
                'message': f'Error updating email settings: {str(e)}'
            }), 500
    
    # GET request - return current settings
    settings = mongo.db.email_settings.find_one() or {}
    # Don't return password for security
    if 'smtp_password' in settings:
        settings.pop('smtp_password')
    return jsonify(settings)

# def send_email(to, subject, template, **kwargs):
#     try:
#         # Get current email settings from database
#         settings = mongo.db.email_settings.find_one() or {}
        
#         msg = MIMEMultipart()
#         msg['From'] = settings.get('admin_email', app.config['MAIL_DEFAULT_SENDER'])
#         msg['To'] = to
#         msg['Subject'] = subject

#         # Render both HTML and plain text versions
#         html = render_template(template + '.html', **kwargs)
#         text = render_template(template + '.txt', **kwargs)

#         # Attach both versions
#         part1 = MIMEText(text, 'plain')
#         part2 = MIMEText(html, 'html')

#         msg.attach(part1)
#         msg.attach(part2)

#         # Send the email using configured settings
#         with smtplib.SMTP(
#             settings.get('smtp_server', app.config['MAIL_SERVER']),
#             settings.get('smtp_port', app.config['MAIL_PORT'])
#         ) as server:
#             if settings.get('use_tls', app.config['MAIL_USE_TLS']):
#                 server.starttls()
#             server.login(
#                 settings.get('smtp_username', app.config['MAIL_USERNAME']),
#                 settings.get('smtp_password', app.config['MAIL_PASSWORD'])
#             )
#             server.send_message(msg)
        
#         return True
#     except Exception as e:
#         print(f"Error sending email: {str(e)}")
#         return False

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")  # All authenticated users join their room
        if current_user.role == 'admin':
            join_room('admin_dashboard')
            
@socketio.on('request_unread_count')
def handle_unread_count_request():
    if current_user.is_authenticated and current_user.role == 'admin':
        unread_count = mongo.db.messages.count_documents({'read': False})
        emit('update_unread_count', {'count': unread_count}, room=request.sid)

@socketio.on('message_read')
def handle_message_read(data):
    if current_user.is_authenticated and current_user.role == 'admin':
        # Mark messages as read when admin opens the chat
        mongo.db.messages.update_many(
            {'email': data['email'], 'read': False},
            {'$set': {'read': True}}
        )
        # Broadcast updated count to all admin dashboards
        unread_count = mongo.db.messages.count_documents({'read': False})
        emit('update_unread_count', {'count': unread_count}, room='admin_dashboard')

def initialize_defaults():
    # Existing initialization code...
    
    # Add default roles if they don't exist
    if not mongo.db.roles.find_one({'name': 'user'}):
        mongo.db.roles.insert_one({'name': 'user'})
    
    if not mongo.db.roles.find_one({'name': 'admin'}):
        mongo.db.roles.insert_one({'name': 'admin'})
    
    if not mongo.db.navbar_settings.find_one():
            mongo.db.navbar_settings.insert_one({
                'site_name': 'Rukmini Hospital',
                'site_logo': '',
                'nav_tab_1': 'Home', 'nav_url_1': '/',
                'nav_tab_2': 'About', 'nav_url_2': '/about',
                'nav_tab_3': 'Services', 'nav_url_3': '/services',
                'nav_tab_4': 'Doctors', 'nav_url_4': '/doctors',
                'nav_tab_5': 'Contact', 'nav_url_5': '/contact',
                'nav_tab_6': '', 'nav_url_6': '',
                'last_updated': datetime.now(timezone.utc)
            })

    # Rest of your existing initialization code...
    if not mongo.db.style_settings.find_one():
        mongo.db.style_settings.insert_one({
            'primary_color': '#4f46e5',
            'background_color': '#f3f4f6',
            'font_family': 'Inter, sans-serif',
            'text_color': '#1f2937',
            'button_bg': '#4f46e5',
            'button_text': '#ffffff',
            'last_updated':datetime.now(timezone.utc)
        })

    if not mongo.db.navbar_settings.find_one():
        mongo.db.navbar_settings.insert_one({
            'site_name': 'My Site',
            'site_logo': '',
            'nav_tab_1': 'Home', 'nav_url_1': '/',
            'nav_tab_2': 'About', 'nav_url_2': '/about',
            'nav_tab_3': '', 'nav_url_3': '',
            'nav_tab_4': '', 'nav_url_4': '',
            'nav_tab_5': '', 'nav_url_5': '',
            'nav_tab_6': '', 'nav_url_6': ''
        })

    if not mongo.db.page_content.find_one():
        mongo.db.page_content.insert_one({
            'home_title': 'Welcome to Rukmini Hospital',
            'home_subtitle': 'Providing exceptional healthcare services with compassion and excellence',
            'emergency_care_text': 'Our emergency department is staffed round the clock with experienced professionals ready to handle any medical crisis.',
            'technology_text': 'We invest in the latest medical technology to ensure accurate diagnoses and effective treatments.',
            'care_text': 'Your comfort and well-being are our top priorities. We tailor treatments to your individual needs.',
            'news_content': '<p>We are proud to announce our new cardiology wing, opening next month with state-of-the-art facilities.</p><p>Our hospital has been awarded the "Best Healthcare Provider" in the region for the third consecutive year.</p>',
            'about_title': 'About Rukmini Hospital',
            'history_text': 'Founded in 1985, Rukmini Hospital began as a small clinic with a vision to provide quality healthcare to the local community.',
            'mission_text': 'To deliver compassionate, accessible, high-quality healthcare services to all our patients.',
            'values_text': 'Patient-Centered Care\nClinical Excellence\nIntegrity and Transparency\nContinuous Improvement\nCommunity Engagement',
            'services_title': 'Our Services',
            'services_intro': 'We offer a comprehensive range of medical services delivered by skilled specialists.',
            'cardiology_text': 'Comprehensive heart care including diagnostic tests and rehabilitation programs.',
            'orthopedics_text': 'Treatment for bone and joint disorders, including joint replacement.',
            'neurology_text': 'Expert care for disorders of the nervous system.',
            'pediatrics_text': 'Specialized care for infants, children and adolescents.',
            'doctors_title': 'Our Medical Team',
            'doctors_intro': 'Meet our team of highly qualified and experienced doctors.',
            'doctor1_name': 'Dr. Rajesh Sharma',
            'doctor1_specialty': 'Cardiologist',
            'doctor1_bio': 'With over 20 years of experience in interventional cardiology.',
            'doctor2_name': 'Dr. Priya Patel',
            'doctor2_specialty': 'Neurologist',
            'doctor2_bio': 'Specializing in stroke management and neurodegenerative disorders.',
            'contact_title': 'Contact Us',
            'contact_intro': "We're here to help you with all your healthcare needs.",
            'address_text': '123 Health Avenue, Medical District, City - 560001',
            'phone_text': 'Emergency: +91 9876543210<br>Appointments: +91 1234567890',
            'footer_text': '© 2023 Agricultural Market Price npm . All Rights Reserved.',
            'last_updated': datetime.now(timezone.utc)
        })




def send_email(to, subject, template, **kwargs):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = to
        msg['Subject'] = subject

        # Render both HTML and plain text versions
        html = render_template(template + '.html', **kwargs)
        text = render_template(template + '.txt', **kwargs)

        # Attach both versions
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        msg.attach(part1)
        msg.attach(part2)

        # Send the email
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def generate_reset_token(email):
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])

def verify_reset_token(token, expiration=3600):
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
        return email
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return None

@app.route('/')
def home():
    return render_template('guest_home.html')

@app.route('/guest-home')
def guest_home():
    styles = mongo.db.style_settings.find_one() or {}
    navbar = mongo.db.navbar_settings.find_one() or {}
    content = mongo.db.page_content.find_one() or {}
    
    return render_template(
        'guest_home.html',
        styles=styles,
        navbar=navbar,
        content=content
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']  # Selected role from registration form

        # Validate inputs
        if not name or not email or not password or not role:
            flash('All fields are required!', 'danger')
            return redirect(url_for('register'))

        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return redirect(url_for('register'))

        # Check if email already exists
        existing_user = mongo.db.users.find_one({'email': email})
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        # Hash password
        hashed_pw = generate_password_hash(password)
        
        # All new registrations go to pending status
        pending_role = f'pending_{role}'
        
        # Create user document
        user_doc = {
            'name': name,
            'email': email,
            'password': hashed_pw,
            'role': pending_role,
            'created_at': datetime.now(timezone.utc),
            'profile_pic': '',
            'phone': '',
            'bio': '',
            'email_verified': False,
            'verification_token': secrets.token_urlsafe(32),
            'approved': False
        }

        # Insert new user
        try:
            user_id = mongo.db.users.insert_one(user_doc).inserted_id
        except Exception as e:
            flash('Registration failed. Please try again.', 'danger')
            return redirect(url_for('register'))

        # Notify admins about the new pending user
        admin_users = mongo.db.users.find({'role': 'admin'})
        for admin in admin_users:
            try:
                subject = "New User Approval Request"
                send_email(
                    admin['email'],
                    subject,
                    'email/new_user_notification',
                    admin_name=admin.get('name', 'Admin'),
                    user_name=name,
                    user_email=email,
                    user_role=role
                )
            except Exception as e:
                print(f"Failed to notify admin {admin['email']}: {e}")

        # Send confirmation email to user
        try:
            subject = "Registration Submitted for Approval"
            send_email(
                email,
                subject,
                'email/registration_submitted',
                name=name,
                role=role
            )
        except Exception as e:
            print(f"Failed to send confirmation email to {email}: {e}")

        flash('Your registration has been submitted and is awaiting admin approval. You will receive an email once your account is approved.', 'info')
        return redirect(url_for('guest_home'))

    # GET request - show registration form
    roles = list(mongo.db.roles.find())
    return render_template('register.html', roles=roles)



@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user_data = mongo.db.users.find_one({'email': email})
        if user_data and check_password_hash(user_data['password'], password):
            # Check if user is approved
            if user_data.get('role', '').startswith('pending_'):
                flash('Your account is still pending approval. Please wait for admin approval or contact support.', 'warning')
                return redirect(url_for('login_page'))
                
            user = User(user_data)
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('css_editor' if user_data['role'] == 'admin' else 'user_home'))
        
        flash("Invalid email or password.", "danger")
    
    return render_template("login.html")

@app.route('/admin/approve-user/<user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
    
    # Remove 'pending_' prefix from role
    new_role = user['role'].replace('pending_', '')
    
    # Update user to approved status
    mongo.db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {
            'role': new_role,
            'approved': True
        }}
    )
    
    # Send approval email using the configured email settings
    try:
        subject = "Your Account Has Been Approved"
        body = (
            f"Hello {user.get('name', 'User')},\n\n"
            f"Your account has been approved by the admin. You can now log in as a {new_role}.\n"
            f"Login here: {url_for('login_page', _external=True)}\n\n"
            f"Best regards,\nThe Team"
        )
        
        # Use the send_email function which will use the configured settings
        send_email(
            user['email'],
            subject,
            'email/account_approved',
            name=user.get('name', 'User'),
            role=new_role,
            login_url=url_for('login_page', _external=True)
        )
        
        return jsonify({
            'success': True,
            'message': f'User approved as {new_role} and notified by email!'
        })
    except Exception as e:
        return jsonify({
            'success': True,  # Still consider it a success, just email failed
            'message': f'User approved, but failed to send email: {e}'
        })


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = mongo.db.users.find_one({'email': email})
        if user:
            otp = str(randint(100000, 999999))
            expiry =datetime.now(timezone.utc) + timedelta(hours=3)
            mongo.db.users.update_one(
                {'email': email},
                {'$set': {'reset_otp': otp, 'reset_otp_expiry': expiry}}
            )
            send_otp_email(email, otp)
            session['reset_email'] = email  # <--- Add this line
        flash('If an account with that email exists, an OTP has been sent.', 'info')
        return redirect(url_for('reset_password_otp'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(request.url)
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return redirect(request.url)
        
        hashed_pw = generate_password_hash(password)
        mongo.db.users.update_one(
            {'email': email},
            {'$set': {'password': hashed_pw}}
        )
        
        flash('Your password has been updated! You can now login with your new password.', 'success')
        return redirect(url_for('login_page'))
    
    return render_template('reset_password.html', token=token)

@app.route('/user-home')
@login_required
def user_home():
    return render_template("user_home.html", name=current_user.name)

@app.route('/admin/css-editor')
@login_required
def css_editor():
    if current_user.role != 'admin':
        abort(403)
    
    # Ensure these always return a dictionary, even if empty
    styles = mongo.db.style_settings.find_one() or {}
    navbar = mongo.db.navbar_settings.find_one() or {}
    content = mongo.db.page_content.find_one() or {}
    email_settings = mongo.db.email_settings.find_one() or {}
    unread_count = mongo.db.messages.count_documents({'read': False})
    roles = list(mongo.db.roles.find())

    users = list(mongo.db.users.find())
    for user in users:
        user['_id'] = str(user['_id'])
        user['is_active'] = True

    now = datetime.now(timezone.utc)
    today = now.date()
    week_ago = now - timedelta(days=7)
    user_stats = {
        'total_users': mongo.db.users.count_documents({}),
        'active_today': mongo.db.users.count_documents({'created_at': {'$gte': datetime.combine(today, datetime.min.time())}}),
        'new_this_week': mongo.db.users.count_documents({'created_at': {'$gte': week_ago}}),
        'admin_users': mongo.db.users.count_documents({'role': 'admin'})
    }

    role_messages = list(mongo.db.admin_role_messages.find().sort('timestamp', -1)) or []
    for msg in role_messages:
        msg['_id'] = str(msg['_id'])
        msg['timestamp_str'] = msg['timestamp'].strftime('%Y-%m-%d %H:%M')
        user = mongo.db.users.find_one({'email': msg['user_email']}) or {}
        msg['user_role'] = user.get('role', 'N/A')
    
    pending_admins = list(mongo.db.users.find({'role': {'$regex': '^pending_'}})) or []
    for user in pending_admins:
        user['_id'] = str(user['_id'])

    return render_template(
        'admin/css_editor.html',
        styles=styles,
        navbar=navbar,
        content=content,
        unread_count=unread_count,
        roles=roles,
        users=users,
        user_stats=user_stats,
        role_messages=role_messages,
        role_messages_count=len(role_messages),
        pending_admins=pending_admins,
        email_settings=email_settings
    )
@app.route('/admin/preview')
@login_required
def admin_preview():
    if current_user.role != 'admin':
        abort(403)
    
    styles = mongo.db.style_settings.find_one()
    navbar = mongo.db.navbar_settings.find_one()
    content = mongo.db.page_content.find_one()
    return render_template("admin/preview.html", styles=styles, navbar=navbar, content=content)

@app.route('/admin/save-styles', methods=['POST'])
@login_required
def save_styles():
    if current_user.role != 'admin':
        abort(403)
    
    try:
        data = request.get_json()
        mongo.db.style_settings.update_one(
            {},
            {'$set': {
                'primary_color': data.get('primary_color'),
                'background_color': data.get('background_color'),
                'font_family': data.get('font_family'),
                'text_color': data.get('text_color'),
                'button_bg': data.get('button_bg'),
                'button_text': data.get('button_text'),
                'last_updated':datetime.now(timezone.utc)
            }},
            upsert=True
        )
        return jsonify({'success': True, 'message': 'Styles updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/save-navbar', methods=['POST'])
@login_required
def save_navbar():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        update_data = {
            'site_name': data.get('site_name', 'My Site'),
            'site_logo': data.get('site_logo', ''),
            'last_updated': datetime.now(timezone.utc)
        }
        
        for i in range(1, 7):
            update_data[f'nav_tab_{i}'] = data.get(f'nav_tab_{i}', '')
            update_data[f'nav_url_{i}'] = data.get(f'nav_url_{i}', '')

        mongo.db.navbar_settings.update_one(
            {},
            {'$set': update_data},
            upsert=True
        )
        
        return jsonify({
            'success': True,
            'message': 'Navigation updated successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error saving navigation: {str(e)}'
        }), 500

@app.route('/admin/save-content', methods=['POST'])
@login_required
def save_content():
    if current_user.role != 'admin':
        abort(403)
    
    try:
        data = request.get_json()
        mongo.db.page_content.update_one(
            {},
            {'$set': {
                'home_title': data.get('home_title'),
                'home_subtitle': data.get('home_subtitle'),
                'emergency_care_text': data.get('emergency_care_text'),
                'technology_text': data.get('technology_text'),
                'care_text': data.get('care_text'),
                'news_content': data.get('news_content'),
                'about_title': data.get('about_title'),
                'history_text': data.get('history_text'),
                'mission_text': data.get('mission_text'),
                'values_text': data.get('values_text'),
                'services_title': data.get('services_title'),
                'services_intro': data.get('services_intro'),
                'cardiology_text': data.get('cardiology_text'),
                'orthopedics_text': data.get('orthopedics_text'),
                'neurology_text': data.get('neurology_text'),
                'pediatrics_text': data.get('pediatrics_text'),
                'doctors_title': data.get('doctors_title'),
                'doctors_intro': data.get('doctors_intro'),
                'doctor1_name': data.get('doctor1_name'),
                'doctor1_specialty': data.get('doctor1_specialty'),
                'doctor1_bio': data.get('doctor1_bio'),
                'doctor2_name': data.get('doctor2_name'),
                'doctor2_specialty': data.get('doctor2_specialty'),
                'doctor2_bio': data.get('doctor2_bio'),
                'contact_title': data.get('contact_title'),
                'contact_intro': data.get('contact_intro'),
                'address_text': data.get('address_text'),
                'phone_text': data.get('phone_text'),
                'footer_text': data.get('footer_text'),
                'last_updated': datetime.now(timezone.utc)
            }},
            upsert=True
        )
        return jsonify({'success': True, 'message': 'Content updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    try:
        user_id = ObjectId(current_user.id)
        update_data = {
            'name': request.form.get('name'),
            'phone': request.form.get('phone'),
            'bio': request.form.get('bio')
        }

        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                user = mongo.db.users.find_one({'_id': user_id})
                if user and user.get('profile_pic'):
                    try:
                        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], user['profile_pic'])
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    except Exception as e:
                        print(f"Error deleting old profile picture: {e}")

                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"user_{user_id}.{ext}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                update_data['profile_pic'] = filename

        mongo.db.users.update_one(
            {'_id': user_id},
            {'$set': update_data}
        )

        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    
    except Exception as e:
        print(f"Error in update_profile: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
                
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            
            if not current_password or not new_password:
                return jsonify({'success': False, 'message': 'Current and new password are required'}), 400
            
            user_data = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
            if not user_data:
                return jsonify({'success': False, 'message': 'User not found'}), 404
                
            if not check_password_hash(user_data['password'], current_password):
                return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
            
            if len(new_password) < 8:
                return jsonify({
                    'success': False,
                    'message': 'Password must be at least 8 characters long'
                }), 400
            
            hashed_pw = generate_password_hash(new_password)
            result = mongo.db.users.update_one(
                {'_id': ObjectId(current_user.id)},
                {'$set': {'password': hashed_pw}}
            )
            
            if result.modified_count == 1:
                logout_user()
                return jsonify({
                    'success': True, 
                    'message': 'Password updated successfully. Please login again.'
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': 'Failed to update password'
                }), 500
                
        except Exception as e:
            app.logger.error(f"Error changing password: {str(e)}")
            return jsonify({
                'success': False, 
                'message': 'An error occurred while changing password'
            }), 500
    
    return render_template('change_password.html')

@app.context_processor
def inject_common_vars():
    navbar = mongo.db.navbar_settings.find_one() or {
        'site_name': 'My Site',
        'site_logo': '',
        'nav_tab_1': 'Home', 'nav_url_1': '/',
        'nav_tab_2': 'About', 'nav_url_2': '/about',
        'nav_tab_3': '', 'nav_url_3': '',
        'nav_tab_4': '', 'nav_url_4': '',
        'nav_tab_5': '', 'nav_url_5': '',
        'nav_tab_6': '', 'nav_url_6': ''
    }
    
    styles = mongo.db.style_settings.find_one() or {
        'primary_color': '#4f46e5',
        'background_color': '#f3f4f6',
        'font_family': 'Inter, sans-serif',
        'text_color': '#1f2937',
        'button_bg': '#4f46e5',
        'button_text': '#ffffff'
    }
    
    content = mongo.db.page_content.find_one() or {
        'home_title': 'Welcome to Rukmini Hospital',
        'home_subtitle': 'Providing exceptional healthcare services with compassion and excellence',
        'emergency_care_text': 'Our emergency department is staffed round the clock with experienced professionals ready to handle any medical crisis.',
        'technology_text': 'We invest in the latest medical technology to ensure accurate diagnoses and effective treatments.',
        'care_text': 'Your comfort and well-being are our top priorities. We tailor treatments to your individual needs.',
        'news_content': '<p>We are proud to announce our new cardiology wing, opening next month with state-of-the-art facilities.</p><p>Our hospital has been awarded the "Best Healthcare Provider" in the region for the third consecutive year.</p>',
        'about_title': 'About Rukmini Hospital',
        'history_text': 'Founded in 1985, Rukmini Hospital began as a small clinic with a vision to provide quality healthcare to the local community.',
        'mission_text': 'To deliver compassionate, accessible, high-quality healthcare services to all our patients.',
        'values_text': 'Patient-Centered Care\nClinical Excellence\nIntegrity and Transparency\nContinuous Improvement\nCommunity Engagement',
        'services_title': 'Our Services',
        'services_intro': 'We offer a comprehensive range of medical services delivered by skilled specialists.',
        'cardiology_text': 'Comprehensive heart care including diagnostic tests and rehabilitation programs.',
        'orthopedics_text': 'Treatment for bone and joint disorders, including joint replacement.',
        'neurology_text': 'Expert care for disorders of the nervous system.',
        'pediatrics_text': 'Specialized care for infants, children and adolescents.',
        'doctors_title': 'Our Medical Team',
        'doctors_intro': 'Meet our team of highly qualified and experienced doctors.',
        'doctor1_name': 'Dr. Rajesh Sharma',
        'doctor1_specialty': 'Cardiologist',
        'doctor1_bio': 'With over 20 years of experience in interventional cardiology.',
        'doctor2_name': 'Dr. Priya Patel',
        'doctor2_specialty': 'Neurologist',
        'doctor2_bio': 'Specializing in stroke management and neurodegenerative disorders.',
        'contact_title': 'Contact Us',
        'contact_intro': "We're here to help you with all your healthcare needs.",
        'address_text': '123 Health Avenue, Medical District, City - 560001',
        'phone_text': 'Emergency: +91 9876543210<br>Appointments: +91 1234567890',
        'footer_text': '© 2023 Agricultural Market Price Prediction. All Rights Reserved.'
    }
    
    return {
        'navbar': navbar,
        'styles': styles,
        'content': content,
        'current_year': datetime.now().year
    }

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('guest_home'))
from random import randint

def send_otp_email(to, otp):
    subject = "Your Password Reset OTP"
    body = f"Your OTP for password reset is: {otp}\nThis OTP is valid for 3 hours."
    msg = MIMEMultipart()
    msg['From'] = app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending OTP email: {e}")
        return False

def send_otp_email(to, otp):
    subject = "Your Password Reset OTP"
    body = f"Your OTP for password reset is: {otp}\nThis OTP is valid for 3 hours."
    msg = MIMEMultipart()
    msg['From'] = app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending OTP email: {e}")
        return False

@app.route('/reset-password-otp', methods=['GET', 'POST'])
def reset_password_otp():
    email = session.get('reset_email')
    if not email:
        flash('Session expired. Please request a new OTP.', 'danger')
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        otp = request.form.get('otp')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        user = mongo.db.users.find_one({'email': email})
        if not user:
            flash('Invalid email or OTP.', 'danger')
            return redirect(request.url)
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(request.url)
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return redirect(request.url)
        if 'reset_otp' not in user or 'reset_otp_expiry' not in user:
            flash('No OTP found. Please request a new one.', 'danger')
            return redirect(url_for('forgot_password'))
        if user['reset_otp'] != otp:
            flash('Invalid OTP.', 'danger')
            return redirect(request.url)
        if datetime.now(timezone.utc)> user['reset_otp_expiry']:
            flash('OTP has expired. Please request a new one.', 'danger')
            return redirect(url_for('forgot_password'))
        hashed_pw = generate_password_hash(password)
        mongo.db.users.update_one(
            {'email': email},
            {'$set': {'password': hashed_pw},
             '$unset': {'reset_otp': "", 'reset_otp_expiry': ""}}
        )
        flash('Your password has been updated! You can now login with your new password.', 'success')
        return redirect(url_for('login_page'))
    return render_template('reset_password_otp.html')
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user




from datetime import datetime

@app.route('/admin/messages')
@login_required
def admin_messages():
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)
    # Mark all unread messages as read when admin opens the page (optional)
    # mongo.db.messages.update_many({'read': False}, {'$set': {'read': True}})
    user_emails = mongo.db.messages.distinct('email')
    messages = []
    for email in user_emails:
        user_msgs = list(mongo.db.messages.find({'email': email}).sort('timestamp', 1))
        replies = list(mongo.db.admin_replies.find({'email': email}).sort('timestamp', 1))
        chat = [
            {'type': 'user', 'text': m['message'], 'timestamp': m['timestamp']}
            for m in user_msgs
        ] + [
            {'type': 'admin', 'text': r['reply'], 'timestamp': r['timestamp']}
            for r in replies
        ]
        chat.sort(key=lambda x: x['timestamp'])
        last_msg = user_msgs[-1] if user_msgs else None
        unread_count = mongo.db.messages.count_documents({'email': email, 'read': False})
        messages.append({
            'email': email,
            'chat': chat,
            'timestamp': last_msg['timestamp'] if last_msg else None,
            'unread_count': unread_count
        })
    # Sort contacts by latest message time (descending)
    messages.sort(key=lambda x: x['timestamp'] or datetime.min, reverse=True)
    return render_template('admin/messages.html', messages=messages)


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        abort(403)
    # return render_template('admin/dashboard.html')
    return redirect(url_for('admin/dashboard.html'))

@login_required
def admin_reply_message():
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)
    email = request.form.get('email')
    reply = request.form.get('reply')
    if not email or not reply:
        flash('Email and reply message are required.', 'danger')
        return redirect(url_for('admin_messages'))
    # Send reply email
    subject = "Reply from Admin"
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(reply, 'plain'))
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        flash('Reply sent successfully!', 'success')
    except Exception as e:
        flash(f'Failed to send reply: {e}', 'danger')
    return redirect(url_for('admin_messages'))

@app.route('/admin/pending-admins')
@login_required
def pending_admins():
    if current_user.role != 'admin':
        abort(403)
    # Get all users with roles starting with 'pending_'
    pending_admins = list(mongo.db.users.find({'role': {'$regex': '^pending_'}}))
    return render_template('admin/pending_admins.html', pending_admins=pending_admins)


@app.route('/admin/approve-admin/<user_id>', methods=['POST'])
@login_required
def approve_admin(user_id):
    if current_user.role != 'admin':
        abort(403)
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('pending_admins'))
    mongo.db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'role': 'admin'}})
    # Send approval email
    try:
        subject = "Your Admin Request Has Been Approved"
        body = f"Hello {user.get('name', '')},\n\nCongratulations! Your request to become an admin has been approved. You can now log in with admin privileges.\n\nBest regards,\nThe Team"
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = user['email']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        flash('Admin approved and notified by email!', 'success')
    except Exception as e:
        flash(f'Admin approved, but failed to send email: {e}', 'warning')
    return redirect(url_for('pending_admins'))
from bson import ObjectId

@app.route('/admin/roles', methods=['GET', 'POST'])
@login_required
def manage_roles():
    if current_user.role != 'admin':
        abort(403)
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'message': 'Role name required.'})
        if mongo.db.roles.find_one({'name': name}):
            return jsonify({'success': False, 'message': 'Role already exists.'})
        mongo.db.roles.insert_one({'name': name})
        return jsonify({'success': True, 'message': 'Role added successfully.'})
    # GET: return all roles
    roles = list(mongo.db.roles.find())
    for role in roles:
        role['_id'] = str(role['_id'])
    return jsonify({'roles': roles})

@app.route('/admin/roles/<role_id>', methods=['DELETE'])
@login_required
def delete_role(role_id):
    if current_user.role != 'admin':
        abort(403)
    mongo.db.roles.delete_one({'_id': ObjectId(role_id)})
    return jsonify({'success': True, 'message': 'Role deleted.'})
# ...existing code...
from werkzeug.utils import secure_filename


@app.route('/admin/communication', methods=['POST'])
@login_required
def admin_communication():
    if current_user.role != 'admin':
        abort(403)

    role = request.form.get('role')
    subject = request.form.get('subject') or "Message from Admin"
    message = request.form.get('message')
    file = request.files.get('attachment')

    if not role or not message:
        flash('Role and message are required.', 'danger')
        return redirect(url_for('css_editor'))

    users = list(mongo.db.users.find({'role': role}))
    if not users:
        flash('No users found with the selected role.', 'warning')
        return redirect(url_for('css_editor'))

    # Get email settings from database
    email_settings = mongo.db.email_settings.find_one() or {}
    
    # Handle file upload
    attachment_path = None
    attachment_filename = None
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        attachment_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(attachment_path)
        attachment_filename = filename

    sent_count = 0
    failed_emails = []

    # Create SMTP connection once and reuse it
    try:
        smtp_server = email_settings.get('smtp_server', app.config['MAIL_SERVER'])
        smtp_port = email_settings.get('smtp_port', app.config['MAIL_PORT'])
        smtp_username = email_settings.get('smtp_username', app.config['MAIL_USERNAME'])
        smtp_password = email_settings.get('smtp_password', app.config['MAIL_PASSWORD'])
        use_tls = email_settings.get('use_tls', app.config['MAIL_USE_TLS'])

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_username, smtp_password)

            for user in users:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = email_settings.get('admin_email', app.config['MAIL_DEFAULT_SENDER'])
                    msg['To'] = user['email']
                    msg['Subject'] = subject
                    msg.attach(MIMEText(message, 'plain'))

                    if attachment_path:
                        with open(attachment_path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={attachment_filename}",
                        )
                        msg.attach(part)

                    server.send_message(msg)
                    sent_count += 1

                    # Save to admin_role_messages collection
                    mongo.db.admin_role_messages.insert_one({
                        'user_id': user['_id'],
                        'user_email': user['email'],
                        'subject': subject,
                        'message': message,
                        'attachment': attachment_filename if attachment_filename else None,
                        'timestamp': datetime.now(timezone.utc),
                        'read': False
                    })

                    # Emit socket event to the specific user
                    socketio.emit('new_admin_message', {
                        'message': message,
                        'subject': subject
                    }, room=f"user_{user['_id']}")

                except Exception as e:
                    print(f"Failed to send to {user['email']}: {e}")
                    failed_emails.append(user['email'])

    except Exception as e:
        print(f"SMTP connection error: {e}")
        flash(f"Failed to establish email connection: {e}", "danger")
        return redirect(url_for('css_editor'))

    # Clean up attachment if it exists
    if attachment_path and os.path.exists(attachment_path):
        try:
            os.remove(attachment_path)
        except Exception as e:
            print(f"Error removing attachment: {e}")

    if sent_count > 0:
        flash(f"Message sent to {sent_count} user(s) with role '{role}'.", "success")
    if failed_emails:
        flash(f"Failed to send to {len(failed_emails)} users.", "warning")

    return redirect(url_for('css_editor'))
# ...existing code...




@app.route('/download/admin-message/<filename>')
@login_required
def download_admin_message(filename):
    # Only allow download if the user has a message with this attachment
    message = mongo.db.admin_role_messages.find_one({
        'user_email': current_user.email,
        'attachment': filename
    })
    if not message:
        abort(403)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# ...existing code...
@app.route('/user/admin-messages')
@login_required
def user_admin_messages():
    # Fetch all admin messages for this user
    messages = list(mongo.db.admin_role_messages.find({'user_email': current_user.email}).sort('timestamp', -1))
    return render_template('user_admin_messages.html', messages=messages)
# ...existing code...


@app.route('/user-message', methods=['GET', 'POST'])
@login_required
def user_message():
    if request.method == 'POST':
        message = request.form.get('message')
        if not message or len(message.strip()) == 0:
            flash('Message cannot be empty.', 'danger')
            return redirect(url_for('user_message'))
        mongo.db.messages.insert_one({
            'user_id': current_user.get_id(),
            'email': current_user.email,
            'message': message.strip(),
            'timestamp': datetime.now(timezone.utc),
            'read': False
        })
        flash('Message sent successfully!', 'success')
        return redirect(url_for('user_message'))

    # Fetch all messages and replies for this user
    user_email = current_user.email
    messages = list(mongo.db.messages.find({'email': user_email}).sort('timestamp', 1))
    replies = list(mongo.db.admin_replies.find({'email': user_email}).sort('timestamp', 1))
    # Merge and sort by timestamp
    chat = [
        {'type': 'user', 'text': m['message'], 'timestamp': m['timestamp']}
        for m in messages
    ] + [
        {'type': 'admin', 'text': r['reply'], 'timestamp': r['timestamp']}
        for r in replies
    ]
    chat.sort(key=lambda x: x['timestamp'])
    return render_template('user_message.html', chat=chat,now=datetime.now(timezone.utc))

    
@app.route('/admin/reply-message', methods=['POST'])
@login_required
def admin_reply_message():
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)
    email = request.form.get('email')
    reply = request.form.get('reply')
    if not email or not reply:
        flash('Email and reply message are required.', 'danger')
        return redirect(url_for('admin_messages'))
    # Save reply in DB for chat display
    mongo.db.admin_replies.insert_one({
        'email': email,
        'reply': reply,
        'timestamp': datetime.now(timezone.utc)
    })
    # Send reply email
    subject = "Reply from Admin"
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(reply, 'plain'))
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        flash('Reply sent successfully!', 'success')
    except Exception as e:
        flash(f'Failed to send reply: {e}', 'danger')
    return redirect(url_for('admin_messages'))
@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)


@socketio.on('send_message')
def handle_send_message(data):
    # Save message to DB
    mongo.db.messages.insert_one({
        'user_id': data.get('user_id'),
        'email': data.get('email'),
        'message': data.get('message'),
        'timestamp': datetime.now(timezone.utc),
        'read': False
    })
    
    # Emit to user's room
    emit('receive_message', {
        'type': 'user',
        'text': data.get('message'),
        'timestamp':datetime.now(timezone.utc).strftime('%I:%M %p'),
        'room': data['room']
    }, room=data['room'])
    
    # Emit to admin_notifications room
    emit('admin_new_message', {
        'email': data.get('email'),
        'message': data.get('message'),
        'timestamp':datetime.now(timezone.utc).strftime('%I:%M %p')
    }, room='admin_notifications')
    
    # Update unread count for all admins
    unread_count = mongo.db.messages.count_documents({'read': False})
    emit('update_unread_count', {'count': unread_count}, room='admin_dashboard')


# @app.route('/admin/mark-messages-read/<email>', methods=['POST'])
# @login_required
# def mark_messages_read(email):
#     if current_user.role != 'admin':
#         abort(403)
#     mongo.db.messages.update_many({'email': email, 'read': False}, {'$set': {'read': True}})
#     return jsonify({'success': True})
@app.route('/admin/mark-messages-read/<email>', methods=['POST'])
@login_required
def mark_messages_read(email):
    if current_user.role != 'admin':
        abort(403)
    mongo.db.messages.update_many(
        {'email': email, 'read': False}, 
        {'$set': {'read': True}}
    )
    # Emit updated count
    unread_count = mongo.db.messages.count_documents({'read': False})
    socketio.emit('update_unread_count', {'count': unread_count}, room='admin_dashboard')
    return jsonify({'success': True})

@socketio.on('send_admin_reply')
def handle_send_admin_reply(data):
    # Save admin reply to DB
    mongo.db.admin_replies.insert_one({
        'email': data.get('email'),
        'reply': data.get('reply'),
        'timestamp': datetime.now(timezone.utc)
    })
    emit('receive_message', {
        'type': 'admin',
        'text': data.get('reply'),
        'timestamp': datetime.now(timezone.utc).strftime('%I:%M %p')
    }, room=data['room'])

@app.route('/get-unread-admin-messages-count')
@login_required
def get_unread_admin_messages_count():
    count = mongo.db.admin_role_messages.count_documents({
        'user_email': current_user.email,
        'read': False
    })
    return jsonify({'count': count})

@app.route('/mark-admin-messages-read', methods=['POST'])
@login_required
def mark_admin_messages_read():
    mongo.db.admin_role_messages.update_many(
        {'user_email': current_user.email, 'read': False},
        {'$set': {'read': True}}
    )
    return jsonify({'success': True})
@app.route('/admin/roles/<role_id>', methods=['PUT'])
@login_required
def update_role(role_id):
    if current_user.role != 'admin':
        abort(403)
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Role name required.'})
    # Prevent duplicate role names
    if mongo.db.roles.find_one({'name': name, '_id': {'$ne': ObjectId(role_id)}}):
        return jsonify({'success': False, 'message': 'Role already exists.'})
    result = mongo.db.roles.update_one({'_id': ObjectId(role_id)}, {'$set': {'name': name}})
    if result.modified_count:
        return jsonify({'success': True, 'message': 'Role updated.'})
    else:
        return jsonify({'success': False, 'message': 'No changes made.'})

@app.route('/admin/crops')
@login_required
def manage_crops():
    if current_user.role != 'admin':
        abort(403)
    
    crops = list(mongo.db.crops.find().sort('name', 1))
    # Convert ObjectId to string for JSON serialization
    for crop in crops:
        crop['_id'] = str(crop['_id'])
    return jsonify(crops)

@app.route('/admin/getcrops')
@login_required
def get_crops():
    if current_user.role != 'admin':
        abort(403)
    
    crops = list(mongo.db.crops.find().sort('name', 1))
    # Convert ObjectId to string for JSON serialization
    for crop in crops:
        crop['_id'] = str(crop['_id'])
    return jsonify({'success': True, 'crops': crops})
    
@app.route('/admin/crops/add', methods=['POST'])
@login_required
def add_crop():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Handle both JSON and form-data (for file uploads)
        if request.is_json:
            data = request.get_json()
            image_url = data.get('image', '')
        else:
            data = request.form.to_dict()
            image_url = ''
            
            # Handle file upload if present
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"crop_{datetime.now().timestamp()}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    image_url = url_for('uploaded_file', filename=filename, _external=True)
        
        # Validate required fields
        if not data.get('name') or not data.get('season'):
            return jsonify({'success': False, 'message': 'Name and season are required'}), 400
        
        # Check if crop already exists
        existing_crop = mongo.db.crops.find_one({'name': data['name']})
        if existing_crop:
            return jsonify({'success': False, 'message': 'Crop with this name already exists'}), 400
        
        # Create new crop document
        crop_data = {
            'name': data['name'],
            'season': data['season'],
            'area': data.get('area', ''),
            'image': image_url or data.get('image', ''),
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Insert into MongoDB
        result = mongo.db.crops.insert_one(crop_data)
        
        # Get the newly created crop to return
        new_crop = mongo.db.crops.find_one({'_id': result.inserted_id})
        new_crop['_id'] = str(new_crop['_id'])
        
        return jsonify({
            'success': True,
            'message': 'Crop added successfully',
            'crop': new_crop
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error adding crop: {str(e)}'
        }), 500

@app.route('/admin/crops/<crop_id>', methods=['PUT'])
@login_required
def update_crop(crop_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Handle both JSON and form-data (for file uploads)
        if request.is_json:
            data = request.get_json()
            image_url = data.get('image', '')
        else:
            data = request.form.to_dict()
            image_url = ''
            
            # Handle file upload if present
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"crop_{datetime.now().timestamp()}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    image_url = url_for('uploaded_file', filename=filename, _external=True)
        
        # Validate required fields
        if not data.get('name') or not data.get('season'):
            return jsonify({'success': False, 'message': 'Name and season are required'}), 400
        
        # Check if crop exists
        crop = mongo.db.crops.find_one({'_id': ObjectId(crop_id)})
        if not crop:
            return jsonify({'success': False, 'message': 'Crop not found'}), 404
        
        # Check if another crop with the same name exists
        existing_crop = mongo.db.crops.find_one({
            'name': data['name'],
            '_id': {'$ne': ObjectId(crop_id)}
        })
        if existing_crop:
            return jsonify({'success': False, 'message': 'Another crop with this name already exists'}), 400
        
        # Prepare update data
        update_data = {
            'name': data['name'],
            'season': data['season'],
            'area': data.get('area', crop.get('area', '')),
            'image': image_url or data.get('image', crop.get('image', '')),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Update in MongoDB
        result = mongo.db.crops.update_one(
            {'_id': ObjectId(crop_id)},
            {'$set': update_data}
        )
        
        # Get the updated crop to return
        updated_crop = mongo.db.crops.find_one({'_id': ObjectId(crop_id)})
        updated_crop['_id'] = str(updated_crop['_id'])
        
        return jsonify({
            'success': True,
            'message': 'Crop updated successfully',
            'crop': updated_crop
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating crop: {str(e)}'
        }), 500

@app.route('/admin/crops/<crop_id>', methods=['DELETE'])
@login_required
def delete_crop(crop_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Check if crop exists
        crop = mongo.db.crops.find_one({'_id': ObjectId(crop_id)})
        if not crop:
            return jsonify({'success': False, 'message': 'Crop not found'}), 404
        
        # Delete associated image file if it exists and is in our upload folder
        if crop.get('image'):
            try:
                image_path = crop['image'].split('/static/uploads/')[-1]
                if image_path:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            except Exception as e:
                print(f"Error deleting image file: {e}")
        
        # Delete from MongoDB
        result = mongo.db.crops.delete_one({'_id': ObjectId(crop_id)})
        
        if result.deleted_count == 1:
            return jsonify({
                'success': True,
                'message': 'Crop deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to delete crop'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting crop: {str(e)}'
        }), 500


@app.route('/api/rainfall-data', methods=['GET', 'POST'])
@login_required
def handle_rainfall_data():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        if request.method == 'GET':
            # Handle GET request (data retrieval for specific crop/year)
            crop_id = request.args.get('crop_id')
            year = request.args.get('year')
            
            if not crop_id or not year:
                return jsonify({'success': False, 'message': 'Crop ID and Year are required'}), 400
            
            data = mongo.db.rainfall_data.find_one({
                'crop_id': ObjectId(crop_id),
                'year': int(year)
            })
            
            if data:
                data['_id'] = str(data['_id'])
                return jsonify({'success': True, 'data': data})
            else:
                return jsonify({'success': True, 'data': None})
                
        elif request.method == 'POST':
            # Handle POST request (data creation)
            data = request.get_json()
            
            # Validate required fields
            if not data.get('crop_id') or not data.get('year') or data.get('base_value') is None:
                return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
            # Check if data already exists
            existing = mongo.db.rainfall_data.find_one({
                'crop_id': ObjectId(data['crop_id']),
                'year': int(data['year'])
            })
            
            if existing:
                return jsonify({
                    'success': False,
                    'message': 'Data for this crop and year already exists'
                }), 400
            
            # Create new document
            rainfall_doc = {
                'crop_id': ObjectId(data['crop_id']),
                'year': int(data['year']),
                'base_value': float(data['base_value']),
                'rainfall': data.get('rainfall', {}),
                'wpi': data.get('wpi', {}),
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            # Insert into MongoDB
            result = mongo.db.rainfall_data.insert_one(rainfall_doc)
            
            return jsonify({
                'success': True,
                'message': 'Rainfall data created successfully',
                'data_id': str(result.inserted_id)
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error processing request: {str(e)}'
        }), 500
@app.route('/api/rainfall-data/all', methods=['GET'])
@login_required
def get_all_rainfall_data():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        # Get all rainfall data sorted by year descending, crop_id ascending
        rainfall_data = list(mongo.db.rainfall_data.find().sort([('year', -1), ('crop_id', 1)]))
        
        for item in rainfall_data:
            # Convert _id and crop_id to strings
            item['_id'] = str(item['_id'])
            crop_id = item.get('crop_id')

            if isinstance(crop_id, str):  # Convert only if needed
                crop_id = ObjectId(crop_id)

            crop = mongo.db.crops.find_one({'_id': crop_id})

            # Add crop name to item
            item['crop_name'] = crop['name'] if crop else 'Unknown Crop'

            # Optional: Convert crop_id to string for frontend if needed
            item['crop_id'] = str(crop_id)

        return jsonify({
            'success': True,
            'data': rainfall_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching rainfall data: {str(e)}'
        }), 500

@app.route('/api/rainfall-data/<data_id>', methods=['GET'])
@login_required
def get_single_rainfall_data(data_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = mongo.db.rainfall_data.find_one({'_id': ObjectId(data_id)})
        if not data:
            return jsonify({'success': False, 'message': 'Data not found'}), 404
        
        data['_id'] = str(data['_id'])
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching rainfall data: {str(e)}'
        }), 500

@app.route('/api/rainfall-data/<data_id>', methods=['PUT'])
@login_required
def update_rainfall_data(data_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # Validate required fields
        if not data.get('crop_id') or not data.get('year') or data.get('base_value') is None:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Prepare update data
        update_data = {
            'crop_id': ObjectId(data['crop_id']),
            'year': int(data['year']),
            'base_value': float(data['base_value']),
            'rainfall': data.get('rainfall', {}),
            'wpi': data.get('wpi', {}),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Update in MongoDB
        result = mongo.db.rainfall_data.update_one(
            {'_id': ObjectId(data_id)},
            {'$set': update_data}
        )
        
        if result.modified_count == 1:
            return jsonify({
                'success': True,
                'message': 'Rainfall data updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No changes made or data not found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating rainfall data: {str(e)}'
        }), 500

@app.route('/api/rainfall-data/<data_id>', methods=['DELETE'])
@login_required
def delete_rainfall_data(data_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        result = mongo.db.rainfall_data.delete_one({'_id': ObjectId(data_id)})
        
        if result.deleted_count == 1:
            return jsonify({
                'success': True,
                'message': 'Rainfall data deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Data not found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting rainfall data: {str(e)}'
        }), 500

# Add this route to serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)




if __name__ == '__main__':
    socketio.run(app, debug=True)