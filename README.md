

#  Smart Infrastructure Tracking

A role-based project management system built using **Flask** and **MySQL** that enables efficient monitoring, assignment, and progress tracking of infrastructure development projects.

## Features

-  **Role-Based Login System**
  - Admin and Contractor dashboards with role-specific actions.

-  **Project Assignment**
  - Admins can assign projects to specific contractors with custom notes and details.

- **Messaging System**
  - Notifications sent when a project is assigned.
  - Contractors can accept or reject projects, notifying the admin.

- **Task Scheduling**
  - Contractors can break down projects into daily tasks and update progress regularly.

- **Taskboard View**
  - Visual progress tracking of tasks and deadlines.

- **Progress Upload**
  - Contractors can upload daily updates and images to report real-time project progress.

-  **Settings Page**
  - View and update contractor/admin profiles and project info.

-  **Deadline Reminders & Alerts**
  - Stylish, dynamic alerts integrated with backend logic and deadlines.

---

##  Tech Stack

| Component        | Technology             |
|------------------|------------------------|
| Frontend         | HTML, CSS, Bootstrap   |
| Backend          | Python (Flask)         |
| Database         | MySQL                  |
| Authentication   | Flask-Login            |
| Media Handling   | File Upload (Images)   |
| Deployment       | Localhost or Web       |

---

## Folder Structure

```

Smart-Infrastructure-Tracking/
│
├── static/
│   └── css, js, uploads/
│
├── templates/
│   └── login.html, dashboard.html, assign\_project.html, etc.
│
├── app.py
├── config.py
├── database.sql
└── README.md

````

---

##  How to Run

1. **Clone the repository**
  
   git clone https://github.com/Mandadapu-Kinnera/Smart-Infrastructure-Tracking.git
   cd Smart-Infrastructure-Tracking


2. **Set up a virtual environment**

  
   python -m venv venv
   source venv/bin/activate  # For Linux/Mac
   venv\Scripts\activate     # For Windows
 

3. **Install dependencies**

 
   pip install -r requirements.txt
 

4. **Configure MySQL Database**

   * Import `database.sql` into your MySQL server
   * Update `config.py` with your database credentials

5. **Run the app**

  
   python app.py
  

6. **Open in browser**

   http://127.0.0.1:5000/
  



## 🙋‍♀️ Author

**Mandadapu Kinnera**
[GitHub](https://github.com/Mandadapu-Kinnera)

