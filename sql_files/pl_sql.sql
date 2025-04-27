DROP PROCEDURE IF EXISTS InsertElectricityConsumption;

DELIMITER //

CREATE PROCEDURE InsertElectricityConsumption(
    IN p_user_id INT,
    IN p_utility_provider_id INT,
    IN p_consumption_date DATE,
    IN p_units_consumed FLOAT
)
BEGIN
    DECLARE base_rate FLOAT;
    DECLARE total FLOAT DEFAULT 0;
    DECLARE remaining FLOAT DEFAULT 0;
    DECLARE subtotal FLOAT;
    DECLARE vat FLOAT;
    DECLARE final_bill FLOAT;
    DECLARE service_charge FLOAT DEFAULT 10;
    DECLARE demand_charge FLOAT DEFAULT 30;
    DECLARE meter_rent FLOAT DEFAULT 10;
    DECLARE vat_rate FLOAT DEFAULT 0.05;
    DECLARE record_exists INT DEFAULT 0;

    -- multipliers
    DECLARE m1 FLOAT DEFAULT 1.00;
    DECLARE m2 FLOAT DEFAULT 1.35;
    DECLARE m3 FLOAT DEFAULT 1.41;
    DECLARE m4 FLOAT DEFAULT 1.48;
    DECLARE m5 FLOAT DEFAULT 2.63;

    -- Check if record already exists
    SELECT COUNT(*) INTO record_exists
    FROM daily_electricity_consumption
    WHERE user_id = p_user_id
      AND consumption_date = p_consumption_date;

    -- If already exists, then do nothing
    IF record_exists = 0 THEN

        -- Calculate electricity bill
        SELECT unit_price INTO base_rate
        FROM utility_providers
        WHERE id = p_utility_provider_id;

        SET remaining = p_units_consumed;

        -- Tiered calculation
        IF remaining > 0 THEN
            SET total = total + LEAST(remaining, 75) * (base_rate * m1);
            SET remaining = remaining - LEAST(remaining, 75);
        END IF;

        IF remaining > 0 THEN
            SET total = total + LEAST(remaining, 125) * (base_rate * m2);
            SET remaining = remaining - LEAST(remaining, 125);
        END IF;

        IF remaining > 0 THEN
            SET total = total + LEAST(remaining, 100) * (base_rate * m3);
            SET remaining = remaining - LEAST(remaining, 100);
        END IF;

        IF remaining > 0 THEN
            SET total = total + LEAST(remaining, 200) * (base_rate * m4);
            SET remaining = remaining - LEAST(remaining, 200);
        END IF;

        IF remaining > 0 THEN
            SET total = total + remaining * (base_rate * m5);
        END IF;

        SET subtotal = total + service_charge + demand_charge + meter_rent;
        SET vat = subtotal * vat_rate;
        SET final_bill = subtotal + vat;

        -- Insert if not already exists
        INSERT INTO daily_electricity_consumption (
            user_id,
            utility_provider_id,
            consumption_date,
            units_consumed,
            daily_bill
        )
        VALUES (
            p_user_id,
            p_utility_provider_id,
            p_consumption_date,
            p_units_consumed,
            final_bill
        );
    END IF;
END //

DELIMITER ;


DROP PROCEDURE IF EXISTS InsertFuelConsumption;

DELIMITER //

CREATE PROCEDURE InsertFuelConsumption(
    IN p_user_id INT,
    IN p_vehicle_id INT,
    IN p_user_vehicle_id INT,
    IN p_consumption_date DATE,
    IN p_fuel_used FLOAT,
    IN p_fuel_price FLOAT,
    IN p_driving_condition VARCHAR(20)
)
BEGIN
    DECLARE existing_record INT DEFAULT 0;
    DECLARE total_cost FLOAT;

    -- Check if already exists
    SELECT COUNT(*) INTO existing_record
    FROM daily_fuel_consumption
    WHERE user_id = p_user_id
      AND user_vehicle_id = p_user_vehicle_id
      AND consumption_date = p_consumption_date;

    -- Insert only if not existing
    IF existing_record = 0 THEN
        SET total_cost = p_fuel_used * p_fuel_price;

        INSERT INTO daily_fuel_consumption (
            user_id,
            vehicle_id,
            user_vehicle_id,
            consumption_date,
            fuel_used_liters,
            fuel_cost,
            driving_condition
        )
        VALUES (
            p_user_id,
            p_vehicle_id,
            p_user_vehicle_id,
            p_consumption_date,
            p_fuel_used,
            total_cost,
            p_driving_condition
        );
    END IF;
END //

DELIMITER ;



DROP PROCEDURE IF EXISTS InsertWaterConsumption;

DELIMITER //

CREATE PROCEDURE InsertWaterConsumption(
    IN p_user_id INT,
    IN p_utility_provider_id INT,
    IN p_consumption_date DATE,
    IN p_liters_consumed FLOAT
)
BEGIN
    DECLARE v_unit_price FLOAT DEFAULT 0;
    DECLARE v_daily_bill FLOAT DEFAULT 0;

    SELECT unit_price INTO v_unit_price
    FROM utility_providers
    WHERE id = p_utility_provider_id
    LIMIT 1;

    SET v_daily_bill = (p_liters_consumed / 1000) * v_unit_price;

    IF NOT EXISTS (
        SELECT 1
        FROM daily_water_consumption
        WHERE user_id = p_user_id AND consumption_date = p_consumption_date
    ) THEN
        INSERT INTO daily_water_consumption (
            user_id,
            utility_provider_id,
            consumption_date,
            liters_consumed,
            daily_bill
        )
        VALUES (
            p_user_id,
            p_utility_provider_id,
            p_consumption_date,
            p_liters_consumed,
            v_daily_bill
        );
    END IF;
END;
//

DELIMITER ;


