DROP TABLE IF EXISTS section_instructors;

CREATE TABLE section_instructors (
    instructor_id INT,
    section_code CHAR(2),
    course_id INT,
    academic_year_id INT,
    section_semester INT,
    
    
    PRIMARY KEY(instructor_id, section_code,
            course_id, academic_year_id,
            section_semester),

    FOREIGN KEY(instructor_id) REFERENCES instructors(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY(section_code, course_id,
            academic_year_id, section_semester)
        REFERENCES
            sections(code, course_id,
                academic_year_id, semester)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);