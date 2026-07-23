DROP TABLE IF EXISTS teaching_assistants;

CREATE TABLE teaching_assistants (
    student_id INT,

    PRIMARY KEY(student_id),

    FOREIGN KEY(student_id) REFERENCES students(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);