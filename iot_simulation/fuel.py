import MySQLdb
import numpy as np
from datetime import datetime, timedelta, date
import os
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

load_dotenv()

# Database configuration
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'care_env')

# Fuel prices
FUEL_PRICES = {
    "petrol": 121.0,
    "diesel": 105.0,
    "cng": 43.0,
    "octane": 125.0
}

# Driving condition probabilities
DRIVING_CONDITION_PROBS = {
    "summer": {"urban": 0.6, "highway": 0.4},
    "winter": {"urban": 0.7, "highway": 0.3}
}

# Weekend usage multipliers
WEEKEND_USAGE_MULTIPLIER = {
    "car": {"urban": 1.3, "highway": 1.8},
    "motorcycle": {"urban": 1.1, "highway": 1.4},
    "truck": {"urban": 1.0, "highway": 1.2},
    "bus": {"urban": 1.0, "highway": 1.0}
}

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
        print(f"Database connection error: {err}")
        raise

def get_season(date_obj):
    month = date_obj.month
    return "summer" if 4 <= month <= 9 else "winter"

def validate_vehicle_data(vehicle):
    vehicle['daily_km'] = vehicle.get('custom_daily_km') or vehicle.get('daily_average_km', 20)
    vehicle['daily_km'] = max(5, min(300, vehicle['daily_km']))
    vehicle['urban_efficiency'] = max(5, min(50, vehicle.get('urban_efficiency', 10)))
    vehicle['highway_efficiency'] = max(8, min(60, vehicle.get('highway_efficiency', 15)))
    return vehicle

