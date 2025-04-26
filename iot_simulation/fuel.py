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

# Fuel prices (excluding electric as it's not applicable)
FUEL_PRICES = {
    "petrol": 121.0,
    "diesel": 105.0,
    "cng": 43.0,
    "octane": 125.0
}

# Driving condition probabilities with seasonal variations
DRIVING_CONDITION_PROBS = {
    "summer": {
        "urban": 0.6,
        "highway": 0.4
    },
    "winter": {
        "urban": 0.7,
        "highway": 0.3
    }
}

# Weekend usage multipliers
WEEKEND_USAGE_MULTIPLIER = {
    "car": {
        "urban": 1.3,
        "highway": 1.8
    },
    "motorcycle": {
        "urban": 1.1,
        "highway": 1.4
    },
    "truck": {
        "urban": 1.0,  # Commercial trucks may not follow weekend patterns
        "highway": 1.2
    },
    "bus": {
        "urban": 1.0,  # Buses follow schedules
        "highway": 1.0
    }
}

def get_db_connection():
    """Create and return a new database connection"""
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
    """Determine season based on date"""
    month = date_obj.month
    return "summer" if 4 <= month <= 9 else "winter"

def validate_vehicle_data(vehicle):
    """Validate and sanitize vehicle data based on your schema"""
    # Set defaults for missing values
    vehicle['daily_km'] = vehicle.get('custom_daily_km') or vehicle.get('daily_average_km', 20)
    vehicle['daily_km'] = max(5, min(300, vehicle['daily_km']))  # Reasonable bounds
    
    # Efficiency validation
    vehicle['urban_efficiency'] = max(5, min(50, vehicle.get('urban_efficiency', 10)))
    vehicle['highway_efficiency'] = max(8, min(60, vehicle.get('highway_efficiency', 15)))
    
    return vehicle

