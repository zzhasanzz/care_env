import MySQLdb
import numpy as np
import os
from datetime import date, timedelta
from dotenv import load_dotenv
import calendar

load_dotenv()

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'care_env')

def get_db_connection():
    conn = MySQLdb.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        passwd=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    return conn

# Constants
NON_METERED_SINGLE_BURNER_MONTHLY = 82  # Cubic meters
NON_METERED_DOUBLE_BURNER_MONTHLY = 88  # Cubic meters
SINGLE_BURNER_RATE = 750  # Tk/month
DOUBLE_BURNER_RATE = 800  # Tk/month
METERED_GAS_PRICE = 9.10  # Tk/cubic meter

def simulate_metered_daily_gas_consumption(num_members):
    activities = {
        "cooking": lambda: np.random.normal(0.5, 0.1) * num_members,
        "water_heating": lambda: np.random.normal(0.3, 0.05) * num_members,
        "space_heating": lambda: np.random.uniform(1.0, 2.0)
    }
    daily_gas_usage = sum(func() for func in activities.values())
    return max(0, daily_gas_usage)

def fetch_all_users_gas_info():
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute("""
        SELECT u.id, u.gas_type, uh.num_members 
        FROM user u
        LEFT JOIN user_housing uh ON u.id = uh.user_id
        WHERE u.gas_provider IS NOT NULL
    """)
    
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users

def log_daily_gas_consumption(user_id, date_obj, gas_used, gas_cost, household_type, burner_type=None, num_members=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 1 FROM daily_gas_consumption 
        WHERE user_id = %s AND consumption_date = %s
    """, (user_id, date_obj))
    
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return False  # Already logged
    
    cursor.execute("""
        INSERT INTO daily_gas_consumption
        (user_id, consumption_date, gas_used_cubic_meters, gas_cost, household_type, burner_type, num_members)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, date_obj, gas_used, gas_cost, household_type, burner_type, num_members))
    
    conn.commit()
    cursor.close()
    conn.close()
    return True

def simulate_and_log_all_users_gas():
    users = fetch_all_users_gas_info()
    today = date.today()
    
    start_date = today.replace(day=1) - timedelta(days=62)  # Two months back
    end_date = today

    print(f"Starting simulation from {start_date} to {end_date}")
    
    for user in users:
        user_id = user['id']
        raw_household_type = user['gas_type'] or "metered"  # fallback if null
        num_members = user['num_members'] if user['num_members'] else 4
        
        # Normalize gas type
        household_type = raw_household_type.strip().lower().replace("-", "_")
        
        for single_date in (start_date + timedelta(n) for n in range((end_date - start_date).days + 1)):
            
            if household_type == "metered":
                daily_usage = simulate_metered_daily_gas_consumption(num_members)
                daily_cost = daily_usage * METERED_GAS_PRICE
                log_daily_gas_consumption(user_id, single_date, daily_usage, daily_cost, "metered", num_members=num_members)
            
            elif household_type == "non_metered":
                # Randomly select burner type with 90% double, 10% single
                burner_type = np.random.choice(["double", "single"], p=[0.9, 0.1])
                
                days_in_month = calendar.monthrange(single_date.year, single_date.month)[1]
                
                if burner_type == "single":
                    daily_usage = NON_METERED_SINGLE_BURNER_MONTHLY / days_in_month
                    daily_cost = SINGLE_BURNER_RATE / days_in_month
                else:
                    daily_usage = NON_METERED_DOUBLE_BURNER_MONTHLY / days_in_month
                    daily_cost = DOUBLE_BURNER_RATE / days_in_month
                
                log_daily_gas_consumption(user_id, single_date, daily_usage, daily_cost, "non_metered", burner_type=burner_type)
            
            else:
                print(f"Unknown gas type for user {user_id}: {raw_household_type} - skipping")
    
    print("Simulation completed for all users ✅")

if __name__ == "__main__":
    print("Starting gas consumption simulation...")
    simulate_and_log_all_users_gas()
    print("Gas consumption simulation fully completed.")



#https://bids.org.bd/page/researches/?rid=203#:~:text=For%20measuring%20the%20quantity%2C%20the,Tk.%2Fcubic%20meter).