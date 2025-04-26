import MySQLdb
import numpy as np
import os
import datetime
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta
# from db import get_db_connection

load_dotenv()  # This loads environment variables from the .env file

# Define water usage categories with random distributions
water_usage_categories = {
    "drinking_cooking": {
        "usage_per_person": lambda: max(0, np.random.normal(15, 2)),  # Normal distribution
        "type": "individual"
    },
    "bathing": {
        "usage_per_person": lambda: max(0, np.random.normal(70, 10)),  # Normal distribution
        "type": "individual"
    },
    "toilet": {
        "usage_per_person": lambda: max(0, np.random.normal(50, 5)),  # Normal distribution
        "type": "individual"
    },
    "cleaning": {
        "usage_per_sqm": lambda: np.random.uniform(0.6, 1.0),  # Uniform distribution
        "type": "house_size"
    },
    "washing_machine": {
        "usage_per_cycle": 60,  # Fixed liters per cycle
        "cycles_per_day": lambda members: max(1, np.random.poisson(members / 4)),  # Poisson distribution
        "type": "appliance"
    },
    "dishwasher": {
        "usage_per_cycle": 20,  # Fixed liters per cycle
        "cycles_per_day": lambda members: max(1, np.random.poisson(members / 5)),  # Poisson distribution
        "type": "appliance"
    },
    "gardening": {
        "usage_per_sqm": lambda: np.random.uniform(1.0, 2.0),  # Uniform distribution
        "type": "outdoor"
    },
    "car_washing": {
        "usage_per_car": lambda: max(0, np.random.normal(120, 20)),  # Normal distribution
        "washes_per_week": 2,  # Fixed washes per week
        "type": "outdoor"
    }
}

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = "care_env"


def get_db_connection():
    print(f"MYSQL_HOST={MYSQL_HOST}, MYSQL_USER={MYSQL_USER}, MYSQL_PASSWORD={MYSQL_PASSWORD}, MYSQL_DATABASE={MYSQL_DATABASE}")
    try:
        conn = MySQLdb.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            passwd=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        return conn
    except MySQLdb.Error as err:
        print(f"Error: Unable to connect to the database. {err}")
        raise

# Seasonal adjustments (multipliers)
seasonal_adjustments = {
    "summer": {
        "bathing": 1.0,
        "gardening": 1.0,
        "cleaning": 1.0,
        "washing_machine": 1.0,
        "dishwasher": 1.0
    },
    "winter": {
        "bathing": 0.7,  # 30% reduction
        "gardening": 0.2,  # 80% reduction
        "cleaning": 0.9,  # 10% reduction
        "washing_machine": 0.8,  # 20% reduction
        "dishwasher": 0.9  # 10% reduction
    }
}

def fetch_all_users():
    """
    Fetch all users and their housing details for calculating water consumption.
    Calculates num_cars from car_ids (comma-separated list).
    """
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            u.id AS user_id, 
            uh.house_size_sqft, 
            uh.num_members, 
            u.water_provider, 
            UP.unit_price,
            u.car_ids  # We'll process this to get num_cars
        FROM user u
        JOIN user_housing uh ON u.id = uh.user_id
        JOIN utility_providers UP ON u.water_provider = UP.id
        WHERE u.water_provider IS NOT NULL
    """)
    users = cursor.fetchall()
    
    # Process car_ids to calculate num_cars
    for user in users:
        if user['car_ids'] and user['car_ids'].strip():
            # Count non-empty items in comma-separated list
            user['num_cars'] = len([x for x in user['car_ids'].split(',') if x.strip()])
        else:
            user['num_cars'] = 0  # No cars if empty or None

    cursor.close()
    conn.close()
    return users


def log_daily_water_consumption(user_id, utility_provider_id, date, liters_consumed, unit_price):
    """
    Log daily water consumption into the daily_water_consumption table with daily bill.
    Only inserts new records or updates if they don't exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # First check if record already exists for this date and user
        cursor.execute("""
            SELECT 1 FROM daily_water_consumption 
            WHERE user_id = %s AND consumption_date = %s
        """, (user_id, date))
        
        if cursor.fetchone():
            print(f"Water record already exists for user {user_id} on {date} - skipping")
            return

        # Calculate daily bill (convert liters to cubic meters if needed)
        # Assuming unit_price is per 1000 liters (1 cubic meter)
        daily_bill = (liters_consumed / 1000) * unit_price

        # Insert new record only
        query = """
            INSERT INTO daily_water_consumption 
            (user_id, utility_provider_id, consumption_date, liters_consumed, daily_bill)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, utility_provider_id, date, liters_consumed, daily_bill))
        conn.commit()
        print(f"Logged water consumption for user {user_id} on {date}: {liters_consumed:.2f} liters")

    except MySQLdb.IntegrityError as e:
        print(f"IntegrityError logging water consumption: {e} for user_id={user_id}, date={date}")
    except MySQLdb.Error as e:
        print(f"MySQL Error logging water consumption: {e}")
    finally:
        cursor.close()
        conn.close()

def calculate_and_log_water_consumption():
    """
    Correct version: fill missing days for past 6 months + current month
    """
    all_users = fetch_all_users()
    today = datetime.date.today()
    six_months_ago = today.replace(day=1) - relativedelta(months=6)

    for user in all_users:
        user_id = user['user_id']
        utility_provider_id = user['water_provider']
        house_size = user['house_size_sqft']
        num_members = user['num_members']
        num_cars = user['num_cars']
        unit_price = user['unit_price']

        print(f"\nProcessing water data for user {user_id}")

        current_date = six_months_ago
        while current_date <= today:
            # Check if this date's record already exists
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 1 FROM daily_water_consumption
                WHERE user_id = %s AND consumption_date = %s
            """, (user_id, current_date))

            exists = cursor.fetchone()
            cursor.close()
            conn.close()

            if exists:
                # Already recorded, no need to insert
                current_date += datetime.timedelta(days=1)
                continue

            # Not recorded -> simulate and log it
            month = current_date.month
            season = "summer" if 4 <= month <= 9 else "winter"

            liters_consumed = simulate_daily_water_usage(
                square_footage=house_size,
                num_members=num_members,
                has_garden=True,
                num_cars=num_cars,
                season=season
            )

            log_daily_water_consumption(
                user_id=user_id,
                utility_provider_id=utility_provider_id,
                date=current_date,
                liters_consumed=liters_consumed,
                unit_price=unit_price
            )

            current_date += datetime.timedelta(days=1)

    print("\n✅ Water simulation complete for all users!")


