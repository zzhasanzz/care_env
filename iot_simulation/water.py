import numpy as np

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