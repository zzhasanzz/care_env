import MySQLdb
import numpy as np
from db import get_db_connection

# Fuel prices as of November 2024
fuel_prices = {
    "petrol": 121,
    "diesel": 105,
    "cng": 43,
    "octane": 125
}

# Fetch vehicle data from the MySQL database
def fetch_vehicle_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch vehicle details
        query = "SELECT * FROM vehicles"
        cursor.execute(query)

        # Get column names
        columns = [desc[0] for desc in cursor.description]
        vehicles = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()
        return vehicles
    except MySQLdb.Error as err:
        print(f"Error: {err}")
        return []

# Simulate daily fuel consumption with randomness
def simulate_daily_fuel_consumption(vehicle, driving_condition="urban"):
    """
    Simulate daily fuel consumption for a vehicle with random travel distance and efficiency.
    :param vehicle: Vehicle data dictionary from the database.
    :param driving_condition: Driving condition ("urban" or "highway").
    :return: Daily fuel consumption (liters) and cost.
    """
    if driving_condition not in ["urban", "highway"]:
        raise ValueError("Invalid driving condition.")

    # Randomize daily distance
    avg_km = vehicle["daily_average_km"]
    daily_km = max(0, np.random.normal(avg_km, avg_km * 0.2))  # Random with 20% std deviation

    # Randomize fuel efficiency
    avg_efficiency = vehicle[f"{driving_condition}_efficiency"]
    efficiency = max(1, np.random.normal(avg_efficiency, avg_efficiency * 0.1))  # 10% std deviation

    # Calculate fuel consumption
    daily_fuel_consumption = daily_km / efficiency

    # Get fuel price
    fuel_price = fuel_prices.get(vehicle["fuel_type"].lower(), 0)

    # Calculate daily cost
    daily_cost = daily_fuel_consumption * fuel_price

    return daily_fuel_consumption, daily_cost

# Simulate monthly fuel consumption
def simulate_monthly_fuel_consumption(vehicle, driving_condition="urban", days=31):
    """
    Simulate monthly fuel consumption for a vehicle with randomized daily usage.
    :param vehicle: Vehicle data dictionary from the database.
    :param driving_condition: Driving condition ("urban" or "highway").
    :param days: Number of days in the month.
    :return: Daily consumption and costs, total monthly consumption, and total cost.
    """
    daily_data = [
        simulate_daily_fuel_consumption(vehicle, driving_condition=driving_condition)
        for _ in range(days)
    ]
    daily_consumptions = [data[0] for data in daily_data]
    daily_costs = [data[1] for data in daily_data]
    total_consumption = sum(daily_consumptions)
    total_cost = sum(daily_costs)

    return daily_consumptions, daily_costs, total_consumption, total_cost

# Main logic
def main():
    vehicles = fetch_vehicle_data()
    if not vehicles:
        print("No vehicles found in the database.")
        return

    print("Vehicle Fuel Consumption Simulation:")
    print("-" * 50)

    for vehicle in vehicles:
        print(f"\nSimulating for: {vehicle['model_name']} ({vehicle['fuel_type']})")
        daily_consumptions, daily_costs, total_consumption, total_cost = simulate_monthly_fuel_consumption(vehicle)

        # Print daily usage and costs
        for day, (usage, cost) in enumerate(zip(daily_consumptions, daily_costs), start=1):
            print(f"Day {day}: {usage:.2f} liters, Cost = Tk {cost:.2f}")

        # Print summary
        print(f"\nSummary for {vehicle['model_name']}:")
        print(f"Total Monthly Fuel Usage: {total_consumption:.2f} liters")
        print(f"Total Monthly Fuel Cost: Tk {total_cost:.2f}")

if __name__ == "__main__":
    main()
