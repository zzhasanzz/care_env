import MySQLdb
import numpy as np
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

# Appliance definitions
appliances = {
    "fan": {
        "power": 0.07,
        "summer_hours": lambda: max(0, np.random.normal(14, 2)),
        "winter_hours": lambda: max(0, np.random.normal(2, 1))
    },
    "light": {
        "power": 0.01,
        "daily_hours": lambda: max(0, np.random.normal(5, 1.5))
    },
    "ac": {
        "power": 1.0,
        "summer_hours": lambda: max(0, np.random.normal(6, 2)),
        "winter_hours": lambda: max(0, np.random.uniform(0, 0.5))
    },
    "fridge": {
        "power": 0.15,
        "daily_hours": lambda: max(0, np.random.normal(24, 0.1))
    },
    "tv": {
        "power": 0.08,
        "daily_hours": lambda: max(0, np.random.normal(4, 1.5))
    },
    "washing_machine": {
        "power": 0.5,
        "daily_hours": lambda: max(0, np.random.exponential(0.5))
    },
    "computer": {
        "power": 0.15,
        "daily_hours": lambda: max(0, np.random.normal(6, 2))
    },
    "microwave": {
        "power": 1.0,
        "daily_hours": lambda: max(0, np.random.exponential(0.3))
    },
    "router": {
        "power": 0.01,
        "daily_hours": lambda: 24
    },
    "water_heater": {
        "power": 1.0,
        "winter_hours": lambda: max(0, np.random.normal(1, 0.5)),
        "summer_hours": lambda: max(0, np.random.normal(0.5, 0.2))
    }
}

# DB settings
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = "care_env"

def get_db_connection():
    try:
        conn = MySQLdb.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            passwd=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        return conn
    except MySQLdb.Error as err:
        print(f"Database Connection Error: {err}")
        raise

def fetch_user_data(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT uh.house_size_sqft, uh.num_members, uh.solar_panel_watt,
               uh.wind_source_watt, u.electricity_provider
        FROM user_housing uh
        JOIN user u ON uh.user_id = u.id
        WHERE u.id = %s
    """, (user_id,))
    housing_data = cursor.fetchone()
    if not housing_data:
        raise ValueError(f"No housing data found for user {user_id}")
    
    cursor.execute("""
        SELECT unit_price FROM utility_providers
        WHERE id = %s
    """, (housing_data['electricity_provider'],))
    provider_data = cursor.fetchone()
    if not provider_data:
        raise ValueError("No utility provider found for user")
    
    housing_data['base_rate'] = provider_data['unit_price']
    cursor.close()
    conn.close()
    return housing_data

def get_house_size_category(square_footage):
    if square_footage <= 1000:
        return "small"
    elif 1001 <= square_footage <= 1600:
        return "medium"
    else:
        return "large"

def scale_appliances(house_size, num_members):
    size_multiplier = {
        "small": 1.0,
        "medium": 1.3,
        "large": 1.6
    }
    member_factor = min(4, num_members) / 3
    
    scaled = {}
    for appliance, details in appliances.items():
        summer_func = (lambda base=details.get('summer_hours'): (lambda: max(0, base() * member_factor)))() if 'summer_hours' in details else None
        winter_func = (lambda base=details.get('winter_hours'): (lambda: max(0, base() * member_factor)))() if 'winter_hours' in details else None
        daily_func = (lambda base=details.get('daily_hours'): (lambda: max(0, base() * member_factor)))() if 'daily_hours' in details else None
        
        scaled[appliance] = {
            "power": details["power"],
            "summer_hours": summer_func,
            "winter_hours": winter_func,
            "daily_hours": daily_func
        }

    final_appliances = {}
    multiplier = int(size_multiplier[get_house_size_category(house_size)])
    
    for appliance in ["fan", "light", "tv", "computer"]:
        for i in range(multiplier):
            final_appliances[f"{appliance}_{i}"] = scaled[appliance]
    
    for appliance in ["ac", "fridge", "washing_machine", "microwave", "router", "water_heater"]:
        final_appliances[appliance] = scaled[appliance]
    
    return final_appliances

def get_season(date_obj):
    month = date_obj.month
    if 4 <= month <= 9:
        return "summer"
    elif month in [3, 10, 11]:
        return "transition"
    else:
        return "winter"

def get_simulation_date_ranges():
    """
    Generate date ranges for the last 6 full months + current month till today.
    """
    today = datetime.date.today()
    current_month_start = today.replace(day=1)

    date_ranges = []

    # Add last 6 full months
    for i in range(6, 0, -1):
        month_start = (current_month_start - datetime.timedelta(days=1)).replace(day=1)
        month_end = current_month_start - datetime.timedelta(days=1)
        date_ranges.append((f"{month_start.strftime('%B_%Y')}", month_start, month_end))
        current_month_start = month_start  # Move one month back

    # Now add current month up to today
    current_month_real_start = today.replace(day=1)
    date_ranges.append(("current_month", current_month_real_start, today))

    return date_ranges

def simulate_renewable_generation(solar_capacity, wind_capacity, season="summer"):
    solar_factors = {"summer": np.random.normal(5, 1), "transition": np.random.normal(4, 1), "winter": np.random.normal(3, 1)}
    wind_factors = {"summer": np.random.normal(3, 1), "transition": np.random.normal(5, 1.5), "winter": np.random.normal(4, 1)}
    solar_output = solar_capacity * 0.2 * solar_factors[season]
    wind_output = wind_capacity * 0.3 * wind_factors[season]
    return max(0, solar_output + wind_output)

def simulate_daily_consumption(square_footage, num_members, date_obj, solar_capacity=0, wind_capacity=0):
    season = get_season(date_obj)
    appliance_set = scale_appliances(square_footage, num_members)
    
    total_consumption = 0
    for appliance, details in appliance_set.items():
        try:
            if season == "summer" and details["summer_hours"]:
                hours = details["summer_hours"]()
            elif season == "winter" and details["winter_hours"]:
                hours = details["winter_hours"]()
            elif details["daily_hours"]:
                hours = details["daily_hours"]()
            else:
                hours = 0

            if season == "transition":
                if appliance.startswith(("fan", "ac")):
                    hours *= 0.7
                elif appliance == "water_heater":
                    hours *= 1.2

            total_consumption += details["power"] * hours
        except Exception as e:
            print(f"Error with {appliance}: {str(e)}")
            continue

    renewable_generation = simulate_renewable_generation(solar_capacity, wind_capacity, season)
    renewable_factor = 1.2 if season == "summer" else (0.8 if season == "winter" else 1.0)
    renewable_generation *= renewable_factor
    
    net_consumption = max(5, total_consumption - renewable_generation)
    return round(net_consumption, 2)

def fetch_all_users():
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT u.id AS user_id, u.electricity_provider AS utility_provider_id,
               uh.house_size_sqft, uh.num_members, uh.solar_panel_watt, uh.wind_source_watt
        FROM user u
        LEFT JOIN user_housing uh ON u.id = uh.user_id
    """)
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users

