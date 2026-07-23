DROP TABLE IF EXISTS student_sections;

CREATE TABLE student_sections (
    student_id INT,
    section_code CHAR(2),
    course_id INT,
    academic_year_id INT,
    section_semester INT,
    final_grade VARCHAR(2),
    is_passed BOOL,
    
    PRIMARY KEY(student_id, section_code,
            course_id, academic_year_id,
            section_semester),

    FOREIGN KEY(student_id) REFERENCES students(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    FOREIGN KEY(section_code, course_id,
            academic_year_id, section_semester)
        REFERENCES
            sections(code, course_id,
                academic_year_id, semester)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CHECK(final_grade IN ('A', 'AB', 'B', 'BC', 'C', 'D', 'E'))
);