
<h1 align="center">care .env</h1>


<h2 align="center">Monitor your Energy and Utility Consumption</h2>


## Project Overview

The **care .env** project is a web application designed to track and analyze the utility consumption (electricity, water, gas, fuel) and its associated carbon footprint for users. The platform performs simulations to mimic real usage, collects consumption data,  and provides detailed reports to help users understand their energy usage, carbon footprint, and ways to reduce them. The system also integrates wallet management for bill payments.

This system is primarily focused on:

- **Utility Consumption Monitoring**: Electricity, water, gas, and fuel consumption.
- **Carbon Footprint Calculation**: Estimating CO₂ emissions based on the consumption data.
- **Wallet Management**: Enabling users to pay their utility bills and track their wallet balance.
- **Detailed Reports**: Providing users with easy-to-read, interactive reports.

## Features

- **User Authentication**: Login and sign-up functionalities.
- **Dashboard**: Overview of utility consumption (electricity, water, gas, fuel) and carbon footprint for the user.
- **Daily Consumption Logs**: Detailed daily consumption data for electricity, water, gas, and fuel.
- **Carbon Footprint Tracking**: Track and visualize the CO₂ emissions for the user based on consumption.
- **Reports**:
    - **Detailed Carbon Reports**: Detailed reports on carbon emissions from various utility sources.
    - **Bill Payment**: View and pay utility bills for electricity, water, gas, and fuel.
    - **Usage Histograms**: Interactive charts showing historical utility usage and emissions.
- **Wallet Management**: Users can manage their wallet balance and pay bills using their available balance.

## Setup and Installation

### Prerequisites

- Python 3.x
- MySQL Database
- Flask
- Chart.js (for data visualization)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/care-environment.git
cd care_env
```

### 2. Set up environment variables

Create a `.env` file in the project root directory and add your database and other configurations:

```bash
MYSQL_HOST=your_mysql_host
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=care_env
SECRET_KEY=your_secret_key
```

### 3. Install dependencies

Create a virtual environment and install the necessary Python libraries.

```bash
python3 -m venv venv
source venv/bin/activate  # For Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 4. Set up the database

Make sure you have a MySQL database set up and run the necessary SQL scripts to create the required tables.

```bash
# Run SQL migrations (can use Flask-Migrate or manually run the scripts)
python manage.py db upgrade
```

### 5. Run the application

Start the Flask development server:

```bash
python app.py
```

