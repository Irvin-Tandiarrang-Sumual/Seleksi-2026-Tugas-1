DROP TABLE IF EXISTS section_teaching_assistants;

CREATE TABLE section_teaching_assistants (
    teaching_assistant_id INT,
    section_code CHAR(2),
    course_id INT,
    academic_year_id INT,
    section_semester INT,
    
    
    PRIMARY KEY(teaching_assistant_id, section_code,
            course_id, academic_year_id,
            section_semester),

    FOREIGN KEY(teaching_assistant_id) REFERENCES teaching_assistants(student_id)
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