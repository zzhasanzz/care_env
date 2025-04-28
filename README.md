
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

To set up the database schema:

1. **Open MySQL Workbench**.
2. **Execute the following SQL scripts**:
   - `ddl.sql` – This script will create the necessary tables.
   - `pl_sql.sql` – This script will set up the required PL/SQL procedures.
   - `triggers.sql` – This script will create any necessary triggers.

Executing these scripts will set up the schema for your project. Let me know if you need further assistance!


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

Overview of the relevant database tables:

1. **utility_providers**: Contains utility provider details (e.g., electricity, water, gas) such as name, energy type, unit price, and billing frequency.

2. **vehicles**: Stores vehicle details (model, type, fuel type, efficiency, daily average km).

3. **user**: Stores user information (name, email, address) and their associated utility providers for electricity, water, and gas.

4. **user_housing**: Contains user housing information such as house size, number of members, and renewable energy sources.

5. **daily_electricity_consumption**: Stores daily electricity consumption data for users (units consumed, daily bill).

6. **daily_water_consumption**: Stores daily water consumption data for users (liters consumed, daily bill).

7. **user_vehicles**: Links users with their vehicles, storing purchase details and custom daily km.

8. **daily_fuel_consumption**: Stores daily fuel consumption data for user vehicles (fuel used, fuel cost).

9. **daily_gas_consumption**: Stores daily gas consumption data for users (gas used, cost, household type).

10. **daily_carbon_footprint**: Calculates and stores the carbon footprint based on consumption (electricity, fuel, gas, water).

11. **safe_limits**: Stores safe consumption limits for users (electricity, gas, fuel, water, total).

12. **admin**: Stores admin details (email, display name, phone).

13. **user_wallet**: Stores user wallet information (balance).

14. **user_wallet_auth**: Stores wallet authentication details (username, phone, password).

15. **transactions**: Tracks user transactions (deposits, payments, refunds) with details like amount, transaction type, and provider.

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



##### `GET /detailed_carbon_reports`
- **Description**: Fetches detailed monthly carbon footprint reports for the user using `ROLLUP` or `CUBE` in SQL.
- **Query Parameters**: None
- **Response**: Renders a detailed carbon footprint report that includes emissions from electricity, fuel, gas, and water consumption.

---



## Testing

1. **Unit Testing**: Use Flask's built-in testing capabilities for unit tests.
2. **API Testing**: Use Postman or cURL to test API endpoints.
3. **Frontend Testing**: Manually test the charts and visualizations to ensure they load and render correctly.