You can now visit the application in your browser at [http://localhost:5000](http://localhost:5000).

### 6. Frontend Chart Configuration

This project uses **Chart.js** for data visualization. The charts are displayed on the frontend within the following views:

- **Daily Consumption**: Line charts showing the daily usage and corresponding cost (for electricity, water, gas, and fuel).
- **Usage Histograms**: Bar charts visualizing the monthly utility consumption and associated costs.

### 7. Database Schema

Here’s a brief overview of the relevant database tables:

- **user**: Stores user information such as name, email, and login credentials.
- **user_vehicles**: Contains the vehicles associated with users and their usage data.
- **daily_electricity_consumption**: Stores daily consumption data for electricity and associated bills.
- **daily_water_consumption**: Stores daily consumption data for water and associated bills.
- **daily_gas_consumption**: Stores daily consumption data for gas and associated bills.
- **daily_fuel_consumption**: Stores daily fuel consumption data for vehicles.
- **daily_carbon_footprint**: Stores the calculated carbon footprint for electricity, water, gas, and fuel consumption.


---

### 8. API Endpoints


#### a. **Login & Authentication**

##### `POST /login`
- **Description**: Redirects to the Google OAuth login page.
- **Query Parameters**: None
- **Response**: Redirects to Google OAuth authorization.

##### `GET /authorize`
- **Description**: Handles the callback from Google OAuth and retrieves the user's information.
- **Query Parameters**: None
- **Response**: 
  - Redirects to the user's dashboard or update page if the user does not exist in the database.
  - Redirects to the admin dashboard if the user is an admin.

#### 2. **User Profile Management**

##### `GET /profile`
- **Description**: Fetches the user's profile information from the session and renders the profile page.
- **Query Parameters**: None
- **Response**: Returns the profile page with user details, vehicles, and wallet balance.

##### `POST /update_user`
- **Description**: Updates the user's information such as phone number, address, and utility providers.
- **Query Parameters**: None
- **Form Data**: 
  - `phone`: User's phone number
  - `address`: User's address
  - `division`: User's division
  - `electricity_provider`: Electricity provider ID
  - `water_provider`: Water provider ID
  - `gas_provider`: Gas provider ID
  - `gas_type`: Gas type (metered or non-metered)
  - `vehicle details`: Information for any vehicle updates
  - `wallet details`: User wallet information (username, phone, password)
- **Response**: 
  - Redirects back to the dashboard if the update is successful.
  - If there is an error (e.g., invalid password), an error message is flashed.

#### 3. **Utility Providers**

##### `GET /get_providers/<division>`
- **Description**: Fetches utility providers based on the user’s division (e.g., electricity, water, gas).
- **Query Parameters**: 
  - `division`: The user's division.
- **Response**: 
  - Returns a JSON response with a list of available utility providers for the given division.

##### `GET /admin/view_providers`
- **Description**: Admin view to see all utility providers and their rankings based on the number of users.
- **Query Parameters**: None
- **Response**: 
  - Renders a template displaying utility providers' data including the rank based on the number of users.

#### 4. **Utility Bill Management**

##### `GET /view_electricity_bills`
- **Description**: Fetches the user’s electricity bills and their payment status.
- **Query Parameters**: None
- **Response**: Renders a page displaying the user’s electricity bills (total and payment status).

##### `GET /view_electricity_bill_detail/<month>/<year>`
- **Description**: Fetches detailed consumption data for a specific month and year for electricity.
- **Query Parameters**: 
  - `month`: The month of the bill.
  - `year`: The year of the bill.
- **Response**: Renders a page showing daily electricity consumption and bills for the selected month.

##### `POST /pay_electricity_bill`
- **Description**: Allows the user to pay for their electricity bill.
- **Request Body**: 
  - `month`: The month of the bill.
  - `year`: The year of the bill.
  - `password`: User’s wallet password.
- **Response**: 
  - Returns a JSON response indicating success or failure.
  - If successful, the user's balance is updated and the bill is marked as paid.

##### `GET /view_water_bills`
- **Description**: Fetches the user’s water bills and their payment status.
- **Query Parameters**: None
- **Response**: Renders a page displaying the user’s water bills (total and payment status).

##### `GET /view_water_bill_detail/<month>/<year>`
- **Description**: Fetches detailed consumption data for a specific month and year for water.
- **Query Parameters**: 
  - `month`: The month of the bill.
  - `year`: The year of the bill.
- **Response**: Renders a page showing daily water consumption and bills for the selected month.

##### `POST /pay_water_bill`
- **Description**: Allows the user to pay for their water bill.
- **Request Body**: 
  - `month`: The month of the bill.
  - `year`: The year of the bill.
  - `password`: User’s wallet password.
- **Response**: 
  - Returns a JSON response indicating success or failure.
  - If successful, the user's balance is updated and the bill is marked as paid.

##### `GET /view_fuel_bills`
- **Description**: Fetches the user’s fuel bills and their payment status.
- **Query Parameters**: None
- **Response**: Renders a page displaying the user’s fuel bills (total and payment status).

##### `GET /view_fuel_bill_detail/<month>/<year>`
- **Description**: Fetches detailed consumption data for a specific month and year for fuel.
- **Query Parameters**: 
  - `month`: The month of the bill.
  - `year`: The year of the bill.
- **Response**: Renders a page showing daily fuel consumption and bills for the selected month.

##### `POST /pay_fuel_bill`
- **Description**: Allows the user to pay for their fuel bill.
- **Request Body**: 
  - `month`: The month of the bill.
  - `year`: The year of the bill.
  - `password`: User’s wallet password.
- **Response**: 
  - Returns a JSON response indicating success or failure.
  - If successful, the user's balance is updated and the bill is marked as paid.

##### `GET /view_gas_bills`
- **Description**: Fetches the user’s gas bills and their payment status.
- **Query Parameters**: None
- **Response**: Renders a page displaying the user’s gas bills (total and payment status).

##### `GET /view_gas_bill_detail/<month>/<year>`
- **Description**: Fetches detailed consumption data for a specific month and year for gas.
- **Query Parameters**: 
  - `month`: The month of the bill.
  - `year`: The year of the bill.
- **Response**: Renders a page showing daily gas consumption and bills for the selected month.

##### `POST /pay_gas_bill`
- **Description**: Allows the user to pay for their gas bill.
- **Request Body**: 
  - `month`: The month of the bill.
  - `year`: The year of the bill.
  - `password`: User’s wallet password.
- **Response**: 
  - Returns a JSON response indicating success or failure.
  - If successful, the user's balance is updated and the bill is marked as paid.

#### 5. **Carbon Footprint Reporting**

##### `GET /detailed_carbon_reports`
- **Description**: Fetches detailed monthly carbon footprint reports for the user using `ROLLUP` or `CUBE` in SQL.
- **Query Parameters**: None
- **Response**: Renders a detailed carbon footprint report that includes emissions from electricity, fuel, gas, and water consumption.

---

Sure! I’ve reviewed all your provided DDL scripts carefully, and here's a **properly structured and complete "Database Structure" section** based on them:

---

## Database Structure

The following tables are used in the application:

- **`user`**  
  Stores user credentials, basic information (address, phone, division), linked utility providers (electricity, gas, water), and gas connection type.  
  ➔ Connected to multiple consumption and wallet-related tables.

- **`user_housing`**  
  Stores housing details for each user including:
  - House size (sqft)
  - Number of family members
  - Renewable energy capacities (solar panel, wind, others)

- **`utility_providers`**  
  Stores information about utility service providers:
  - Provider name, energy type (electricity/gas/water)
  - Billing information, emission factors, regional info

- **`vehicles`**  
  Predefined database of vehicle models with:
  - Fuel type (petrol, diesel, CNG, electric, etc.)
  - Efficiency (urban/highway km per liter)
  - Average daily driving distance
  
- **`user_vehicles`**  
  Stores user-specific vehicle ownership details:
  - Links users to selected vehicles
  - Custom daily driving distances
  - License plate information

- **`daily_electricity_consumption`**  
  Daily logging of electricity usage for users:
  - Units consumed
  - Bill calculated
  - Linked to user and utility provider

- **`daily_water_consumption`**  
  Daily logging of water usage for users:
  - Liters consumed
  - Daily water bill amount
  - Linked to user and utility provider

- **`daily_gas_consumption`**  
  Daily logging of gas consumption:
  - Amount used (cubic meters)
  - Billing details
  - Different logic depending on whether the gas connection is metered or non-metered

- **`daily_fuel_consumption`**  
  Logs fuel consumption from vehicles:
  - Fuel usage in liters
  - Fuel cost
  - Driving condition (urban or highway)

- **`daily_carbon_footprint`**  
  Logs calculated carbon footprint for each user based on:
  - Electricity
  - Fuel
  - Gas
  - Water usage
  - Generates a total emission score with an emission tag (e.g., Good, Moderate, High) and suggestions.

- **`safe_limits`**  
  Stores personalized safe consumption limits for:
  - Electricity
  - Gas
  - Fuel
  - Water
  - Total carbon emission limit
  
- **`admin`**  
  Stores administrator information like email, phone, and name to manage the system.

- **`user_wallet`**  
  Stores the user's wallet balance for possible future transactions/payments inside the app.

- **`user_wallet_auth`**  
  Stores authentication information for users specifically for wallet login:
  - Username
  - Phone number
  - Encrypted password hash

---


## Testing

1. **Unit Testing**: Use Flask's built-in testing capabilities for unit tests.
2. **API Testing**: Use Postman or cURL to test API endpoints.
3. **Frontend Testing**: Manually test the charts and visualizations to ensure they load and render correctly.

