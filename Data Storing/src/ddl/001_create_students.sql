DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INT AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    student_number VARCHAR(12) UNIQUE NOT NULL,

    PRIMARY KEY (id),

    CHECK(LENGTH(student_number) BETWEEN 8 AND 12)
);