def log_daily_consumption(user_id, utility_provider_id, date, units_consumed, base_rate, multipliers, tiers):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM daily_electricity_consumption
        WHERE user_id = %s AND consumption_date = %s
    """, (user_id, date))
    
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return

    daily_bill = calculate_bill(units_consumed, base_rate, multipliers, tiers)
    
    cursor.execute("""
        INSERT INTO daily_electricity_consumption
        (user_id, utility_provider_id, consumption_date, units_consumed, daily_bill)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, utility_provider_id, date, units_consumed, daily_bill))
    conn.commit()
    cursor.close()
    conn.close()

def calculate_bill(total_units, base_rate, multipliers, tiers, service_charge=10, demand_charge=30, meter_rent=10, vat_rate=0.05):
    rates = [base_rate * m for m in multipliers]
    total = 0
    remaining = total_units
    
    for limit, rate in zip(tiers, rates):
        if remaining <= 0:
            break
        in_this_tier = min(remaining, limit)
        total += in_this_tier * rate
        remaining -= in_this_tier
    
    if remaining > 0:
        total += remaining * rates[-1]
    
    subtotal = total + service_charge + demand_charge + meter_rent
    vat = subtotal * vat_rate
    return subtotal + vat

def calculate_and_log_consumption():
    all_users = fetch_all_users()
    date_ranges = get_simulation_date_ranges()
    multipliers = [1.00, 1.35, 1.41, 1.48, 2.63]
    tiers = [75, 125, 100, 200, float('inf')]

    for user in all_users:
        user_id = user['user_id']
        utility_provider_id = user['utility_provider_id']
        house_size = user['house_size_sqft']
        num_members = user['num_members'] or 4
        solar_capacity = user['solar_panel_watt'] or 0
        wind_capacity = user['wind_source_watt'] or 0
        base_rate = fetch_user_data(user_id)['base_rate']

        for period_name, start_date, end_date in date_ranges:
            print(f"Processing {user_id} for {period_name} ({start_date} to {end_date})")
            current_date = start_date
            while current_date <= end_date:
                units = simulate_daily_consumption(house_size, num_members, current_date, solar_capacity, wind_capacity)
                log_daily_consumption(user_id, utility_provider_id, current_date, units, base_rate, multipliers, tiers)
                current_date += datetime.timedelta(days=1)

def main(user_id):
    user = fetch_user_data(user_id)
    house_size = user['house_size_sqft']
    num_members = user['num_members'] or 4
    solar_capacity = user['solar_panel_watt'] or 0
    wind_capacity = user['wind_source_watt'] or 0
    base_rate = user['base_rate']
    
    today = datetime.date.today()
    total_units = sum(simulate_daily_consumption(house_size, num_members, today - datetime.timedelta(days=i), solar_capacity, wind_capacity) for i in range(31))
    multipliers = [1.00, 1.35, 1.41, 1.48, 2.63]
    tiers = [75, 125, 100, 200, float('inf')]
    total_bill = calculate_bill(total_units, base_rate, multipliers, tiers)
    
    print(f"Total Monthly Consumption: {total_units:.2f} kWh")
    print(f"Total Electricity Bill: Tk {total_bill:.2f}")

if __name__ == "__main__":
    calculate_and_log_consumption()


# https://bdepoint.com/electric-bill-calculation-bangladesh/