def fetch_user_vehicles():
    """Fetch all user vehicles with combined data from both tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        query = """
        SELECT 
            uv.id as user_vehicle_id,
            uv.user_id,
            uv.vehicle_id,
            uv.custom_daily_km,
            uv.license_plate,
            v.model_name,
            v.vehicle_type,
            v.fuel_type,
            v.urban_efficiency,
            v.highway_efficiency,
            v.daily_average_km,
            v.description
        FROM user_vehicles uv
        JOIN vehicles v ON uv.vehicle_id = v.id
        WHERE v.fuel_type != 'electric'  # Skip electric vehicles
        ORDER BY uv.user_id, v.vehicle_type DESC, v.daily_average_km DESC
        """
        cursor.execute(query)
        
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
    """
    Distribute daily driving across a user's vehicles according to your schema
    """
    if not user_vehicles:
        return []
    
    # Base total km on vehicle types and day of week
    base_total_km = sum(v['daily_km'] for v in user_vehicles)
    
    # Weekend adjustment based on vehicle types
    if date_obj.weekday() >= 5:  # Weekend
        total_km = base_total_km * 1.5  # Base weekend increase
    else:
        total_km = base_total_km
    
    # For single vehicle households
    if len(user_vehicles) == 1:
        return [(user_vehicles[0], total_km)]
    
    # For multiple vehicles - distribute based on vehicle type
    results = []
    remaining_km = total_km
    
    # Sort vehicles by type (larger vehicles first)
    sorted_vehicles = sorted(
        user_vehicles,
        key=lambda x: x['vehicle_type'],
        reverse=True
    )
    
    for i, vehicle in enumerate(sorted_vehicles):
        if i == len(sorted_vehicles) - 1:
            # Last vehicle gets remaining distance
            distance = remaining_km
        else:
            # Allocate based on vehicle type
            if vehicle['vehicle_type'] == 'truck':
                portion = np.random.uniform(0.5, 0.8)
            elif vehicle['vehicle_type'] == 'bus':
                portion = np.random.uniform(0.7, 0.9)
            elif vehicle['vehicle_type'] == 'car':
                portion = np.random.uniform(0.3, 0.6)
            else:  # motorcycle
                portion = np.random.uniform(0.1, 0.3)
            
            distance = remaining_km * portion
            remaining_km -= distance
        
        # Ensure reasonable distance bounds
        distance = max(1, min(500, distance))
        results.append((vehicle, round(distance, 2)))
    
    return results

def simulate_daily_fuel_usage(vehicle, date_obj, distance):
    """
    Simulate daily fuel usage based on your exact schema
    """
    try:
        # Skip electric vehicles (shouldn't happen due to query filter)
        if vehicle['fuel_type'] == 'electric':
            return 0, 0, 'none'
        
        season = get_season(date_obj)
        is_weekend = date_obj.weekday() >= 5
        vehicle_type = vehicle['vehicle_type']
        
        # Select driving condition with seasonal probabilities
        driving_condition = np.random.choice(
            list(DRIVING_CONDITION_PROBS[season].keys()),
            p=list(DRIVING_CONDITION_PROBS[season].values())
        )
        
        # Get appropriate efficiency
        efficiency = vehicle[f"{driving_condition}_efficiency"]
        
        # Calculate base fuel used
        base_fuel_used = distance / efficiency
        
        # Apply daily variation (±15%)
        daily_variation = np.random.normal(1.0, 0.075)
        fuel_used = max(0.1, base_fuel_used * daily_variation)
        
        # Apply weekend multiplier if applicable
        if is_weekend:
            multiplier = WEEKEND_USAGE_MULTIPLIER.get(vehicle_type, {}).get(driving_condition, 1.0)
            fuel_used *= multiplier
        
        # Calculate cost
        fuel_price = FUEL_PRICES.get(vehicle['fuel_type'], 0)
        fuel_cost = max(1.0, fuel_used * fuel_price)
        
        return round(fuel_used, 2), round(fuel_cost, 2), driving_condition
        
    except Exception as e:
        print(f"Error simulating for vehicle {vehicle.get('model_name', 'unknown')}: {str(e)}")
        return 5.0, 500.0, "urban"  # Safe default values

def log_daily_consumption(user_id, vehicle_id, user_vehicle_id, date_obj, 
                         fuel_used, fuel_cost, driving_condition):
    """Log daily fuel consumption with duplicate checking"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for existing record
        cursor.execute("""
            SELECT 1 FROM daily_fuel_consumption 
            WHERE user_id = %s AND user_vehicle_id = %s AND consumption_date = %s
        """, (user_id, user_vehicle_id, date_obj))
        
        if cursor.fetchone():
            print(f"Record exists for user {user_id}, vehicle {user_vehicle_id} on {date_obj}")
            return True
        
        # Insert new record
        query = """
        INSERT INTO daily_fuel_consumption 
        (user_id, vehicle_id, user_vehicle_id, consumption_date, 
         fuel_used_liters, fuel_cost, driving_condition)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            user_id,
            vehicle_id,
            user_vehicle_id,
            date_obj,
            fuel_used,
            fuel_cost,
            driving_condition
        ))
        
        conn.commit()
        return True
        
    except MySQLdb.Error as err:
        print(f"Error logging consumption: {err}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_last_consumption_date(user_id, user_vehicle_id):
    """Get the last consumption date for a user's vehicle"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT MAX(consumption_date) as last_date 
            FROM daily_fuel_consumption 
            WHERE user_id = %s AND user_vehicle_id = %s
        """, (user_id, user_vehicle_id))
        
        result = cursor.fetchone()
        return result[0] if result and result[0] else None
    except MySQLdb.Error as err:
        print(f"Error getting last consumption date: {err}")
        return None
    finally:
        if conn:
            conn.close()

def get_simulation_date_ranges():
    """Generate date ranges for past 6 months + current month (up to today)"""
    today = date.today()
    current_month_start = today.replace(day=1)

    date_ranges = []

    # Add last 6 full months
    for i in range(6, 0, -1):
        month_start = (current_month_start - relativedelta(months=1)).replace(day=1)
        month_end = current_month_start - timedelta(days=1)
        date_ranges.append((f"{month_start.strftime('%B_%Y')}", month_start, month_end))
        current_month_start = month_start  # Move back one month

    # Finally add current month up to today
    current_month_real_start = today.replace(day=1)
    date_ranges.append(("current_month", current_month_real_start, today))

    return date_ranges


def calculate_and_log_fuel_consumption():
    """Main function to calculate and log fuel consumption"""
    user_vehicles = fetch_user_vehicles()
    if not user_vehicles:
        print("No fuel-powered user vehicles found")
        return False
    
    date_ranges = get_simulation_date_ranges()
    
    for period_name, start_date, end_date in date_ranges:
        print(f"\nProcessing {period_name.replace('_', ' ')} ({start_date} to {end_date})")
        
        for user_id, vehicles in user_vehicles.items():
            print(f"  User {user_id} with {len(vehicles)} vehicles")
            
            # Calculate all vehicle distances for each day first
            for single_date in (start_date + timedelta(n) for n in range((end_date - start_date).days + 1)):
                # Get distance distribution for all vehicles this day
                vehicle_distances = calculate_vehicle_usage(vehicles, single_date)
                
                for vehicle, distance in vehicle_distances:
                    # Skip if no distance or electric vehicle
                    if distance <= 0 or vehicle['fuel_type'] == 'electric':
                        continue
                    
                    # ✅ Check if specific day's record exists
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT 1 FROM daily_fuel_consumption 
                        WHERE user_id = %s AND user_vehicle_id = %s AND consumption_date = %s
                    """, (user_id, vehicle['user_vehicle_id'], single_date))
                    
                    already_logged = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    
                    if already_logged:
                        continue
                    
                    # Simulate and log
                    fuel_used, fuel_cost, condition = simulate_daily_fuel_usage(
                        vehicle, single_date, distance
                    )
                    
                    log_daily_consumption(
                        user_id,
                        vehicle['vehicle_id'],
                        vehicle['user_vehicle_id'],
                        single_date,
                        fuel_used,
                        fuel_cost,
                        condition
                    )
    
    return True

