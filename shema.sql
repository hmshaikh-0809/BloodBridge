CREATE DATABASE Hamza_BD;
USE Hamza_BD;
-- Camps
CREATE TABLE camps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_name VARCHAR(255) NOT NULL,
    address VARCHAR(255) NOT NULL,
    camp_name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
USE Hamza_BD;

-- Donor table
CREATE TABLE donors (
    donor_id INT AUTO_INCREMENT PRIMARY KEY,
    
    full_name        VARCHAR(100) NOT NULL,
    gender           ENUM('Male','Female','Other') NOT NULL,
    blood_group      ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') NOT NULL,
    
    weight_kg        DECIMAL(5,2) NOT NULL,
    age              INT NOT NULL,
    phone            VARCHAR(15) NOT NULL,
    address          TEXT NOT NULL,
    
    donated_before   ENUM('Yes','No') NOT NULL,
    last_donation_date DATE NULL,           -- NULL allowed if never donated
    
    any_disease      ENUM('Yes','No') NOT NULL,
    bleeding_disorder ENUM('Yes','No') NOT NULL,
    diabetic         ENUM('Yes','No') NOT NULL,
    
    email            VARCHAR(120) NOT NULL UNIQUE,
    password_hash    VARCHAR(255) NOT NULL,
    
    consent_given    TINYINT(1) NOT NULL DEFAULT 0,
    status           ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
    
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME NULL DEFAULT NULL
                     ON UPDATE CURRENT_TIMESTAMP,
    
    is_active        TINYINT(1) NOT NULL DEFAULT 1
);
-- Patient Table
CREATE TABLE patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,
    gender ENUM('Male','Female','Other') NOT NULL,

    blood_group ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') NOT NULL,

    weight INT NOT NULL,
    age INT NOT NULL,

    phone VARCHAR(15) NOT NULL,
    address TEXT NOT NULL,

    reason TEXT NOT NULL,
    hospital_name VARCHAR(255) NOT NULL,

    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,

    date_of_registration DATETIME DEFAULT CURRENT_TIMESTAMP,

    status ENUM('pending','approved') DEFAULT 'pending',

    consent_accepted TINYINT(1) DEFAULT 0
);

-- requests table
CREATE TABLE donation_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,

    donor_id INT NOT NULL,
    patient_id INT NOT NULL,

    request_date DATE NOT NULL DEFAULT (CURRENT_DATE),
    last_updated DATE NOT NULL DEFAULT (CURRENT_DATE),

    status ENUM(
        'Pending',     -- patient sent request to donor but donor did nothing niether rejected nor accepted
        'Accepted'     -- donor accepted the request
    ) NOT NULL DEFAULT 'Pending',

    CONSTRAINT fk_req_donor FOREIGN KEY (donor_id)
        REFERENCES donors(donor_id) ON DELETE CASCADE,

    CONSTRAINT fk_req_patient FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id) ON DELETE CASCADE,

    --One patient can send only one request to same donor at a time
    UNIQUE KEY unique_request (donor_id, patient_id)
);

-- Donation table
CREATE TABLE donations (
    donation_id INT AUTO_INCREMENT PRIMARY KEY,

    donor_id INT NOT NULL,
    patient_id INT NOT NULL,

    request_date DATE NOT NULL,            -- Date on which donor accepted request
    last_updated DATE NOT NULL,            -- Date on which status changed last time

    donor_confirmed ENUM('Yes','No') DEFAULT 'No',
    patient_confirmed ENUM('Yes','No') DEFAULT 'No',

    status ENUM(
        'Active',
        'Pending Donor Approval',
        'Pending Patient Approval',
        'Completed'
    ) DEFAULT 'Active',

    completion_date DATE NULL,             -- donation completion date

    reason VARCHAR(255) NOT NULL,          
    hospital_name VARCHAR(255) NOT NULL,   
    CONSTRAINT fk_donor FOREIGN KEY (donor_id)
        REFERENCES donors(donor_id) ON DELETE CASCADE,

    CONSTRAINT fk_patient FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id) ON DELETE CASCADE
);
-- admin table
CREATE TABLE admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,  -- store hashed password
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
