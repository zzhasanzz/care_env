from flask import Flask, render_template, request, redirect, url_for, session


from authlib.integrations.flask_client import OAuth
from functools import wraps
from dotenv import load_dotenv
import MySQLdb
import os
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# MySQL connection
db = MySQLdb.connect(
    host="localhost",
    user="root",
    passwd="1234",
    database="care_env"
)

# Initialize the database table
def init_user_table():
    """Create the user table if it doesn't exist."""
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INT AUTO_INCREMENT PRIMARY KEY,
            google_id VARCHAR(255) NOT NULL UNIQUE,
            display_name VARCHAR(255),
            email VARCHAR(255) NOT NULL UNIQUE,
            phone VARCHAR(15),
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

# Call the table initialization function
init_user_table()

# OAuth setup
oauth = OAuth(app)
google = oauth.register(
     name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

# Utility functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'profile' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login')
def login():
    redirect_uri = os.getenv('REDIRECT_URI', url_for('authorize', _external=True))
    return google.authorize_redirect(redirect_uri)


@app.route('/authorize')
def authorize():
    """Handle the callback from Google and retrieve user info."""
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    session['profile'] = user_info  # Store user info in session

    # Extract user details
    google_id = user_info['id']
    display_name = user_info.get('name', '')
    email = user_info.get('email', '')

    # Insert or update user in the database
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO user (google_id, display_name, email)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE display_name = VALUES(display_name)
    """, (google_id, display_name, email))
    db.commit()

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = session['profile']
    return render_template('dashboard.html', user=user)

@app.route('/update_user', methods=['POST'])
def update_user():
    """Update additional user information."""
    if 'profile' not in session:
        return redirect(url_for('login'))

    google_id = session['profile']['id']
    phone = request.form.get('phone', '')
    address = request.form.get('address', '')

    # Update the user's additional information
    cursor = db.cursor()
    cursor.execute("""
        UPDATE user
        SET phone = %s, address = %s
        WHERE google_id = %s
    """, (phone, address, google_id))
    db.commit()

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
