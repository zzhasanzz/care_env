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

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

# MySQL connection
db = MySQLdb.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    passwd=MYSQL_PASSWORD,
    database=MYSQL_DATABASE
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
        division VARCHAR(50),
        electricity_provider INT,
        water_provider INT,
        gas_provider INT,
        gas_type ENUM('metered', 'non-metered'),
        car_ids TEXT, -- Comma-separated list of car IDs
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (electricity_provider) REFERENCES utility_providers(id),
        FOREIGN KEY (water_provider) REFERENCES utility_providers(id),
        FOREIGN KEY (gas_provider) REFERENCES utility_providers(id)
        );
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

@app.route('/get_providers/<division>')
def get_providers(division):
    """Fetch utility providers based on the user's division."""
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT id, provider_name, energy_type 
        FROM utility_providers 
        WHERE region = %s OR region = 'Nationwide'
    """, (division,))
    providers = cursor.fetchall()
    return {'providers': providers}

@app.route('/search_cars', methods=['GET'])
def search_cars():
    """Search for car models based on user input."""
    query = request.args.get('q', '')
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT id, model_name 
        FROM vehicles
        WHERE model_name LIKE %s
    """, (f"%{query}%",))
    cars = cursor.fetchall()
    return {'cars': cars}


@app.route('/update')  # Route for updating user information
@login_required
def update():
    user = session['profile']
    return render_template('update.html', user=user)

@app.route('/dashboard')  # Route for the main dashboard
@login_required
def dashboard():
    user = session['profile']
    return render_template('dashboard.html', user=user)

@app.route('/update_user', methods=['POST'])
def update_user():
    """Update user information and housing details."""
    if 'profile' not in session or 'id' not in session['profile']:
        return "User is not logged in", 401

    google_id = session['profile']['id']

    # Fetch user ID from `user` table
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM user WHERE google_id = %s", (google_id,))
    user = cursor.fetchone()

    if not user:
        print(f"No user found for google_id: {google_id}")
        return "User not found in the database. Please register first.", 404

    user_id = user['id']

    # Fetch user data from the form
    phone = request.form.get('phone', '')
    address = request.form.get('address', '')
    division = request.form.get('division', '')
    electricity_provider = request.form.get('electricity_provider', None)
    water_provider = request.form.get('water_provider', None)
    gas_provider = request.form.get('gas_provider', None)
    gas_type = request.form.get('gas_type', None)
    car_ids = request.form.getlist('car_ids')  # Multiple car IDs

    # Update user table
    cursor.execute("""
        UPDATE user
        SET phone = %s, address = %s, division = %s,
            electricity_provider = %s, water_provider = %s,
            gas_provider = %s, gas_type = %s, car_ids = %s
        WHERE id = %s
    """, (phone, address, division, electricity_provider, water_provider,
          gas_provider, gas_type, ','.join(car_ids), user_id))

    # Fetch housing data from the form
    house_size_sqft = request.form.get('house_size_sqft', 0, type=int)
    num_members = request.form.get('num_members', 0, type=int)
    solar_panel_watt = request.form.get('solar_panel_watt', 0, type=int)
    wind_source_watt = request.form.get('wind_source_watt', 0, type=int)
    other_renewable_source = request.form.get('other_renewable_source', 0, type=int)

    # Check if housing record exists for the user
    cursor.execute("SELECT id FROM user_housing WHERE user_id = %s", (user_id,))
    housing = cursor.fetchone()

    if housing:
        # Update existing housing record
        cursor.execute("""
            UPDATE user_housing
            SET house_size_sqft = %s, num_members = %s,
                solar_panel_watt = %s, wind_source_watt = %s,
                other_renewable_source = %s
            WHERE user_id = %s
        """, (house_size_sqft, num_members, solar_panel_watt, wind_source_watt,
              other_renewable_source, user_id))
    else:
        # Insert new housing record
        cursor.execute("""
            INSERT INTO user_housing (user_id, house_size_sqft, num_members,
                                       solar_panel_watt, wind_source_watt,
                                       other_renewable_source)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, house_size_sqft, num_members, solar_panel_watt, wind_source_watt,
              other_renewable_source))

    # Commit changes to the database
    db.commit()

    return redirect(url_for('update'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
