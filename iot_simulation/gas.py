import numpy as np


# Constants for Non-Metered Households
NON_METERED_SINGLE_BURNER_MONTHLY = 82  # Cubic meters
NON_METERED_DOUBLE_BURNER_MONTHLY = 88  # Cubic meters
SINGLE_BURNER_RATE = 750  # Tk/month
DOUBLE_BURNER_RATE = 800  # Tk/month

# Metered Gas Price
METERED_GAS_PRICE = 9.10  # Tk per cubic meter

NON_METERED_FLOW_RATES = {
    "single_burner": 12 * 10 * 26 * 0.85,  
    "double_burner": 21 * 8 * 26 * 0.85   
}

# Conversion factor (cubic feet to cubic meters)
CUBIC_FEET_TO_CUBIC_METERS = 0.0283168

# Simulate daily gas consumption for metered households
def simulate_metered_daily_gas_consumption(num_members, activities=None):
    """
    Simulate daily gas consumption for metered households.
    :param num_members: Number of household members.
    :param activities: Dictionary of activities and their gas usage (cubic meters/day).
    :return: Daily gas consumption in cubic meters.
    """
    if activities is None:
        activities = {
            "cooking": lambda: np.random.normal(0.5, 0.1) * num_members,  # Per member
            "water_heating": lambda: np.random.normal(0.3, 0.05) * num_members,  # Per member
            "space_heating": lambda: np.random.uniform(1.0, 2.0)  # Random hours/day
        }

    daily_gas_usage = sum(func() for func in activities.values())
    return max(0, daily_gas_usage)  # Ensure no negative usage

# Calculate monthly gas bill for metered households
def calculate_metered_gas_bill(total_gas_usage, price_per_cubic_meter=METERED_GAS_PRICE):
    return total_gas_usage * price_per_cubic_meter

# Simulate monthly gas consumption
def simulate_monthly_gas_consumption(household_type="metered", num_members=4, burner_type="double", days=31):
    if household_type == "non_metered":
        # Calculate fixed usage and billing for non-metered households
        if burner_type == "single":
            monthly_usage = NON_METERED_SINGLE_BURNER_MONTHLY
            monthly_bill = SINGLE_BURNER_RATE
        elif burner_type == "double":
            monthly_usage = NON_METERED_DOUBLE_BURNER_MONTHLY
            monthly_bill = DOUBLE_BURNER_RATE
        else:
            raise ValueError("Invalid burner type. Use 'single' or 'double'.")
        return [monthly_usage / days] * days, monthly_usage, monthly_bill

    elif household_type == "metered":
        # Simulate daily usage and calculate bill for metered households
        daily_usages = [simulate_metered_daily_gas_consumption(num_members) for _ in range(days)]
        total_usage = sum(daily_usages)
        monthly_bill = calculate_metered_gas_bill(total_usage)
        return daily_usages, total_usage, monthly_bill
    else:
        raise ValueError("Invalid household type. Use 'metered' or 'non_metered'.")

# Example: Simulating gas consumption
household_type = "metered"  # Options: "metered" or "non_metered"
burner_type = "double"  # For non-metered households: "single" or "double"
num_members = 5  # For metered households
days = 31  # Number of days in a month

# Simulate gas usage and billing
daily_gas_usages, total_monthly_gas_usage, monthly_gas_bill = simulate_monthly_gas_consumption(
    household_type=household_type,
    num_members=num_members,
    burner_type=burner_type,
    days=days
)

# Print results
print(f"Household Type: {household_type.capitalize()}")
if household_type == "non_metered":
    print(f"Burner Type: {burner_type.capitalize()} Burner")
print("\nDaily Gas Consumption (cubic meters):")
for day, usage in enumerate(daily_gas_usages, start=1):
    print(f"Day {day}: {usage:.2f} cubic meters")
print("\nSummary:")
print(f"Total Monthly Gas Usage: {total_monthly_gas_usage:.2f} cubic meters")
print(f"Total Monthly Gas Bill: Tk {monthly_gas_bill:.2f}")


#https://bids.org.bd/page/researches/?rid=203#:~:text=For%20measuring%20the%20quantity%2C%20the,Tk.%2Fcubic%20meter).