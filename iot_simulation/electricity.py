import numpy as np

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



# Function to calculate electricity bill
def calculate_bill(total_units):
    billing_rates = [
        (75, 3.80),
        (125, 5.14),
        (100, 5.36),
        (200, 5.63),
        (np.inf, 9.98)
    ]
    service_charge = 10
    demand_charge = 30
    meter_rent = 10
    vat_rate = 0.05

    bill = 0
    remaining_units = total_units

    for slab, rate in billing_rates:
        if remaining_units <= 0:
            break
        units_in_slab = min(slab, remaining_units)
        bill += units_in_slab * rate
        remaining_units -= units_in_slab

    subtotal = bill + service_charge + demand_charge + meter_rent
    vat = subtotal * vat_rate
    total_bill = subtotal + vat
    return total_bill

# Simulate consumption for 31 days
# Simulate consumption for 31 days and print daily consumption and cost
square_footage = 1100  # Example house size in sqft
num_members = 5  # Number of people in the house
solar_capacity = 1.0  # 1 kW solar panel
wind_capacity = 1.0  # 1 kW wind turbine
season = "summer"

try:
    daily_consumptions = []
    daily_costs = []

    print("Day-by-Day Energy Consumption and Cost:")
    print("-" * 50)

    for day in range(1, 32):  # Loop for 31 days
        daily_consumption = simulate_daily_consumption(square_footage, num_members, season, solar_capacity, wind_capacity)
        daily_cost = calculate_bill(daily_consumption)
        
        daily_consumptions.append(daily_consumption)
        daily_costs.append(daily_cost)

        print(f"Day {day}: Consumption = {daily_consumption:.2f} kWh, Cost = Tk {daily_cost:.2f}")

    total_consumption = sum(daily_consumptions)
    total_bill = sum(daily_costs)

    print("\nSummary:")
    print("-" * 50)
    print(f"House Size: {get_house_size_category(square_footage)}")
    print(f"Total Monthly Consumption: {total_consumption:.2f} kWh")
    print(f"Total Electricity Bill: Tk {total_bill:.2f}")
except Exception as e:
    print(f"Error during simulation: {e}")
    raise


# https://bdepoint.com/electric-bill-calculation-bangladesh/