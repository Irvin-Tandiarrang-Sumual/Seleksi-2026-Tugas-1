DROP TABLE IF EXISTS student_assignments;

CREATE TABLE student_assignments (
    assignment_id INT,
    student_id INT,
    grade INT,
    
    PRIMARY KEY(assignment_id, student_id),

    FOREIGN KEY(assignment_id) REFERENCES assignments(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY(student_id) REFERENCES students(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);