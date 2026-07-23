DROP TABLE IF EXISTS section_materials;

CREATE TABLE section_materials (
    material_id INT,
    section_code CHAR(2),
    course_id INT,
    academic_year_id INT,
    section_semester INT,
    
    
    PRIMARY KEY(material_id, section_code,
            course_id, academic_year_id,
            section_semester),

    FOREIGN KEY(material_id) REFERENCES materials(id)
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