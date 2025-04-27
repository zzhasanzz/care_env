import MySQLdb
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return MySQLdb.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        passwd=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )

def create_safe_limits_for_all_users():
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Fetch users with housing and providers
    cursor.execute("""
        SELECT u.id AS user_id, uh.num_members, 
               u.electricity_provider, u.gas_provider, u.water_provider
        FROM user u
        LEFT JOIN user_housing uh ON u.id = uh.user_id
    """)
    users = cursor.fetchall()

    base_limits = {
        'electricity': 55,  
        'gas': 20,
        'fuel': 50,
        'water': 7
    }

    for user in users:
        user_id = user['user_id']
        num_members = user['num_members'] or 4

        # Default safe limits
        electricity_limit = base_limits['electricity'] * num_members
        gas_limit = base_limits['gas'] * num_members
        fuel_limit = base_limits['fuel'] * num_members
        water_limit = base_limits['water'] * num_members

        def fetch_emission_factor(provider_id):
            if not provider_id:
                return 1.0
            cursor.execute("SELECT emission_factor FROM utility_providers WHERE id = %s", (provider_id,))
            result = cursor.fetchone()
            if result and result['emission_factor'] is not None:
                return result['emission_factor']
            return 1.0

        electricity_factor = fetch_emission_factor(user['electricity_provider'])
        gas_factor = fetch_emission_factor(user['gas_provider'])
        water_factor = fetch_emission_factor(user['water_provider'])

        electricity_limit *= electricity_factor
        gas_limit *= gas_factor
        water_limit *= water_factor

        total_safe_limit = electricity_limit + gas_limit + fuel_limit + water_limit

        # 🔥 Check if user already has a record
        cursor.execute("SELECT id FROM safe_limits WHERE user_id = %s", (user_id,))
        existing = cursor.fetchone()

        if existing:
            # ✅ If exists, UPDATE
            cursor.execute("""
                UPDATE safe_limits
                SET electricity_safe_limit = %s,
                    gas_safe_limit = %s,
                    fuel_safe_limit = %s,
                    water_safe_limit = %s,
                    total_safe_limit = %s
                WHERE user_id = %s
            """, (electricity_limit, gas_limit, fuel_limit, water_limit, total_safe_limit, user_id))
        else:
            # ✅ If doesn't exist, INSERT
            cursor.execute("""
                INSERT INTO safe_limits
                (user_id, electricity_safe_limit, gas_safe_limit, fuel_safe_limit, water_safe_limit, total_safe_limit)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, electricity_limit, gas_limit, fuel_limit, water_limit, total_safe_limit))


    conn.commit()
    cursor.close()
    conn.close()

def update_safe_limits_for_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Fetch updated housing and providers
    cursor.execute("""
        SELECT uh.num_members,
               u.electricity_provider, u.gas_provider, u.water_provider
        FROM user u
        LEFT JOIN user_housing uh ON u.id = uh.user_id
        WHERE u.id = %s
    """, (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return

    num_members = user['num_members'] or 4

    # Default per member safe limits
    base_limits = {
        'electricity': 55,  
        'gas': 20,
        'fuel': 50,
        'water': 7
    }


    # Calculate base safe limits
    electricity_limit = base_limits['electricity'] * num_members
    gas_limit = base_limits['gas'] * num_members
    fuel_limit = base_limits['fuel'] * num_members
    water_limit = base_limits['water'] * num_members

    # Apply provider-specific emission factors
    def fetch_emission_factor(provider_id):
        if not provider_id:
            return 1.0
        cursor.execute("SELECT emission_factor FROM utility_providers WHERE id = %s", (provider_id,))
        result = cursor.fetchone()
        if result and result['emission_factor'] is not None:
            return result['emission_factor']
        return 1.0

    electricity_factor = fetch_emission_factor(user['electricity_provider'])
    gas_factor = fetch_emission_factor(user['gas_provider'])
    water_factor = fetch_emission_factor(user['water_provider'])

    electricity_limit *= electricity_factor
    gas_limit *= gas_factor
    water_limit *= water_factor

    total_safe_limit = electricity_limit + gas_limit + fuel_limit + water_limit

    # Now UPDATE safe_limits table
    cursor.execute("""
        UPDATE safe_limits
        SET electricity_safe_limit = %s,
            gas_safe_limit = %s,
            fuel_safe_limit = %s,
            water_safe_limit = %s,
            total_safe_limit = %s
        WHERE user_id = %s
    """, (electricity_limit, gas_limit, fuel_limit, water_limit, total_safe_limit, user_id))

    conn.commit()
    cursor.close()
    conn.close()


if _name_ == "_main_":
    create_safe_limits_for_all_users()