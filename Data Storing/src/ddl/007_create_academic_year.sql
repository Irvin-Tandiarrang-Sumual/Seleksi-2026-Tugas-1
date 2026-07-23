DROP TABLE IF EXISTS academic_years;

CREATE TABLE academic_years (
    id INT AUTO_INCREMENT,
    start_year INT NOT NULL,
    end_year INT NOT NULL,
    is_active BOOL DEFAULT FALSE,

    PRIMARY KEY(id),

    CHECK(start_year < end_year)
);