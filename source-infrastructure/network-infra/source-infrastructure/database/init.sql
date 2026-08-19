CREATE TABLE IF NOT EXISTS students (id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL, department VARCHAR(100) NOT NULL);
INSERT INTO students (name, department) VALUES ('Demo Student', 'Computer Science'), ('Test Student', 'Cyber Security');
