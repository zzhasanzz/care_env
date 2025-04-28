-- 1. Create Utility Providers Table
CREATE TABLE utility_providers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider_name VARCHAR(255) NOT NULL,
    energy_type ENUM('electricity', 'gas', 'water') NOT NULL,
    transaction_phone VARCHAR(20),
    unit_price FLOAT NOT NULL,
    emission_factor FLOAT,
    billing_frequency ENUM('monthly', 'yearly'),
    website VARCHAR(255),
    region VARCHAR(255),
    description TEXT
);

-- 2. Create Vehicles Table
CREATE TABLE vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    vehicle_type ENUM('car', 'motorcycle', 'truck', 'bus') NOT NULL,
    fuel_type ENUM('petrol', 'diesel', 'cng', 'octane', 'electric') NOT NULL,
    urban_efficiency FLOAT NOT NULL,
    highway_efficiency FLOAT NOT NULL,
    daily_average_km FLOAT NOT NULL,
    description TEXT
);

-- 3. Create User Table
CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    google_id VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(15),
    address TEXT,
    division VARCHAR(50),
    electricity_provider INT,
    water_provider INT,
    gas_provider INT,
    gas_type ENUM('metered', 'non-metered'),
    car_ids TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (electricity_provider) REFERENCES utility_providers(id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (water_provider) REFERENCES utility_providers(id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (gas_provider) REFERENCES utility_providers(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- 4. Create User Housing Table
CREATE TABLE user_housing (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    house_size_sqft INT NOT NULL,
    num_members INT NOT NULL,
    solar_panel_watt INT DEFAULT 0,
    wind_source_watt INT DEFAULT 0,
    other_renewable_source INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- 5. Create Daily Electricity Consumption Table
CREATE TABLE daily_electricity_consumption (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    utility_provider_id INT NOT NULL,
    consumption_date DATE NOT NULL,
    units_consumed FLOAT NOT NULL,
    daily_bill FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, consumption_date),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (utility_provider_id) REFERENCES utility_providers(id) ON DELETE CASCADE
);

-- 6. Create Daily Water Consumption Table
CREATE TABLE daily_water_consumption (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    utility_provider_id INT NOT NULL,
    consumption_date DATE NOT NULL,
    liters_consumed FLOAT NOT NULL,
    daily_bill FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, consumption_date),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (utility_provider_id) REFERENCES utility_providers(id) ON DELETE CASCADE
);

-- 7. Create User Vehicles Table
CREATE TABLE user_vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    vehicle_id INT NOT NULL,
    purchase_date DATE DEFAULT NULL,
    custom_daily_km FLOAT DEFAULT NULL,
    license_plate VARCHAR(50) DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

-- 8. Create Daily Fuel Consumption Table
CREATE TABLE daily_fuel_consumption (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    vehicle_id INT NOT NULL,
    user_vehicle_id INT NOT NULL,
    consumption_date DATE NOT NULL,
    fuel_used_liters FLOAT NOT NULL,
    fuel_cost FLOAT NOT NULL,
    driving_condition ENUM('urban', 'highway') DEFAULT 'urban',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    FOREIGN KEY (user_vehicle_id) REFERENCES user_vehicles(id)
);

-- 9. Create Daily Gas Consumption Table (Updated)
CREATE TABLE daily_gas_consumption (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    utility_provider_id INT NOT NULL,
    consumption_date DATE NOT NULL,
    gas_used_cubic_meters FLOAT NOT NULL,
    gas_cost FLOAT NOT NULL,
    household_type ENUM('metered', 'non_metered') NOT NULL,
    burner_type ENUM('single', 'double') NULL,
    num_members INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (utility_provider_id) REFERENCES utility_providers(id)
);

-- 10. Create Daily Carbon Footprint Table
CREATE TABLE daily_carbon_footprint (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    consumption_date DATE NOT NULL,
    electricity_emission_kg FLOAT DEFAULT 0,
    fuel_emission_kg FLOAT DEFAULT 0,
    gas_emission_kg FLOAT DEFAULT 0,
    water_emission_kg FLOAT DEFAULT 0,
    total_emission_kg FLOAT DEFAULT 0,
    emission_tag VARCHAR(20),
    suggestions TEXT,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- 11. Create Safe Limits Table
CREATE TABLE safe_limits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    electricity_safe_limit FLOAT NOT NULL,
    gas_safe_limit FLOAT NOT NULL,
    fuel_safe_limit FLOAT NOT NULL,
    water_safe_limit FLOAT NOT NULL,
    total_safe_limit FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- 12. Create Admin Table
CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. Create User Wallet Table
CREATE TABLE user_wallet (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    balance DECIMAL(10,2) DEFAULT 0.00,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- 14. Create User Wallet Authentication Table
CREATE TABLE user_wallet_auth (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- 15. Create Transaction Table
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    provider_id INT, -- New
    amount DECIMAL(10,2) NOT NULL,
    transaction_type ENUM('deposit', 'payment', 'refund') NOT NULL,
    utility_type ENUM('electricity', 'water', 'gas', 'fuel') NULL,
    reference_id VARCHAR(50) NULL,
    description TEXT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (provider_id) REFERENCES utility_providers(id)
);



--Inserts
INSERT INTO vehicles (model_name, vehicle_type, fuel_type, urban_efficiency, highway_efficiency, daily_average_km, description)
VALUES 
    -- Cars
    ('Toyota Corolla', 'car', 'petrol', 12.5, 16.0, 40, 'Popular compact car with decent mileage.'),
    ('Honda Civic', 'car', 'petrol', 11.0, 14.5, 50, 'Stylish sedan with sporty handling.'),
    ('Ford Ranger', 'car', 'diesel', 10.0, 13.0, 60, 'Pickup truck designed for tough terrains.'),
    ('Nissan Leaf', 'car', 'electric', 0.0, 0.0, 50, 'Electric car with zero emissions.'),

    -- Motorcycles
    ('Suzuki Gixxer', 'motorcycle', 'petrol', 40.0, 50.0, 20, 'Efficient two-wheeler with sporty looks.'),
    ('Honda Activa', 'motorcycle', 'petrol', 45.0, 55.0, 25, 'Popular scooter for urban commuting.'),

    -- Trucks
    ('Ashok Leyland Ecomet', 'truck', 'diesel', 5.0, 8.0, 120, 'Heavy-duty truck for goods transport.'),
    ('Tata 1212 LPT', 'truck', 'diesel', 4.5, 7.0, 150, 'Long-haul truck for industrial use.'),

    -- Buses
    ('Tata Marcopolo', 'bus', 'diesel', 3.0, 5.0, 100, 'Passenger transport bus for cities and highways.'),
    ('Ashok Leyland ULE', 'bus', 'diesel', 2.8, 4.5, 120, 'Ultra-low emission bus for public transport.');


INSERT INTO utility_providers (provider_name, energy_type, transaction_phone, unit_price, emission_factor, billing_frequency, website, region, description)
VALUES 
    -- Dhaka Division
    ('Dhaka Electric Supply Company (DESCO)', 'electricity', '01787654321', 8.00, 0.65, 'monthly', 'https://www.desco.org.bd', 'Dhaka', 'Electricity provider for urban areas in Dhaka.'),
    ('Titas Gas Transmission and Distribution Company', 'gas', '01912345678', 9.10, 2.75, 'monthly', 'https://www.titasgas.org.bd', 'Dhaka', 'Primary gas distributor in urban Bangladesh.'),
    ('Dhaka Water Supply and Sewerage Authority (DWASA)', 'water', '01612345678', 14.46, NULL, 'monthly', 'https://www.dwasa.org.bd', 'Dhaka', 'Water and sewerage service provider for Dhaka.'),

    -- Chattogram Division
    ('Bangladesh Power Development Board (BPDB)', 'electricity', '01776543210', 7.90, 0.66, 'monthly', 'https://www.bpdb.gov.bd', 'Chattogram', 'Electricity provider for Chattogram division.'),
    ('Karnaphuli Gas Distribution Company', 'gas', '01987654321', 9.20, 2.80, 'monthly', 'https://www.kgdcl.gov.bd', 'Chattogram', 'Gas distributor for Chattogram region.'),
    ('Chattogram Water Supply and Sewerage Authority (CWASA)', 'water', '01687654321', 13.50, NULL, 'monthly', 'https://www.cwasa.org.bd', 'Chattogram', 'Water and sewerage service provider for Chattogram.'),

    -- Khulna Division
    ('West Zone Power Distribution Company (WZPDCL)', 'electricity', '01876543210', 7.85, 0.70, 'monthly', 'https://www.wzpdcl.org.bd', 'Khulna', 'Electricity distributor in southwest Bangladesh.'),
    ('Khulna Water Supply and Sewerage Authority (KWASA)', 'water', '01512345678', 12.00, NULL, 'monthly', 'https://www.kwasa.org.bd', 'Khulna', 'Water service provider for Khulna region.'),
    ('Khulna Gas Distribution Limited', 'gas', '01955667788', 9.30, 2.78, 'monthly', 'https://www.khulnagascorp.com.bd', 'Khulna', 'Gas provider for Khulna region.'),

    -- Rajshahi Division
    ('Northern Electricity Supply Company (NESCO)', 'electricity', '01711223344', 7.90, 0.68, 'monthly', 'https://www.nesco.gov.bd', 'Rajshahi', 'Electricity provider for Rajshahi and Rangpur divisions.'),
    ('Rajshahi Gas Distribution Company', 'gas', '01966778899', 9.15, 2.75, 'monthly', 'https://www.rajshahigas.com.bd', 'Rajshahi', 'Gas provider for Rajshahi region.'),
    ('Rajshahi Water Supply and Sewerage Authority', 'water', '01699887766', 12.80, NULL, 'monthly', 'https://www.rajshahiwasa.gov.bd', 'Rajshahi', 'Water service provider for Rajshahi region.'),

    -- Barishal Division
    ('Barishal Electric Supply Company (BESCO)', 'electricity', '01722334455', 7.95, 0.69, 'monthly', 'https://www.besco.gov.bd', 'Barishal', 'Electricity provider for Barishal region.'),
    ('Barishal Gas Distribution Company', 'gas', '01811223344', 9.10, 2.80, 'monthly', 'https://www.barisalgas.com.bd', 'Barishal', 'Gas provider for Barishal region.'),
    ('Barishal Water Supply and Sewerage Authority', 'water', '01633445566', 12.50, NULL, 'monthly', 'https://www.barisalwasa.gov.bd', 'Barishal', 'Water service provider for Barishal region.'),

    -- Sylhet Division
    ('Bangladesh Power Development Board (BPDB)', 'electricity', '01755443322', 7.88, 0.65, 'monthly', 'https://www.bpdb.gov.bd', 'Sylhet', 'Electricity provider for Sylhet division.'),
    ('Sylhet Gas Fields Limited', 'gas', '01933445566', 9.15, 2.78, 'monthly', 'https://www.sgfl.org.bd', 'Sylhet', 'Gas provider for Sylhet region.'),
    ('Sylhet Water Supply Authority', 'water', '01644556677', 13.20, NULL, 'monthly', 'https://www.sylhetwasa.gov.bd', 'Sylhet', 'Water service provider for Sylhet region.'),

    -- Rangpur Division
    ('Northern Electricity Supply Company (NESCO)', 'electricity', '01711223344', 7.90, 0.68, 'monthly', 'https://www.nesco.gov.bd', 'Rangpur', 'Electricity provider for Rajshahi and Rangpur divisions.'),
    ('Rangpur Gas Distribution Company', 'gas', '01855667788', 9.05, 2.70, 'monthly', 'https://www.rangpurgas.com.bd', 'Rangpur', 'Gas provider for Rangpur region.'),
    ('Rangpur Water Supply Authority', 'water', '01622334455', 11.90, NULL, 'monthly', 'https://www.rangpurwasa.gov.bd', 'Rangpur', 'Water service provider for Rangpur region.'),

    -- Mymensingh Division
    ('Mymensingh Electric Supply Company (MESCO)', 'electricity', '01744556677', 7.88, 0.67, 'monthly', 'https://www.mesco.gov.bd', 'Mymensingh', 'Electricity provider for Mymensingh region.'),
    ('Mymensingh Gas Distribution Company', 'gas', '01833445566', 9.25, 2.77, 'monthly', 'https://www.mymensinghgas.com.bd', 'Mymensingh', 'Gas provider for Mymensingh region.'),
    ('Mymensingh Water Supply Authority', 'water', '01655667788', 13.00, NULL, 'monthly', 'https://www.mymensinghwasa.gov.bd', 'Mymensingh', 'Water service provider for Mymensingh region.'),

    -- Nationwide Providers
    ('Rural Electrification Board (REB)', 'electricity', '01500000000', 6.85, 0.60, 'monthly', 'https://www.reb.gov.bd', 'Nationwide', 'Provides electricity to rural areas across Bangladesh.'),
    ('Jalalabad Gas Transmission and Distribution System Limited', 'gas', '01700000000', 9.25, 2.80, 'monthly', 'https://www.jalalabadgas.org.bd', 'Nationwide', 'Gas distribution company serving multiple regions.'),
    ('Bangladesh Water Development Board (BWDB)', 'water', '01600000000', 10.00, NULL, 'monthly', 'https://www.bwdb.gov.bd', 'Nationwide', 'Manages water resources and supply across the country.'),

    -- Non-Governmental Providers
    ('Summit Power Limited', 'electricity', '01800000000', 8.50, 0.65, 'monthly', 'https://www.summitpower.org', 'Various', 'Private sector power generation company operating in multiple regions.'),
    ('United Power Generation & Distribution Company Ltd.', 'electricity', '01900000000', 8.75, 0.68, 'monthly', 'https://www.unitedpowerbd.com', 'Various', 'Private power generation and distribution company.'),
    ('Meghna Group of Industries', 'gas', '01711111111', 9.50, 2.85, 'monthly', 'https://www.meghnagroup.biz', 'Various', 'Private company supplying gas to industrial clients.'),
    ('BRAC WASH Program', 'water', '01611111111', 12.00, NULL, 'monthly', 'https://www.brac.net/wash', 'Various', 'Non-governmental organization providing water and sanitation services.');
