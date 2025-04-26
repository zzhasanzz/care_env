import MySQLdb
import os
import datetime
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

load_dotenv()

# Database connection
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'care_env')

def get_db_connection():
    return MySQLdb.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        passwd=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

# Emission Factors
EMISSION_FACTORS = {
    "electricity": 0.62,  # kg CO2 per kWh
    "fuel": {             # kg CO2 per liter
        "petrol": 2.31,
        "diesel": 2.68,
        "cng": 2.14,
        "octane": 2.33
    },
    "gas": 1.8,           # kg CO2 per cubic meter
    "water": 0.00025       # kg CO2 per liter
}

# Classify emissions
def classify_emission(total_emission_kg):
    if total_emission_kg <= 10:
        return "Good", "Excellent! Your carbon footprint is low. Keep it up!"
    elif total_emission_kg <= 25:
        return "Moderate", "Moderate footprint. Try reducing fuel or electricity usage."
    else:
        return "High", "High footprint! Consider using public transport, saving water, and switching to renewable energy."

# Fetch all daily consumption for a specific date
def fetch_daily_consumption(date_obj):
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    users = {}

    # Electricity
    cursor.execute("""
        SELECT user_id, units_consumed 
        FROM daily_electricity_consumption 
        WHERE consumption_date = %s
    """, (date_obj,))
    for row in cursor.fetchall():
        users.setdefault(row['user_id'], {})['electricity_units'] = row['units_consumed']

    # Fuel
    cursor.execute("""
        SELECT user_id, SUM(fuel_used_liters) as total_fuel 
        FROM daily_fuel_consumption 
        WHERE consumption_date = %s 
        GROUP BY user_id
    """, (date_obj,))
    for row in cursor.fetchall():
        users.setdefault(row['user_id'], {})['fuel_liters'] = row['total_fuel']

    # Gas
    cursor.execute("""
        SELECT user_id, gas_used_cubic_meters 
        FROM daily_gas_consumption 
        WHERE consumption_date = %s
    """, (date_obj,))
    for row in cursor.fetchall():
        users.setdefault(row['user_id'], {})['gas_cubic_meters'] = row['gas_used_cubic_meters']

    # Water
    cursor.execute("""
        SELECT user_id, liters_consumed 
        FROM daily_water_consumption 
        WHERE consumption_date = %s
    """, (date_obj,))
    for row in cursor.fetchall():
        users.setdefault(row['user_id'], {})['water_liters'] = row['liters_consumed']

    cursor.close()
    conn.close()
    return users

# Calculate emissions
def calculate_emissions(data):
    electricity_emission = data.get('electricity_units', 0) * EMISSION_FACTORS['electricity']
    fuel_emission = data.get('fuel_liters', 0) * 2.4  # Average across fuel types
    gas_emission = data.get('gas_cubic_meters', 0) * EMISSION_FACTORS['gas']
    water_emission = data.get('water_liters', 0) * EMISSION_FACTORS['water']

    total_emission = electricity_emission + fuel_emission + gas_emission + water_emission

    return {
        "electricity_kg": round(electricity_emission, 2),
        "fuel_kg": round(fuel_emission, 2),
        "gas_kg": round(gas_emission, 2),
        "water_kg": round(water_emission, 2),
        "total_kg": round(total_emission, 2)
    }

# Log daily carbon footprint
def log_carbon_footprint(user_id, date_obj, emissions, tag, suggestion):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if already logged
        cursor.execute("""
            SELECT 1 FROM daily_carbon_footprint 
            WHERE user_id = %s AND consumption_date = %s
        """, (user_id, date_obj))
        if cursor.fetchone():
            print(f"Already logged: User {user_id} on {date_obj}")
            return

        cursor.execute("""
            INSERT INTO daily_carbon_footprint
            (user_id, consumption_date, electricity_emission_kg, fuel_emission_kg, gas_emission_kg, water_emission_kg, total_emission_kg, emission_tag, suggestions)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, date_obj,
            emissions['electricity_kg'],
            emissions['fuel_kg'],
            emissions['gas_kg'],
            emissions['water_kg'],
            emissions['total_kg'],
            tag,
            suggestion
        ))

        conn.commit()
        print(f"Logged: User {user_id} on {date_obj}: {emissions['total_kg']} kg")
    except MySQLdb.Error as e:
        print(f"Error logging: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

# Main calculation over past 6 months
def calculate_and_log_for_past_six_months():
    today = datetime.date.today()
    six_months_ago = today.replace(day=1) - relativedelta(months=6)

    current_date = six_months_ago
    while current_date <= today:
        print(f"\nProcessing {current_date}...")
        all_data = fetch_daily_consumption(current_date)

        for user_id, consumptions in all_data.items():
            emissions = calculate_emissions(consumptions)
            tag, suggestion = classify_emission(emissions['total_kg'])
            log_carbon_footprint(user_id, current_date, emissions, tag, suggestion)

        current_date += datetime.timedelta(days=1)

if __name__ == "__main__":
    print("Starting full carbon footprint simulation...")
    calculate_and_log_for_past_six_months()
    print("\nCarbon footprint simulation completed ✅")
