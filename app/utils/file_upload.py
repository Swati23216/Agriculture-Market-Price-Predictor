import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def handle_upload(file):
    if file.filename == '':
        return {'error': 'No selected file'}
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join('app/static/uploads', filename))
        return {'filename': filename}
    return {'error': 'Invalid file type'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS