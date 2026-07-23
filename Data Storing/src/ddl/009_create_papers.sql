DROP TABLE IF EXISTS papers;

CREATE TABLE papers (
    assignment_id INT,
    student_id INT,
    title VARCHAR(255) NOT NULL,
    abstract TEXT,
    url VARCHAR(500) UNIQUE NOT NULL,
    language VARCHAR(16) NOT NULL,
    
    PRIMARY KEY(assignment_id, student_id, title),

    FOREIGN KEY(assignment_id) REFERENCES assignments(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY(student_id) REFERENCES students(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);