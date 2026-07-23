DROP TABLE IF EXISTS courses;

CREATE TABLE courses (
    id INT AUTO_INCREMENT,
    subject_id INT,
    title VARCHAR(255) NOT NULL,
    code CHAR(6) NOT NULL,
    credits INT NOT NULL,

    PRIMARY KEY (id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CHECK(LENGTH(code) = 6),
    CHECK(credits >= 1 AND credits <= 4)
);