def generate_fuel_report(user_id):
    """Generate comprehensive fuel consumption report"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        # Get user and vehicle info
        cursor.execute("""
            SELECT 
                uv.id as user_vehicle_id,
                v.model_name,
                v.vehicle_type,
                v.fuel_type,
                uv.license_plate
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
        
        # Get date ranges for reporting
        date_ranges = get_simulation_date_ranges()
        
        # Process each vehicle
        for vehicle in vehicles:
            print(f"\nVehicle: {vehicle['model_name']} ({vehicle['vehicle_type']})")
            print(f"Fuel Type: {vehicle['fuel_type'].upper()}")
            print(f"License Plate: {vehicle['license_plate'] or 'Not specified'}")
            print("-"*50)
            
            total_liters = 0
            total_cost = 0
            total_days = 0
            
            # Process each time period
            for period_name, start_date, end_date in date_ranges:
                cursor.execute("""
                    SELECT 
                        SUM(fuel_used_liters) AS liters,
                        SUM(fuel_cost) AS cost,
                        COUNT(*) AS days
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
                print(f"  Avg Daily: {liters/days:.2f} liters, Tk {cost/days:.2f}" if days > 0 else "  No data")
                
                total_liters += liters
                total_cost += cost
                total_days += days
            
            # Print totals
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
    
    # Calculate and log consumption for all users
    if calculate_and_log_fuel_consumption():
        print("\nSimulation completed successfully!")
        
        # Example: Generate report for user 1
        generate_fuel_report(1)
    else:
        print("\nSimulation encountered errors!")