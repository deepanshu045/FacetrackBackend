-- Separate NGO data tables.
-- Run this once if the old NGO attendance table already exists.
-- This removes the previous NGO attendance table because its structure referenced the college Student/ClassSection tables.

DROP TABLE IF EXISTS ngo_attendance;
DROP TABLE IF EXISTS ngo_students;
DROP TABLE IF EXISTS ngo_classes;

CREATE TABLE ngo_classes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    department VARCHAR(100) NOT NULL,
    class_name VARCHAR(100) NOT NULL,
    section VARCHAR(50) NOT NULL,
    CONSTRAINT fk_ngo_class_admin
        FOREIGN KEY (admin_id) REFERENCES admins(id),
    CONSTRAINT uq_ngo_admin_class_section
        UNIQUE (admin_id, department, class_name, section)
);

CREATE TABLE ngo_students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    ngo_class_id INT NOT NULL,
    roll_no VARCHAR(30) NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NULL,
    phone_no VARCHAR(30) NULL,
    CONSTRAINT fk_ngo_student_admin
        FOREIGN KEY (admin_id) REFERENCES admins(id),
    CONSTRAINT fk_ngo_student_class
        FOREIGN KEY (ngo_class_id) REFERENCES ngo_classes(id),
    CONSTRAINT uq_ngo_admin_student_roll_no
        UNIQUE (admin_id, roll_no)
);

CREATE TABLE ngo_attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    student_id INT NOT NULL,
    ngo_class_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'Present',
    marked_by_admin_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    CONSTRAINT fk_ngo_attendance_admin
        FOREIGN KEY (admin_id) REFERENCES admins(id),
    CONSTRAINT fk_ngo_attendance_student
        FOREIGN KEY (student_id) REFERENCES ngo_students(id),
    CONSTRAINT fk_ngo_attendance_class
        FOREIGN KEY (ngo_class_id) REFERENCES ngo_classes(id),
    CONSTRAINT fk_ngo_attendance_marker
        FOREIGN KEY (marked_by_admin_id) REFERENCES admins(id),
    CONSTRAINT uq_ngo_attendance_student_class_date
        UNIQUE (admin_id, student_id, ngo_class_id, attendance_date)
);
