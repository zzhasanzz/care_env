DELIMITER //

CREATE TRIGGER before_insert_user_defaults
BEFORE INSERT ON user
FOR EACH ROW
BEGIN
    IF NEW.electricity_provider IS NULL THEN
        SET NEW.electricity_provider = 1; -- Default to DESCO for example
    END IF;
    IF NEW.gas_provider IS NULL THEN
        SET NEW.gas_provider = 2; -- Default to Titas Gas
    END IF;
    IF NEW.water_provider IS NULL THEN
        SET NEW.water_provider = 3; -- Default to DWASA
    END IF;
    IF NEW.gas_type IS NULL THEN
        SET NEW.gas_type = 'metered';
    END IF;
    IF NEW.car_ids IS NULL THEN
        SET NEW.car_ids = '';
    END IF;
END //

DELIMITER ;


 DELIMITER //

CREATE TRIGGER after_update_user_housing_update_limits
AFTER UPDATE ON user_housing
FOR EACH ROW
BEGIN
    IF OLD.num_members != NEW.num_members THEN
        CALL update_safe_limits_for_user(NEW.user_id);
    END IF;
END //

DELIMITER ;


DELIMITER //

CREATE TRIGGER before_insert_utility_provider_check
BEFORE INSERT ON utility_providers
FOR EACH ROW
BEGIN
    DECLARE duplicate_count INT;

    SELECT COUNT(*)
    INTO duplicate_count
    FROM utility_providers
    WHERE provider_name = NEW.provider_name
      AND region = NEW.region
      AND energy_type = NEW.energy_type;

    IF duplicate_count > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Duplicate utility provider detected!';
    END IF;
END //

DELIMITER ;
