# Blood Bank Management System 🩸

## 📌 Project Overview

The **Blood Bank Management System** is a web-based application developed using Python, HTML, CSS, and MySQL (if configured). It helps manage blood donors, blood requests, donor information, and blood bank activities through a user-friendly interface.

The main objective of this project is to simplify blood donation management and help users find suitable donors during emergency situations.

## 🎯 Objectives

- Maintain donor information efficiently.
- Manage blood requests and donor details.
- Help users identify suitable donors.
- Provide a dashboard for managing blood bank activities.
- Support communication and feedback between users and administrators.

## ✨ Features

- User Registration and Login
- Donor Management
- Blood Request Management
- Emergency Blood Request Interface
- Matched Donor Information
- User Profile Management
- Admin Dashboard
- Feedback Management
- Health Dashboard
- Report and Supporting Image Uploads

*Note: Features depend on the functionality implemented in the application.*

## 🛠️ Technologies Used

- **Backend:** Python
- **Web Framework:** Flask (if used by the application)
- **Frontend:** HTML, CSS, JavaScript, Bootstrap (if included)
- **Database:** MySQL (if configured)
- **Data Handling:** Pandas, as required by the application
- **Development Tool:** Visual Studio Code
- **Version Control:** Git and GitHub

## 📂 Project Structure

```text
blood-bank-management-system/
│
├── app.py
├── dataset.xlsx
├── requirements.txt
├── Procfile
│
├── static/
│   ├── images/
│   └── uploads/
│
└── templates/
    ├── about.html
    ├── admin_dashboard.html
    ├── admin_feedback.html
    ├── admin_home.html
    ├── admin_login.html
    ├── base.html
    ├── blood_requests.html
    ├── dashboard.html
    ├── donors.html
    ├── emergency.html
    ├── feedback.html
    ├── home.html
    ├── login.html
    ├── matched_donors.html
    ├── profile.html
    ├── request.html
    └── signup.html
```

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Nagu2730/blood-bank-management-system.git
```

### 2. Navigate to the Project Folder

```bash
cd blood-bank-management-system
```

### 3. Create a Virtual Environment

```bash
python -m venv .venv
```

### 4. Activate the Virtual Environment

For Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 5. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 6. Configure the Database

If the application uses MySQL, create the required database and configure the database connection settings according to the code in `app.py`.

Do not publish database passwords or other secret credentials.

### 7. Run the Application

```bash
python app.py
```

Open the local URL shown in the terminal. For a typical Flask development server, this may be:

`http://127.0.0.1:5000`

## 🔐 Security Considerations

- Store passwords securely using an appropriate password-hashing method.
- Keep database credentials and API keys private.
- Do not upload real donor records, medical reports, or other sensitive personal information to a public repository.
- Validate user inputs and uploaded files.
- Use HTTPS and appropriate access controls when deploying the application.

## 🚀 Future Enhancements

- Blood availability tracking
- Location-based donor search
- SMS or email notifications
- Improved emergency donor matching
- Enhanced reporting and analytics
- Secure cloud deployment
- Mobile-friendly user interface

## 🎓 Project Purpose

This project is developed for educational purposes to demonstrate web application development and blood bank management workflows.

## 👨‍💻 Developer

**Naga Chaitanya Ganta**

GitHub: [Nagu2730](https://github.com/Nagu2730)

## 📄 License

A license has not yet been specified. Add a suitable license before permitting reuse or redistribution of this project.