# Function to simulate daily water usage
def simulate_daily_water_usage(square_footage, num_members, has_garden=True, num_cars=1, season="summer"):
    daily_water_usage = 0
    adjustments = seasonal_adjustments.get(season, seasonal_adjustments["summer"])  # Default to summer

    # Calculate individual water usage
    for category, details in water_usage_categories.items():
        if details["type"] == "individual":
            usage = sum(details["usage_per_person"]() for _ in range(num_members))  # Random per person
            daily_water_usage += usage * adjustments.get(category, 1.0)
        elif details["type"] == "house_size":
            sqm = square_footage / 10.764  # Convert sqft to sqm
            usage = details["usage_per_sqm"]() * sqm  # Random per sqm
            daily_water_usage += usage * adjustments.get(category, 1.0)
        elif details["type"] == "appliance":
            cycles = details["cycles_per_day"](num_members)  # Random cycles
            daily_water_usage += details["usage_per_cycle"] * cycles * adjustments.get(category, 1.0)
        elif details["type"] == "outdoor" and has_garden:
            if category == "gardening":
                sqm = square_footage / 10.764  # Convert sqft to sqm
                usage = details["usage_per_sqm"]() * sqm  # Random per sqm
                daily_water_usage += usage * adjustments.get(category, 1.0)
            elif category == "car_washing":
                weekly_usage = sum(details["usage_per_car"]() for _ in range(num_cars)) * details["washes_per_week"]
                daily_water_usage += weekly_usage / 7  # Average daily usage

    return daily_water_usage

def main(user_id):
    """
    Main function to calculate AND LOG daily water consumption for a user.
    Shows existing data and ensures missing days are filled.
    """
    try:
        # First ensure all consumption data is logged
        calculate_and_log_water_consumption()
        
        # Now fetch and display the data
        conn = get_db_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        # Get user details
        cursor.execute("""
            SELECT 
                u.id,
                uh.house_size_sqft,
                uh.num_members,
                u.water_provider,
                up.unit_price,
                u.car_ids
            FROM user u
            JOIN user_housing uh ON u.id = uh.user_id
            JOIN utility_providers up ON u.water_provider = up.id
            WHERE u.id = %s
        """, (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            raise ValueError("User not found or missing water provider")
        
        # Get current month consumption summary
        current_month_start = datetime.date.today().replace(day=1)
        cursor.execute("""
            SELECT 
                SUM(liters_consumed) AS total_liters,
                SUM(daily_bill) AS total_bill,
                COUNT(*) AS days_recorded
            FROM daily_water_consumption
            WHERE user_id = %s
            AND consumption_date BETWEEN %s AND %s
        """, (user_id, current_month_start, datetime.date.today()))
        monthly_data = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        # Display results
        print(f"\nWater Consumption Report for User {user_id}")
        print("----------------------------------------")
        print(f"House Size: {user_data['house_size_sqft']} sqft")
        print(f"Household Members: {user_data['num_members']}")
        print(f"Current Month Usage: {monthly_data['total_liters']:.2f} liters")
        print(f"Current Month Bill: Tk {monthly_data['total_bill']:.2f}")
        print(f"Days Recorded: {monthly_data['days_recorded']}")
        print("----------------------------------------")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Example usage
    main(user_id=1)

    
# https://www.thedailystar.net/city/news/wasa-hikes-water-tariff-residential-commercial-use-1874149