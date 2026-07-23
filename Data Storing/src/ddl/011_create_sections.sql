DROP TABLE IF EXISTS sections;

CREATE TABLE sections (
    code CHAR(2) NOT NULL,
    course_id INT,
    academic_year_id INT,
    semester INT,
    
    PRIMARY KEY(code, course_id,
            academic_year_id, semester),

    FOREIGN KEY(course_id) REFERENCES courses(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    FOREIGN KEY(academic_year_id) REFERENCES academic_years(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CHECK(LENGTH(code) = 2),
    CHECK(semester IN (1, 2))
);