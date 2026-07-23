DROP TABLE IF EXISTS student_emails;

CREATE TABLE student_emails (
    student_id INT,
    email VARCHAR(255) UNIQUE NOT NULL,

    PRIMARY KEY(student_id, email),

    FOREIGN KEY(student_id) REFERENCES students(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);