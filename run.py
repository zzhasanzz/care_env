import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from flask import Flask, render_template, request, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from functools import wraps
from dotenv import load_dotenv
from iot_simulation.electricity import simulate_daily_consumption, fetch_user_data, calculate_bill, get_db_connection, calculate_and_log_consumption
from iot_simulation.admin_model import get_admin_by_email
import MySQLdb
import requests
import io
import base64
import flash



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
    
     # First check if the email belongs to an Admin
    admin = get_admin_by_email(email)
    if admin:
        session['admin_id'] = admin['id']
        session['user_type'] = 'admin'
        session['display_name'] = admin['display_name']
        return redirect(url_for('admin_dashboard')) 

    # Insert or update user in the database
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM user WHERE google_id = %s", (google_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        session['user_type'] = 'user'
        session['user_id'] = existing_user['id']
        session['display_name'] = display_name
        return redirect(url_for('dashboard'))
  
    else:
        cursor.execute("""
            INSERT INTO user (google_id, display_name, email)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE display_name = VALUES(display_name)
        """, (google_id, display_name, email))
        db.commit()
        return redirect(url_for('update_user'))

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


# @app.route('/update')  # Route for updating user information
# @login_required
# def update():
#     user = session['profile']
#     return render_template('update.html', user=user)

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('user_type') != 'admin':
        return "Access Denied", 403

    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # Fetch top 5 utility providers
    cursor.execute("""
        SELECT 
            up.provider_name,
            COUNT(u.id) AS num_users
        FROM utility_providers up
        LEFT JOIN user u 
        ON (u.electricity_provider = up.id OR u.water_provider = up.id OR u.gas_provider = up.id)
        GROUP BY up.id
        ORDER BY num_users DESC
        LIMIT 5
    """)
    top_providers = cursor.fetchall()

    #  Fetch top 5 users with highest total carbon emissions
    cursor.execute("""
        SELECT 
            u.display_name,
            IFNULL(SUM(dc.total_emission_kg), 0) AS total_emission
        FROM user u
        LEFT JOIN daily_carbon_footprint dc ON u.id = dc.user_id
        GROUP BY u.id
        ORDER BY total_emission DESC
        LIMIT 5
    """)
    top_users = cursor.fetchall()

    cursor.close()

    return render_template('admin_dashboard.html', 
                            admin_name=session.get('display_name'), 
                            top_providers=top_providers,
                            top_users=top_users)  # ✅ Pass it to template!


@app.route('/admin_profile')
def admin_profile():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login'))

    admin_id = session.get('admin_id')
    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, display_name, email FROM admin WHERE id = %s", (admin_id,))
    admin = cursor.fetchone()

    if not admin:
        return redirect(url_for('logout'))

    return render_template('admin_profile.html', admin=admin)

@app.route('/admin/user_details')
def user_details():
    if session.get('user_type') != 'admin':
        return "Access Denied", 403

    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # Fetch user list with service providers and RANK() based on total emissions
    cursor.execute("""
        SELECT 
            u.id,
            u.display_name,
            u.email,
            u.phone,
            u.division,
            up.provider_name AS electricity_provider,
            uw.provider_name AS water_provider,
            ug.provider_name AS gas_provider,
            IFNULL(SUM(dc.total_emission_kg), 0) AS total_emission,
            RANK() OVER (ORDER BY IFNULL(SUM(dc.total_emission_kg), 0) DESC) AS emission_rank
        FROM user u
        LEFT JOIN utility_providers up ON u.electricity_provider = up.id
        LEFT JOIN utility_providers uw ON u.water_provider = uw.id
        LEFT JOIN utility_providers ug ON u.gas_provider = ug.id
        LEFT JOIN daily_carbon_footprint dc ON u.id = dc.user_id
        GROUP BY u.id
        ORDER BY total_emission DESC
    """)
    users = cursor.fetchall()
    cursor.close()

    return render_template('user_details.html', users=users)


