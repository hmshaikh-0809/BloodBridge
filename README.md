# BloodBridge – Blood Donation Management System

## Project Overview

BloodBridge is a web-based Blood Donation Management System designed to connect blood donors and patients efficiently. The system provides a centralized platform where donors can register, patients can request blood, and administrators can manage the entire workflow.

The main objective of this project is to simplify and digitalize the process of blood donation, reduce delays during emergencies, and maintain accurate records of donors, patients, and blood donation activities.

---

## Key Features

### Donor Module
- Donor registration and login system
- Profile management (view, edit, delete account)
- View blood donation requests
- Accept or reject patient requests
- Track active and completed donations

### Patient Module
- Patient registration and login system
- Profile management
- Find matching donors based on blood group
- Send and cancel donation requests
- Track active requests and donation history

### Admin Module
- Admin dashboard with statistics
- Approve or reject donor and patient registrations
- Manage blood donation camps
- Monitor active and completed donations
- View detailed records of donors and patients

### BloodBot AI Assistant
- AI chatbot integrated using Ollama local LLM
- Answers queries related to blood donation and health
- Provides real-time responses with streaming support

---

## Technologies Used

### Programming Language
- Python

### Framework
- Flask (Web Framework)

### Frontend Technologies
- HTML
- CSS
- JavaScript
- Jinja2 Templates

### Database
- MySQL

### AI Integration
- Ollama Local LLM (Phi3 Mini Model)

### Development Tools
- Visual Studio Code
- Git & GitHub

---

## Hardware and Software Requirements

### Hardware Requirements
- Minimum 4 GB RAM
- Intel i3 or higher processor
- 10 GB free disk space

### Software Requirements
- Python 3.10 or above
- MySQL Server
- Ollama installed locally
- Web browser (Chrome recommended)
- Visual Studio Code (optional)

---

## Installation and Setup Guide

### Step 1: Clone the Repository

Open terminal and run:

git clone https://github.com/hmshaikh-0809/BloodBridge.git

cd BloodBridge

---

### Step 2: Create Virtual Environment

python -m venv venv

Activate environment:

Windows:
venv\Scripts\activate

---

### Step 3: Install Required Packages

pip install -r requirements.txt

---

### Step 4: Setup MySQL Database

1. Install MySQL Server.
2. Create a new database:

CREATE DATABASE Hamza_BD;

3. Import the schema file:

Use the provided `schema.sql` file to create tables.

4. Update database credentials in `main.py`:

host = "localhost"  
user = "your_mysql_username"  
password = "your_mysql_password"  
database = "Hamza_BD"  

---

### Step 5: Install and Setup Ollama

Download and install Ollama from:

https://ollama.com

Pull the required model:

ollama pull phi3:mini

Start Ollama service:

ollama serve

---

### Step 6: Run the Application

Start the Flask server:

python main.py

Open browser and visit:

http://127.0.0.1:5000

---

## Project Structure

BloodBridge/
│
├── main.py
├── requirements.txt
├── schema.sql
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│
└── README.md

---

## Future Scope

- Integration with real hospital databases
- Real-time emergency blood alerts
- SMS and email notification system
- Mobile application development
- Cloud deployment for large-scale usage
- Advanced AI health assistant features

---

## Conclusion

BloodBridge provides a comprehensive solution for managing blood donation activities efficiently. The system reduces manual effort, improves response time during emergencies, and ensures secure management of donor and patient data. The integration of an AI chatbot further enhances user interaction by providing instant guidance related to blood donation and health awareness.

---

## Author

Developed by:

Hamza Shaikh  
Bachelor of Computer Science (BCA)

---

## License

This project is for academic and educational purposes only.
