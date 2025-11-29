import os
import json
import uuid
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from agents.root_agent import RootAgent

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Create necessary directories
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
Path('reviews').mkdir(exist_ok=True)

# Initialize root agent
root_agent = RootAgent()

# In-memory storage for reviews (use database in production)
reviews_db = {}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_paper():
    """Handle paper upload and initiate review process"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Generate unique token
        review_token = str(uuid.uuid4())
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{review_token}_{filename}")
        file.save(file_path)
        
        # Initialize review entry
        reviews_db[review_token] = {
            'token': review_token,
            'original_filename': filename,
            'file_path': file_path,
            'status': 'processing',
            'uploaded_at': datetime.now().isoformat(),
            'progress': 'Uploaded successfully. Starting review process...'
        }
        
        # Start processing in background
        threading.Thread(target=process_review, args=(review_token, file_path), daemon=True).start()
        
        return jsonify({
            'success': True,
            'token': review_token,
            'message': 'Paper uploaded successfully. Processing started.'
        })
    
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


def process_review(review_token, file_path):
    """Process the paper review through the agent pipeline"""
    try:
        # Update status
        reviews_db[review_token]['progress'] = 'Parsing document...'
        
        # Run root agent
        result = root_agent.process_paper(file_path)
        
        if isinstance(result, dict) and result.get('error'):
            reviews_db[review_token].update({
                'status': 'failed',
                'progress': f"Error: {result['error']}",
                'completed_at': datetime.now().isoformat(),
                'result': result,
                'error': result.get('details', result['error'])
            })
            return
        
        # Update review entry for successful runs
        reviews_db[review_token].update({
            'status': 'completed',
            'progress': 'Review completed successfully!',
            'completed_at': datetime.now().isoformat(),
            'result': result
        })
        
        # Save review to file
        review_file = f"reviews/{review_token}.json"
        with open(review_file, 'w') as f:
            json.dump(result, f, indent=2)
    
    except Exception as e:
        app.logger.error(f"Processing error for {review_token}: {str(e)}")
        reviews_db[review_token].update({
            'status': 'failed',
            'progress': f'Error: {str(e)}',
            'error': str(e)
        })


@app.route('/api/status/<token>', methods=['GET'])
def check_status(token):
    """Check review status"""
    if token not in reviews_db:
        return jsonify({'error': 'Invalid review token'}), 404
    
    review = reviews_db[token]
    
    return jsonify({
        'token': token,
        'status': review['status'],
        'progress': review.get('progress', ''),
        'uploaded_at': review.get('uploaded_at'),
        'completed_at': review.get('completed_at')
    })


@app.route('/api/review/<token>', methods=['GET'])
def get_review(token):
    """Retrieve completed review"""
    if token not in reviews_db:
        return jsonify({'error': 'Invalid review token'}), 404
    
    review = reviews_db[token]
    
    if review['status'] != 'completed':
        return jsonify({
            'error': 'Review not yet completed',
            'status': review['status'],
            'progress': review.get('progress')
        }), 400
    
    return jsonify({
        'token': token,
        'status': review['status'],
        'result': review.get('result'),
        'original_filename': review.get('original_filename'),
        'completed_at': review.get('completed_at')
    })


@app.route('/api/reviews', methods=['GET'])
def list_reviews():
    """List all reviews"""
    reviews = []
    for token, review in reviews_db.items():
        reviews.append({
            'token': token,
            'status': review['status'],
            'original_filename': review.get('original_filename'),
            'uploaded_at': review.get('uploaded_at'),
            'completed_at': review.get('completed_at')
        })
    
    return jsonify({'reviews': reviews})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