@app.route('/admin/add_utility_provider', methods=['GET', 'POST'])
def add_utility_provider():
    if session.get('user_type') != 'admin':
        return "Access Denied", 403

    if request.method == 'POST':
        provider_name = request.form['provider_name']
        energy_type = request.form['energy_type']
        transaction_phone = request.form.get('transaction_phone')
        unit_price = request.form['unit_price']
        emission_factor = request.form.get('emission_factor') or None
        billing_frequency = request.form['billing_frequency']
        website = request.form.get('website')
        region = request.form['region']
        description = request.form.get('description')

        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            INSERT INTO utility_providers 
            (provider_name, energy_type, transaction_phone, unit_price, emission_factor, billing_frequency, website, region, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (provider_name, energy_type, transaction_phone, unit_price, emission_factor, billing_frequency, website, region, description))
        db.commit()
        cursor.close()

        return redirect(url_for('view_providers'))  # after adding, redirect back to dashboard

    return render_template('add_utility_provider.html')

@app.route('/admin/view_providers')
def view_providers():
    if session.get('user_type') != 'admin':
        return "Access Denied", 403

    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            up.id,
            up.provider_name,
            up.region,
            up.energy_type,
            up.transaction_phone,
            up.unit_price,
            up.emission_factor,
            up.billing_frequency,
            up.website,
            COUNT(u.id) AS num_users,
            RANK() OVER (ORDER BY COUNT(u.id) DESC) AS rank_position
        FROM utility_providers up
        LEFT JOIN user u 
            ON (u.electricity_provider = up.id 
                OR u.water_provider = up.id 
                OR u.gas_provider = up.id)
        GROUP BY up.id
        ORDER BY up.energy_type, num_users DESC
    """)
    providers = cursor.fetchall()
    cursor.close()

    return render_template('view_providers.html', providers=providers)

@app.route('/admin/view_vehicles')
def view_vehicles():
    if session.get('user_type') != 'admin':
        return "Access Denied", 403

    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # Fetch all vehicles
    cursor.execute("""
        SELECT 
        v.id,
        v.model_name,
        v.vehicle_type,
        v.fuel_type,
        v.urban_efficiency,
        v.highway_efficiency,
        v.daily_average_km,
        v.description,
        COUNT(uv.id) AS num_users
    FROM vehicles v
    LEFT JOIN user_vehicles uv ON v.id = uv.vehicle_id
    GROUP BY v.id
    ORDER BY num_users DESC, v.model_name ASC;

    """)
    vehicles = cursor.fetchall()
    cursor.close()

    return render_template('view_vehicles.html', vehicles=vehicles)

@app.route('/admin/add_vehicle', methods=['GET', 'POST'])
def add_vehicle():
    if session.get('user_type') != 'admin':
        return "Access Denied", 403

    if request.method == 'POST':
        model_name = request.form['model_name']
        vehicle_type = request.form['vehicle_type']
        fuel_type = request.form['fuel_type']
        urban_efficiency = request.form['urban_efficiency']
        highway_efficiency = request.form['highway_efficiency']
        daily_average_km = request.form['daily_average_km']
        description = request.form.get('description')

        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            INSERT INTO vehicles 
            (model_name, vehicle_type, fuel_type, urban_efficiency, highway_efficiency, daily_average_km, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (model_name, vehicle_type, fuel_type, urban_efficiency, highway_efficiency, daily_average_km, description))
        db.commit()
        cursor.close()

        return redirect(url_for('view_vehicles', success='1'))
    return render_template('add_vehicle.html')


@app.route('/dashboard')
@login_required
def dashboard():
    user_profile = session['profile']
    google_id = user_profile['id']
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # Fetch user details
    cursor.execute("""
        SELECT u.display_name, u.email, u.phone, u.address, u.division,
               up.provider_name AS electricity_provider,
               uw.provider_name AS water_provider,
               ug.provider_name AS gas_provider, u.gas_type
        FROM user u
        LEFT JOIN utility_providers up ON u.electricity_provider = up.id
        LEFT JOIN utility_providers uw ON u.water_provider = uw.id
        LEFT JOIN utility_providers ug ON u.gas_provider = ug.id
        WHERE u.google_id = %s
    """, (google_id,))
    user_data = cursor.fetchone()

    if not user_data:
        return "User information not found.", 404

    # Fetch user_id
    cursor.execute("SELECT id FROM user WHERE google_id = %s", (google_id,))
    user_id_row = cursor.fetchone()
    if not user_id_row:
        return "User not found.", 404
    user_id = user_id_row['id']

    # Fetch housing details
    cursor.execute("""
        SELECT house_size_sqft, num_members, solar_panel_watt, wind_source_watt, other_renewable_source
        FROM user_housing
        WHERE user_id = %s
    """, (user_id,))
    housing_data = cursor.fetchone()

    # Fetch last 15 days' electricity consumption and daily bills
    cursor.execute("""
        SELECT consumption_date, units_consumed, daily_bill
        FROM daily_electricity_consumption
        WHERE user_id = %s
        ORDER BY consumption_date DESC
        LIMIT 15
    """, (user_id,))
    consumption_records = cursor.fetchall()

    # Fetch last 15 days' water consumption and daily bills
    cursor.execute("""
        SELECT consumption_date, liters_consumed, daily_bill
        FROM daily_water_consumption
        WHERE user_id = %s
        ORDER BY consumption_date DESC
        LIMIT 15
    """, (user_id,))
    water_consumption_records = cursor.fetchall()
    
    # Fetch last 15 days' gas consumption
    cursor.execute("""
        SELECT consumption_date, gas_used_cubic_meters, gas_cost
        FROM daily_gas_consumption
        WHERE user_id = %s
        ORDER BY consumption_date DESC
        LIMIT 15
    """, (user_id,))
    gas_consumption_records = cursor.fetchall()

    # Fetch last 15 days' fuel consumption
    cursor.execute("""
        SELECT consumption_date, fuel_used_liters, fuel_cost
        FROM daily_fuel_consumption
        WHERE user_id = %s
        ORDER BY consumption_date DESC
        LIMIT 15
    """, (user_id,))
    fuel_consumption_records = cursor.fetchall()


    # Fetch last 15 days' carbon footprint
    cursor.execute("""
        SELECT consumption_date, total_emission_kg, emission_tag, suggestions
        FROM daily_carbon_footprint
        WHERE user_id = %s
        ORDER BY consumption_date DESC
        LIMIT 15
    """, (user_id,))
    carbon_footprint_records = cursor.fetchall()




    # Fetch aggregated monthly electricity usage
    cursor.execute("""
        SELECT 
        MONTH(consumption_date) AS bill_month, 
        YEAR(consumption_date) AS bill_year, 
        SUM(units_consumed) AS total_units,
        SUM(daily_bill) AS total_bill
        FROM daily_electricity_consumption
        WHERE user_id = %s
        GROUP BY bill_year, bill_month
        ORDER BY bill_year DESC, bill_month DESC
    """, (user_id,))
    monthly_electricity_data = cursor.fetchall()
    
    # Fetch aggregated monthly water usage
    cursor.execute("""
        SELECT 
            MONTH(consumption_date) AS month, 
            YEAR(consumption_date) AS year, 
            SUM(liters_consumed) AS total_liters,
            SUM(daily_bill) AS total_bill
        FROM daily_water_consumption
        WHERE user_id = %s
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """, (user_id,))
    monthly_water_data = cursor.fetchall()
    
    # Fetch monthly gas usage
    cursor.execute("""
        SELECT 
            MONTH(consumption_date) AS month,
            YEAR(consumption_date) AS year,
            SUM(gas_used_cubic_meters) AS total_cubic_meters,
            SUM(gas_cost) AS total_bill
        FROM daily_gas_consumption
        WHERE user_id = %s
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """, (user_id,))
    monthly_gas_data = cursor.fetchall()

    # Fetch monthly fuel usage
    cursor.execute("""
        SELECT 
            MONTH(consumption_date) AS month,
            YEAR(consumption_date) AS year,
            SUM(fuel_used_liters) AS total_liters,
            SUM(fuel_cost) AS total_bill
        FROM daily_fuel_consumption
        WHERE user_id = %s
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """, (user_id,))
    monthly_fuel_data = cursor.fetchall()  

    # Fetch monthly carbon emissions
    cursor.execute("""
        SELECT 
            MONTH(consumption_date) AS month,
            YEAR(consumption_date) AS year,
            SUM(total_emission_kg) AS total_carbon_kg
        FROM daily_carbon_footprint
        WHERE user_id = %s
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """, (user_id,))
    monthly_carbon_data = cursor.fetchall()

    # 1. Fetch Monthly Carbon Footprint (electricity, fuel, gas, water individually)
    cursor.execute("""
        SELECT 
            MONTH(consumption_date) AS month,
            YEAR(consumption_date) AS year,
            SUM(electricity_emission_kg) AS total_electricity_kg,
            SUM(fuel_emission_kg) AS total_fuel_kg,
            SUM(gas_emission_kg) AS total_gas_kg,
            SUM(water_emission_kg) AS total_water_kg,
            SUM(total_emission_kg) AS total_carbon_kg
        FROM daily_carbon_footprint
        WHERE user_id = %s
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """, (user_id,))
    monthly_carbon_detailed_data = cursor.fetchall()


    # 2. Fetch the user's safe limits
    cursor.execute("""
        SELECT electricity_safe_limit, gas_safe_limit, fuel_safe_limit, water_safe_limit, total_safe_limit
        FROM safe_limits
        WHERE user_id = %s
    """, (user_id,))
    safe_limits_row = cursor.fetchone()

    if safe_limits_row:
        safe_limits = {
            'electricity': safe_limits_row['electricity_safe_limit'],
            'gas': safe_limits_row['gas_safe_limit'],
            'fuel': safe_limits_row['fuel_safe_limit'],
            'water': safe_limits_row['water_safe_limit'],
            'total': safe_limits_row['total_safe_limit'],
        }
    else:
        # fallback if not found
        safe_limits = {
            'electricity': 200,
            'gas': 200,
            'fuel': 200,
            'water': 50,
            'total': 500
        }


    # Determine average emission level
    emission_levels = [record['emission_tag'] for record in carbon_footprint_records]

    if emission_levels.count('high') > len(emission_levels) * 0.5:
        average_emission_level = "high"
    elif emission_levels.count('moderate') > len(emission_levels) * 0.5:
        average_emission_level = "moderate"
    else:
        average_emission_level = "low"

    reduction_suggestions = list(set(
        record['suggestions'] for record in carbon_footprint_records if record['suggestions']
    ))

    recent_carbon_footprint = [
        {
            "date": record["consumption_date"].strftime("%Y-%m-%d"),
            "carbon_kg": record["total_emission_kg"],
            "level": record["emission_tag"],
            "suggestion": record["suggestions"]
        }
        for record in carbon_footprint_records
    ]   

    # Fetch user's vehicles (NOW FROM user_vehicles)
    cursor.execute("""
        SELECT v.model_name 
        FROM user_vehicles uv
        JOIN vehicles v ON uv.vehicle_id = v.id
        WHERE uv.user_id = %s
    """, (user_id,))
    car_list = [car['model_name'] for car in cursor.fetchall()]

    cursor.close()

    # Combine all data
    user_info = {
        'profile': user_profile,
        'details': user_data,
        'housing': housing_data,
        'cars': car_list,
    }

    # Structure  electricity `recent_consumption`
    recent_consumption = [
        {"date": record["consumption_date"].strftime("%Y-%m-%d"), "units": record["units_consumed"], "bill": record["daily_bill"]}
        for record in consumption_records
    ]

    # Structure recent_water_consumption
    recent_water_consumption = [
        {
            "date": record["consumption_date"].strftime("%Y-%m-%d"),
            "liters": record["liters_consumed"],
            "bill": record["daily_bill"]
        }
        for record in water_consumption_records
    ]
    
    recent_gas_consumption=[
        {
            "date": record["consumption_date"].strftime("%Y-%m-%d"),
            "cubic_meters": record["gas_used_cubic_meters"],
            "bill": record["gas_cost"]
        }
        for record in gas_consumption_records
    ]
    recent_fuel_consumption=[
        {
            "date": record["consumption_date"].strftime("%Y-%m-%d"),
            "liters": record["fuel_used_liters"],
            "bill": record["fuel_cost"]
        }
        for record in fuel_consumption_records
    ]
    
    # Combine all user info
    user_info = {
        'profile': user_profile,
        'details': user_data,
        'housing': housing_data,
        'cars': car_list,
    }

    # Save into session ✅
    session['user_info'] = user_info

    return render_template(
        'dashboard.html',
        user_info=user_info,
        recent_consumption=recent_consumption,
        monthly_electricity_data=monthly_electricity_data,
        recent_water_consumption=recent_water_consumption,
        monthly_water_data=monthly_water_data,
        monthly_gas_data=monthly_gas_data,
        monthly_fuel_data=monthly_fuel_data,
        recent_gas_consumption=recent_gas_consumption,
        recent_fuel_consumption=recent_fuel_consumption,
        recent_carbon_footprint=recent_carbon_footprint,
        monthly_carbon_data=monthly_carbon_data,
        average_emission_level=average_emission_level,
        reduction_suggestions=reduction_suggestions,
        monthly_carbon_detailed_data=monthly_carbon_detailed_data,
        safe_limits=safe_limits,
    )


@app.route('/profile')
def profile():
    # Assuming you already have user_info session
    return render_template('profile.html', user_info=session['user_info'])


@app.route('/update_user', methods=['GET', 'POST'])
def update_user():
    if 'profile' not in session or 'id' not in session['profile']:
        return redirect(url_for('login'))

    google_id = session['profile']['id']
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # Get user info
    cursor.execute("SELECT * FROM user WHERE google_id = %s", (google_id,))
    user = cursor.fetchone()
    if not user:
        return redirect(url_for('logout'))

    # Get existing housing data if it exists
    cursor.execute("""
        SELECT id, house_size_sqft, num_members, 
               solar_panel_watt, wind_source_watt, other_renewable_source
        FROM user_housing 
        WHERE user_id = %s
    """, (user['id'],))
    housing = cursor.fetchone()

    if request.method == 'POST':
        try:
            # Update basic user details
            phone = request.form.get('phone', '')
            address = request.form.get('address', '')
            division = request.form.get('division', '')
            electricity_provider = request.form.get('electricity_provider') or None
            water_provider = request.form.get('water_provider') or None
            gas_provider = request.form.get('gas_provider') or None
            gas_type = request.form.get('gas_type') or None

            cursor.execute("""
                UPDATE user
                SET phone = %s, address = %s, division = %s,
                    electricity_provider = %s, water_provider = %s,
                    gas_provider = %s, gas_type = %s
                WHERE id = %s
            """, (phone, address, division, electricity_provider,
                 water_provider, gas_provider, gas_type, user['id']))

            # Handle deleted vehicles
            deleted_ids = request.form.get('deleted_vehicle_ids', '')
            if deleted_ids:
                deleted_ids_list = [vid for vid in deleted_ids.split(',') if vid]
                for vid in deleted_ids_list:
                    cursor.execute("DELETE FROM user_vehicles WHERE id = %s", (vid,))

            # Handle vehicles (existing and new)
            counter = 0
            while True:
                model_name = request.form.get(f'vehicle_model_name_{counter}')
                if not model_name:
                    break

                vehicle_id = request.form.get(f'vehicle_vehicle_id_{counter}')
                user_vehicle_id = request.form.get(f'vehicle_user_vehicle_id_{counter}')
                purchase_date = request.form.get(f'purchase_date_{counter}')
                custom_daily_km = request.form.get(f'custom_daily_km_{counter}') or None
                license_plate = request.form.get(f'license_plate_{counter}')

                if user_vehicle_id:  # Update existing
                    cursor.execute("""
                        UPDATE user_vehicles
                        SET purchase_date = %s, custom_daily_km = %s, license_plate = %s
                        WHERE id = %s
                    """, (purchase_date, custom_daily_km, license_plate, user_vehicle_id))
                else:  # Insert new
                    cursor.execute("""
                        INSERT INTO user_vehicles 
                        (user_id, vehicle_id, purchase_date, custom_daily_km, license_plate)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user['id'], vehicle_id, purchase_date, custom_daily_km, license_plate))

                counter += 1

            # Update housing details
            house_size_sqft = request.form.get('house_size_sqft', 0, type=int) or 0
            num_members = request.form.get('num_members', 0, type=int) or 0
            solar_panel_watt = request.form.get('solar_panel_watt', 0, type=int) or 0
            wind_source_watt = request.form.get('wind_source_watt', 0, type=int) or 0
            other_renewable_source = request.form.get('other_renewable_source', 0, type=int) or 0

            if housing:  # Update existing housing record
                cursor.execute("""
                    UPDATE user_housing
                    SET house_size_sqft = %s, num_members = %s,
                        solar_panel_watt = %s, wind_source_watt = %s,
                        other_renewable_source = %s
                    WHERE id = %s
                """, (house_size_sqft, num_members, solar_panel_watt,
                     wind_source_watt, other_renewable_source, housing['id']))
            else:  # Create new housing record
                cursor.execute("""
                    INSERT INTO user_housing 
                    (user_id, house_size_sqft, num_members,
                     solar_panel_watt, wind_source_watt,
                     other_renewable_source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user['id'], house_size_sqft, num_members,
                     solar_panel_watt, wind_source_watt, other_renewable_source))

            db.commit()
            #flash("Your profile has been updated successfully!", "success")
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.rollback()
            #flash(f"An error occurred: {str(e)}", "error")
            return redirect(url_for('dashboard'))

    # For GET requests, render the form with existing data
    # Get user vehicles for display
    cursor.execute("""
        SELECT uv.id as user_vehicle_id, uv.*, v.model_name 
        FROM user_vehicles uv
        JOIN vehicles v ON uv.vehicle_id = v.id
        WHERE uv.user_id = %s
    """, (user['id'],))
    user_vehicles = cursor.fetchall()

    

    housing_data = housing or {
        'house_size_sqft': 0,
        'num_members': 0,
        'solar_panel_watt': 0,
        'wind_source_watt': 0,
        'other_renewable_source': 0
    }


    return render_template('update.html',
                         user=user,
                         user_vehicles=user_vehicles,
                         housing=housing_data)




@app.route('/log_consumption', methods=['GET'])
def log_consumption():
    """
    Calculate and log daily consumption for all users for the last 30 days.
    """
    try:
        calculate_and_log_consumption()
        return "Daily consumption logged successfully for all users.", 200
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/bills')
@login_required
def view_electricity_bills():
    user_profile = session['profile']
    google_id = user_profile['id']

    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    # Fetch user ID
    cursor.execute("""
        SELECT u.id AS user_id
        FROM user u
        WHERE u.google_id = %s
    """, (google_id,))
    user = cursor.fetchone()

    if not user:
        return "User not found.", 404

    user_id = user['user_id']

    # aggregated monthly electricity consumption and bill
    cursor.execute("""
        SELECT 
            MONTH(consumption_date) AS bill_month, 
            YEAR(consumption_date) AS bill_year, 
            SUM(units_consumed) AS total_units, 
            SUM(daily_bill) AS total_bill,
            'due' AS payment_status -- For now, set all bills as 'due'
        FROM daily_electricity_consumption
        WHERE user_id = %s
        GROUP BY bill_year, bill_month
        ORDER BY bill_year DESC, bill_month DESC
    """, (user_id,))
    bills = cursor.fetchall()
    cursor.close()
    
    
    
    # Render the updated template
    return render_template('electricity_bills.html', bills=bills)

@app.route('/bills/<int:month>/<int:year>')
@login_required
def view_electricity_bill_detail(month, year):
    user_profile = session['profile']
    google_id = user_profile['id']

    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    # Fetch user ID
    cursor.execute("""
        SELECT u.id AS user_id
        FROM user u
        WHERE u.google_id = %s
    """, (google_id,))
    user = cursor.fetchone()

    if not user:
        return "User not found.", 404

    user_id = user['user_id']

    # Fetch detailed consumption for the given month and year
    cursor.execute("""
        SELECT consumption_date, units_consumed, daily_bill
        FROM daily_electricity_consumption
        WHERE user_id = %s AND MONTH(consumption_date) = %s AND YEAR(consumption_date) = %s
        ORDER BY consumption_date
    """, (user_id, month, year))
    bill_details = cursor.fetchall()
    cursor.close()

    # Render bill details
    return render_template('electricity_bill_detail.html', bill_details=bill_details, month=month, year=year)

@app.route('/water_bills')
@login_required
def view_water_bills():
    user_profile = session['profile']
    google_id = user_profile['id']

    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM user WHERE google_id = %s", (google_id,))
    user = cursor.fetchone()
    if not user:
        return "User not found.", 404

    user_id = user['id']

    cursor.execute("""
        SELECT 
            MONTH(consumption_date) AS month,
            YEAR(consumption_date) AS year,
            SUM(liters_consumed) AS total_liters,
            SUM(daily_bill) AS total_bill
        FROM daily_water_consumption
        WHERE user_id = %s
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """, (user_id,))
    bills = cursor.fetchall()
    cursor.close()

    return render_template('water_bills.html', bills=bills)


@app.route('/water_bills/<int:month>/<int:year>')
@login_required
def view_water_bill_detail(month, year):
    user_profile = session['profile']
    google_id = user_profile['id']

    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM user WHERE google_id = %s", (google_id,))
    user = cursor.fetchone()
    if not user:
        return "User not found.", 404

    user_id = user['id']

    cursor.execute("""
        SELECT consumption_date, liters_consumed, daily_bill
        FROM daily_water_consumption
        WHERE user_id = %s AND MONTH(consumption_date) = %s AND YEAR(consumption_date) = %s
        ORDER BY consumption_date
    """, (user_id, month, year))
    bill_details = cursor.fetchall()
    cursor.close()

    return render_template('water_bill_detail.html', bill_details=bill_details, month=month, year=year)

# Fuel Bills page
@app.route('/fuel_bills')
@login_required
def view_fuel_bills():
    user_profile = session['profile']
    google_id = user_profile['id']

    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM user WHERE google_id = %s", (google_id,))
    user = cursor.fetchone()
    if not user:
        return "User not found.", 404

    user_id = user['id']

    cursor.execute("""
        SELECT MONTH(consumption_date) AS month, YEAR(consumption_date) AS year,
               SUM(fuel_used_liters) AS total_liters, SUM(fuel_cost) AS total_bill
        FROM daily_fuel_consumption
        WHERE user_id = %s
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """, (user_id,))
    fuel_bills = cursor.fetchall()

    return render_template('fuel_bills.html', fuel_bills=fuel_bills)

# Fuel Bill Detail page
@app.route('/fuel_bills/<int:month>/<int:year>')
@login_required
def view_fuel_bill_detail(month, year):
    user_profile = session['profile']
    google_id = user_profile['id']

    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM user WHERE google_id = %s", (google_id,))
    user = cursor.fetchone()
    if not user:
        return "User not found.", 404

    user_id = user['id']

    cursor.execute("""
        SELECT consumption_date, fuel_used_liters, fuel_cost
        FROM daily_fuel_consumption
        WHERE user_id = %s AND MONTH(consumption_date) = %s AND YEAR(consumption_date) = %s
        ORDER BY consumption_date
    """, (user_id, month, year))
    fuel_bill_details = cursor.fetchall()

    return render_template('fuel_bill_detail.html', fuel_bill_details=fuel_bill_details, month=month, year=year)


# Gas Bills page
@app.route('/gas_bills')
@login_required
def view_gas_bills():
    user_profile = session['profile']
    google_id = user_profile['id']

    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM user WHERE google_id = %s", (google_id,))
    user = cursor.fetchone()
    if not user:
        return "User not found.", 404

    user_id = user['id']

    cursor.execute("""
        SELECT MONTH(consumption_date) AS month, YEAR(consumption_date) AS year,
               SUM(gas_used_cubic_meters) AS total_cubic_meters, SUM(gas_cost) AS total_bill
        FROM daily_gas_consumption
        WHERE user_id = %s
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """, (user_id,))
    gas_bills = cursor.fetchall()

    return render_template('gas_bills.html', gas_bills=gas_bills)

# Gas Bill Detail page
@app.route('/gas_bills/<int:month>/<int:year>')
@login_required
def view_gas_bill_detail(month, year):
    user_profile = session['profile']
    google_id = user_profile['id']

    cursor = db.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM user WHERE google_id = %s", (google_id,))
    user = cursor.fetchone()
    if not user:
        return "User not found.", 404

    user_id = user['id']

    cursor.execute("""
        SELECT consumption_date, gas_used_cubic_meters, gas_cost
        FROM daily_gas_consumption
        WHERE user_id = %s AND MONTH(consumption_date) = %s AND YEAR(consumption_date) = %s
        ORDER BY consumption_date
    """, (user_id, month, year))
    gas_bill_details = cursor.fetchall()

    return render_template('gas_bill_detail.html', gas_bill_details=gas_bill_details, month=month, year=year)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