def fetch_user_vehicles():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT uv.id as user_vehicle_id, uv.user_id, uv.vehicle_id,
                   uv.custom_daily_km, v.model_name, v.vehicle_type, v.fuel_type,
                   v.urban_efficiency, v.highway_efficiency, v.daily_average_km, v.description
            FROM user_vehicles uv
            JOIN vehicles v ON uv.vehicle_id = v.id
            WHERE v.fuel_type != 'electric'
            ORDER BY uv.user_id, v.vehicle_type DESC, v.daily_average_km DESC
        """)
        user_vehicles = {}
        for row in cursor.fetchall():
            user_id = row['user_id']
            if user_id not in user_vehicles:
                user_vehicles[user_id] = []
            user_vehicles[user_id].append(validate_vehicle_data(row))
        cursor.close()
        conn.close()
        return user_vehicles
    except MySQLdb.Error as err:
        print(f"Database error fetching vehicles: {err}")
        return {}

def calculate_vehicle_usage(user_vehicles, date_obj):
    if not user_vehicles:
        return []

    base_total_km = sum(v['daily_km'] for v in user_vehicles)
    total_km = base_total_km * 1.5 if date_obj.weekday() >= 5 else base_total_km

    if len(user_vehicles) == 1:
        return [(user_vehicles[0], total_km)]

    results = []
    remaining_km = total_km

    sorted_vehicles = sorted(user_vehicles, key=lambda x: x['vehicle_type'], reverse=True)

    for i, vehicle in enumerate(sorted_vehicles):
        if i == len(sorted_vehicles) - 1:
            distance = remaining_km
        else:
            if vehicle['vehicle_type'] == 'truck':
                portion = np.random.uniform(0.5, 0.8)
            elif vehicle['vehicle_type'] == 'bus':
                portion = np.random.uniform(0.7, 0.9)
            elif vehicle['vehicle_type'] == 'car':
                portion = np.random.uniform(0.3, 0.6)
            else:
                portion = np.random.uniform(0.1, 0.3)
            distance = remaining_km * portion
            remaining_km -= distance

        distance = max(1, min(500, distance))
        results.append((vehicle, round(distance, 2)))

    return results

def simulate_daily_fuel_usage(vehicle, date_obj, distance):
    try:
        if vehicle['fuel_type'] == 'electric':
            return 0, 0, 'none'

        season = get_season(date_obj)
        is_weekend = date_obj.weekday() >= 5
        driving_condition = np.random.choice(
            list(DRIVING_CONDITION_PROBS[season].keys()),
            p=list(DRIVING_CONDITION_PROBS[season].values())
        )
        efficiency = vehicle[f"{driving_condition}_efficiency"]
        base_fuel_used = distance / efficiency
        daily_variation = np.random.normal(1.0, 0.075)
        fuel_used = max(0.1, base_fuel_used * daily_variation)

        if is_weekend:
            multiplier = WEEKEND_USAGE_MULTIPLIER.get(vehicle['vehicle_type'], {}).get(driving_condition, 1.0)
            fuel_used *= multiplier

        return round(fuel_used, 2), driving_condition

    except Exception as e:
        print(f"Error simulating for vehicle {vehicle.get('model_name', 'unknown')}: {str(e)}")
        return 5.0, "urban"

def log_daily_consumption(user_id, vehicle_id, user_vehicle_id, date_obj, fuel_used, fuel_price, driving_condition):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.callproc('InsertFuelConsumption', (
            user_id, vehicle_id, user_vehicle_id, date_obj, fuel_used, fuel_price, driving_condition
        ))

        conn.commit()
        return True

    except MySQLdb.Error as err:
        print(f"Error inserting fuel record for user {user_id}, vehicle {vehicle_id} on {date_obj}: {err}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_simulation_date_ranges():
    today = date.today()
    current_month_start = today.replace(day=1)
    date_ranges = []

    for i in range(6, 0, -1):
        month_start = (current_month_start - relativedelta(months=1)).replace(day=1)
        month_end = current_month_start - timedelta(days=1)
        date_ranges.append((f"{month_start.strftime('%B_%Y')}", month_start, month_end))
        current_month_start = month_start

    date_ranges.append(("current_month", today.replace(day=1), today))
    return date_ranges

def calculate_and_log_fuel_consumption():
    user_vehicles = fetch_user_vehicles()
    if not user_vehicles:
        print("No fuel-powered user vehicles found")
        return False

    date_ranges = get_simulation_date_ranges()

    for period_name, start_date, end_date in date_ranges:
        print(f"\nProcessing {period_name.replace('_', ' ')} ({start_date} to {end_date})")

        for user_id, vehicles in user_vehicles.items():
            for single_date in (start_date + timedelta(n) for n in range((end_date - start_date).days + 1)):
                vehicle_distances = calculate_vehicle_usage(vehicles, single_date)

                for vehicle, distance in vehicle_distances:
                    if distance <= 0 or vehicle['fuel_type'] == 'electric':
                        continue

                    fuel_used, driving_condition = simulate_daily_fuel_usage(vehicle, single_date, distance)
                    fuel_price = FUEL_PRICES.get(vehicle['fuel_type'], 0)

                    log_daily_consumption(
                        user_id,
                        vehicle['vehicle_id'],
                        vehicle['user_vehicle_id'],
                        single_date,
                        fuel_used,
                        fuel_price,
                        driving_condition
                    )
    return True

def generate_fuel_report(user_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("""
            SELECT uv.id as user_vehicle_id, v.model_name, v.vehicle_type,
                   v.fuel_type, uv.license_plate
            FROM user_vehicles uv
            JOIN vehicles v ON uv.vehicle_id = v.id
            WHERE uv.user_id = %s AND v.fuel_type != 'electric'
        """, (user_id,))

        vehicles = cursor.fetchall()

        if not vehicles:
            print(f"No fuel-powered vehicles found for user {user_id}")
            return

        print(f"\nFuel Consumption Report for User {user_id}")
        print("="*60)

        date_ranges = get_simulation_date_ranges()

        for vehicle in vehicles:
            print(f"\nVehicle: {vehicle['model_name']} ({vehicle['vehicle_type']})")
            print(f"Fuel Type: {vehicle['fuel_type'].upper()}")
            print(f"License Plate: {vehicle['license_plate'] or 'Not specified'}")
            print("-"*50)

            total_liters = 0
            total_cost = 0
            total_days = 0

            for period_name, start_date, end_date in date_ranges:
                cursor.execute("""
                    SELECT SUM(fuel_used_liters) AS liters, SUM(fuel_cost) AS cost, COUNT(*) AS days
                    FROM daily_fuel_consumption
                    WHERE user_id = %s AND user_vehicle_id = %s
                    AND consumption_date BETWEEN %s AND %s
                """, (user_id, vehicle['user_vehicle_id'], start_date, end_date))

                period_data = cursor.fetchone()
                liters = period_data['liters'] or 0
                cost = period_data['cost'] or 0
                days = period_data['days'] or 0

                print(f"{period_name.replace('_', ' ').title()}:")
                print(f"  Days Driven: {days}")
                print(f"  Fuel Used: {liters:.2f} liters")
                print(f"  Total Cost: Tk {cost:.2f}")
                if days > 0:
                    print(f"  Avg Daily: {liters/days:.2f} liters, Tk {cost/days:.2f}")

                total_liters += liters
                total_cost += cost
                total_days += days

            print("\nTotals for all periods:")
            print(f"  Total Days Driven: {total_days}")
            print(f"  Total Fuel Used: {total_liters:.2f} liters")
            print(f"  Total Cost: Tk {total_cost:.2f}")
            if total_days > 0:
                print(f"  Average Daily: {total_liters/total_days:.2f} liters")
                print(f"  Average Cost per Day: Tk {total_cost/total_days:.2f}")
                print(f"  Average Cost per Liter: Tk {total_cost/total_liters:.2f}")

        print("\n" + "="*60)

    except MySQLdb.Error as err:
        print(f"Database error generating report: {err}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Starting fuel consumption simulation...")
    if calculate_and_log_fuel_consumption():
        print("\nSimulation completed successfully!")
        generate_fuel_report(1)
    else:
        print("\nSimulation encountered errors!")
