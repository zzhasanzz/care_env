import MySQLdb
import numpy as np
import os
import datetime
from dotenv import load_dotenv
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

YSQL_HOST = os.getenv('MYSQL_HOST')
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
    """
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT u.id AS user_id, uh.house_size_sqft, uh.num_members, u.water_provider, UP.unit_price
        FROM user u
        JOIN user_housing uh ON u.id = uh.user_id
        JOIN utility_providers UP ON u.water_provider = UP.id
        WHERE u.water_provider IS NOT NULL
    """)
    users = cursor.fetchall()

    cursor.close()
    conn.close()
    return users

def log_daily_water_consumption(user_id, utility_provider_id, date, liters_consumed, unit_price):
    """
    Log daily water consumption into the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        daily_bill = (liters_consumed / 1000) * unit_price  # Tariff per 1000 liters
        query = """
            INSERT INTO daily_water_consumption 
            (user_id, utility_provider_id, consumption_date, liters_consumed, daily_bill)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                liters_consumed = VALUES(liters_consumed),
                daily_bill = VALUES(daily_bill);
        """
        cursor.execute(query, (user_id, utility_provider_id, date, liters_consumed, daily_bill))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def calculate_and_log_water_consumption():
    """
    Calculate and log daily water consumption for all users for the past 90 days.
    """
    all_users = fetch_all_users()
    today = datetime.date.today()

    for user in all_users:
        for day_offset in range(90):
            date = today - datetime.timedelta(days=day_offset)
            liters_consumed = simulate_daily_water_usage(
                square_footage=user['house_size_sqft'],
                num_members=user['num_members'],
                has_garden=True,
                num_cars=1,
                season="summer"
            )
            log_daily_water_consumption(
                user_id=user['user_id'],
                utility_provider_id=user['water_provider'],
                date=date,
                liters_consumed=liters_consumed,
                unit_price=user['unit_price']
            )

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

# Function to calculate monthly water usage
def simulate_monthly_water_usage(square_footage, num_members, has_garden=True, num_cars=1, days=31, season="summer"):
    daily_usages = [
        simulate_daily_water_usage(square_footage, num_members, has_garden, num_cars, season)
        for _ in range(days)
    ]
    return sum(daily_usages)

# Example: Simulating water usage for a household
square_footage = 1400  # House size in sqft
num_members = 5  # Number of members
has_garden = True  # Garden present
num_cars = 1  # Number of cars
season = "summer"  # Set season to winter

# Simulate daily and monthly water usage
daily_water_usage = simulate_daily_water_usage(square_footage, num_members, has_garden, num_cars, season)
monthly_water_usage = simulate_monthly_water_usage(square_footage, num_members, has_garden, num_cars, days=31, season=season)

# Tariff per 1,000 liters
water_tariff = 14.46  # Tk per 1,000 liters
monthly_water_bill = (monthly_water_usage / 1000) * water_tariff

print(f"Daily Water Usage ({season.title()}): {daily_water_usage:.2f} liters")
print(f"Monthly Water Usage ({season.title()}): {monthly_water_usage:.2f} liters")
print(f"Monthly Water Bill ({season.title()}): Tk {monthly_water_bill:.2f}")

# https://www.thedailystar.net/city/news/wasa-hikes-water-tariff-residential-commercial-use-1874149