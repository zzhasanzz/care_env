import MySQLdb
import numpy as np
import os
import datetime
from dotenv import load_dotenv
# from db import get_db_connection

load_dotenv()  # This loads environment variables from the .env file


# Define appliances and their power ratings with usage hours
appliances = {
    "fan": {
        "power": 0.07,
        "summer_hours": lambda: np.random.normal(12, 2),
        "winter_hours": lambda: np.random.poisson(3)
    },
    "light": {
        "power": 0.01,
        "daily_hours": lambda: np.random.normal(6, 1)
    },
    "ac": {
        "power": 1.4,
        "summer_hours": lambda: np.random.uniform(2, 6),
        "winter_hours": lambda: 0
    },
    "fridge": {
        "power": 0.15,
        "daily_hours": lambda: np.random.normal(8, 0.5)
    },
    "tv": {
        "power": 0.1,
        "daily_hours": lambda: np.random.poisson(4)
    },
    "washing_machine": {
        "power": 0.5,
        "daily_hours": lambda: np.random.normal(1, 0.2)
    },
    "computer": {
        "power": 0.2,
        "daily_hours": lambda: np.random.normal(5, 1)
    },
    "microwave": {
        "power": 1.2,
        "daily_hours": lambda: np.random.normal(0.5, 0.1)
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

    
def fetch_user_data(user_id):
    """
    Fetch housing details and electricity provider info for the user.
    """
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    # Fetch user housing data
    cursor.execute("""
        SELECT uh.house_size_sqft, uh.num_members, uh.solar_panel_watt,
               uh.wind_source_watt, u.electricity_provider
        FROM user_housing uh
        JOIN user u ON uh.user_id = u.id
        WHERE u.id = %s
    """, (user_id,))
    housing_data = cursor.fetchone()

    if not housing_data:
        raise ValueError("No housing data found for the given user.")

    # Fetch utility provider's unit price
    electricity_provider = housing_data['electricity_provider']
    cursor.execute("""
        SELECT unit_price FROM utility_providers
        WHERE id = %s
    """, (electricity_provider,))
    provider_data = cursor.fetchone()

    if not provider_data:
        raise ValueError("No utility provider found for the given user.")

    housing_data['base_rate'] = provider_data['unit_price']
    return housing_data

# Function to categorize house size based on square footage
def get_house_size_category(square_footage):
    if square_footage <= 1000:
        return "small"
    elif 1001 <= square_footage <= 1600:
        return "medium"
    else:
        return "large"

# Function to scale appliances based on house size and members
def scale_appliances(house_size, num_members):
    """
    Scale appliances based on house size and number of members.
    """
    house_size_multiplier = {
        "small": 1.0,
        "medium": 1.5,
        "large": 2.0
    }
    member_usage_multiplier = num_members / 3  # Baseline: 3 members

    scaled_appliances = {}
    for appliance, details in appliances.items():
        scaled_appliances[appliance] = {
            "power": details["power"],
            "summer_hours": (
                lambda base_func=details.get("summer_hours"): max(0, base_func() * member_usage_multiplier)
                if base_func else None
            ),
            "winter_hours": (
                lambda base_func=details.get("winter_hours"): max(0, base_func() * member_usage_multiplier)
                if base_func else None
            ),
            "daily_hours": (
                lambda base_func=details.get("daily_hours"): max(0, base_func() * member_usage_multiplier)
                if base_func else None
            )
        }

    # Apply house size scaling
    final_appliances = {}
    multiplier = int(house_size_multiplier[house_size])
    for appliance, scaled_detail in scaled_appliances.items():
        for i in range(multiplier):
            final_appliances[f"{appliance}_{i}"] = scaled_detail

    return final_appliances


# Function to simulate renewable energy generation
def simulate_renewable_generation(solar_capacity=0, wind_capacity=0, hours_of_sunlight=np.random.normal(8, 1), avg_wind_hours=np.random.normal(5, 2)):
    solar_output = solar_capacity * 0.2 * np.random.normal(hours_of_sunlight, 1)  # 20% efficiency
    wind_output = wind_capacity * 0.3 * np.random.normal(avg_wind_hours, 1)  # 30% efficiency
    return max(0, solar_output) + max(0, wind_output)

# Function to simulate daily energy consumption
def simulate_daily_consumption(square_footage, num_members, season="summer", solar_capacity=0, wind_capacity=0):
    house_size = get_house_size_category(square_footage)
    scaled_appliances = scale_appliances(house_size, num_members)

    total_consumption = 0
    for appliance, details in scaled_appliances.items():
        try:
            hours = 0  # Default to 0 if hours_func is invalid

            # Check for seasonal or daily hours
            if appliance.startswith("fan") or appliance.startswith("ac"):
                hours_func = details.get(f"{season}_hours")
            else:
                hours_func = details.get("daily_hours")

            # Validate callable
            if callable(hours_func):
                result = hours_func()
                if result is not None:
                    hours = max(0, result)

            # Calculate consumption
            consumption = details["power"] * hours
            total_consumption += consumption
        except Exception as e:
            print(f"Error simulating appliance {appliance}: {e}")
            raise

    renewable_generation = simulate_renewable_generation(solar_capacity, wind_capacity)
    net_consumption = max(0, total_consumption - renewable_generation)
    return net_consumption



def fetch_all_users():
    """
    Fetch all users and their housing details for calculating daily consumption.
    """
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT u.id AS user_id, u.electricity_provider AS utility_provider_id, 
               uh.house_size_sqft, uh.num_members, uh.solar_panel_watt, uh.wind_source_watt
        FROM user u
        LEFT JOIN user_housing uh ON u.id = uh.user_id
    """)
    users = cursor.fetchall()  # Corrected this line
    cursor.close()
    conn.close()
    return users


def log_daily_consumption(user_id, utility_provider_id, date, units_consumed, base_rate, multipliers, tiers):
    """
    Log daily consumption into the daily_electricity_consumption table with daily bill.
    Ensures rows are inserted or updated only when necessary.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Calculate daily bill using the billing logic
        daily_bill = calculate_bill(
            total_units=units_consumed,
            base_rate=base_rate,
            multipliers=multipliers,
            tiers=tiers
        )

        # Insert or conditionally update the daily consumption and daily bill
        query = """
            INSERT INTO daily_electricity_consumption 
            (user_id, utility_provider_id, consumption_date, units_consumed, daily_bill)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                units_consumed = IFNULL(units_consumed, VALUES(units_consumed)),
                daily_bill = IFNULL(daily_bill, VALUES(daily_bill));
        """
        # Execute the query
        cursor.execute(query, (user_id, utility_provider_id, date, units_consumed, daily_bill))
        conn.commit()

    except MySQLdb.IntegrityError as e:
        print(f"IntegrityError: {e} for user_id={user_id}, date={date}")
    except MySQLdb.Error as e:
        print(f"MySQL Error: {e}")
    finally:
        cursor.close()
        conn.close()




def calculate_and_log_consumption():
    """
    Calculate and log daily consumption and daily bill for all users for the last 30 days.
    """
    all_users = fetch_all_users()
    today = datetime.date.today()

    # Billing configuration
    multipliers = [1.00, 1.35, 1.41, 1.48, 2.63]
    tiers = [75, 125, 100, 200, float('inf')]

    for user in all_users:
        user_id = user['user_id']
        utility_provider_id = user['utility_provider_id']
        house_size = user['house_size_sqft']
        num_members = user['num_members']
        solar_capacity = user['solar_panel_watt']
        wind_capacity = user['wind_source_watt']
        base_rate = fetch_user_data(user_id)['base_rate']  # Get the base rate from user data

        # Simulate consumption for the last 90 days
        for day_offset in range(90):
            date = today - datetime.timedelta(days=day_offset)
            #print(f"Processing date: {date}") 
            units_consumed = simulate_daily_consumption(
                house_size, num_members, season="summer",
                solar_capacity=solar_capacity, wind_capacity=wind_capacity
            )
            print(f"User {user_id}, Date {date}: {units_consumed} kWh")  # Debugging
            log_daily_consumption(user_id, utility_provider_id, date, units_consumed, base_rate, multipliers, tiers)



def calculate_bill(total_units, base_rate, multipliers, tiers, service_charge=10, demand_charge=30, meter_rent=10, vat_rate=0.05):
    """
    Calculate the total electricity bill for a given number of units with fixed charges and VAT.
    """
    # Calculate tiered rates dynamically
    rates = [base_rate * multiplier for multiplier in multipliers]
    total_bill = 0
    remaining_units = total_units

    # Calculate the base bill using tiered rates
    for tier_limit, rate in zip(tiers, rates):
        if remaining_units <= 0:
            break
        units_in_tier = min(remaining_units, tier_limit)
        total_bill += units_in_tier * rate
        remaining_units -= units_in_tier

    # Handle remaining units for the last tier
    if remaining_units > 0:
        total_bill += remaining_units * rates[-1]

    # Add fixed charges
    subtotal = total_bill + service_charge + demand_charge + meter_rent

    # Add VAT
    vat = subtotal * vat_rate
    total_bill_with_vat = subtotal + vat

    return total_bill_with_vat


def main(user_id):
    """
    Main function to calculate electricity consumption and bill for a user.
    """
    try:
        # Fetch user data from the database
        user_data = fetch_user_data(user_id)
        house_size = user_data['house_size_sqft']
        num_members = user_data['num_members']
        solar_capacity = user_data['solar_panel_watt']
        wind_capacity = user_data['wind_source_watt']
        base_rate = user_data['base_rate']
        season = "summer"

        # Billing configuration
        multipliers = [1.00, 1.35, 1.41, 1.48, 2.63]
        tiers = [75, 125, 100, 200, float('inf')]

        # Simulate monthly consumption
        total_units = sum(simulate_daily_consumption(house_size, num_members, season , solar_capacity, wind_capacity) for _ in range(31))

        # Calculate the total bill
        total_bill = calculate_bill(total_units, base_rate, multipliers, tiers)

        # Output results
        print(f"Total Monthly Consumption: {total_units:.2f} kWh")
        print(f"Total Electricity Bill: Tk {total_bill:.2f}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Replace 1 with the user_id of the logged-in user
    main(user_id=1)
    calculate_and_log_consumption()




# https://bdepoint.com/electric-bill-calculation-bangladesh/
