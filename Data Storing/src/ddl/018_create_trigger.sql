DELIMITER //

DROP TRIGGER IF EXISTS calculate_is_passed_insert//

CREATE TRIGGER calculate_is_passed_insert
BEFORE INSERT ON student_sections
FOR EACH ROW
BEGIN
    IF NEW.final_grade IN ('A', 'AB', 'B', 'BC', 'C') THEN
        SET NEW.is_passed = TRUE;
    ELSEIF NEW.final_grade IN ('D', 'E') THEN
        SET NEW.is_passed = FALSE;
    ELSE
        SET NEW.is_passed = NULL;
    END IF;
END//

DROP TRIGGER IF EXISTS calculate_is_passed_update//

CREATE TRIGGER calculate_is_passed_update
BEFORE UPDATE ON student_sections
FOR EACH ROW
BEGIN
    IF NEW.final_grade IN ('A', 'AB', 'B', 'BC', 'C') THEN
        SET NEW.is_passed = TRUE;
    ELSEIF NEW.final_grade IN ('D', 'E') THEN
        SET NEW.is_passed = FALSE;
    ELSE
        SET NEW.is_passed = NULL;
    END IF;
END//

DROP TRIGGER IF EXISTS before_academic_years_insert//

CREATE TRIGGER before_academic_years_insert
BEFORE INSERT ON academic_years
FOR EACH ROW
BEGIN
    SET NEW.is_active = IF(
        CURDATE() >= STR_TO_DATE(CONCAT(NEW.start_year, '-08-01'), '%Y-%m-%d')
        AND CURDATE() < STR_TO_DATE(CONCAT(NEW.end_year, '-08-01'), '%Y-%m-%d'),
        1,
        0
    );
END//

DROP TRIGGER IF EXISTS before_academic_years_update//

CREATE TRIGGER before_academic_years_update
BEFORE UPDATE ON academic_years
FOR EACH ROW
BEGIN
    SET NEW.is_active = IF(
        CURDATE() >= STR_TO_DATE(CONCAT(NEW.start_year, '-08-01'), '%Y-%m-%d')
        AND CURDATE() < STR_TO_DATE(CONCAT(NEW.end_year, '-08-01'), '%Y-%m-%d'),
        1,
        0
    );
END//

DELIMITER ;