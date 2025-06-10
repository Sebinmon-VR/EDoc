import sqlite3
import os
from datetime import datetime, timedelta
import random

def create_sample_database():
    """Create a sample attendance database for testing KOREV AI."""
    database_path = os.getenv('DATABASE_PATH', 'attendance.db')
    
    # Remove existing database if it exists
    if os.path.exists(database_path):
        os.remove(database_path)
    
    # Create new database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Create employees table
    cursor.execute('''
    CREATE TABLE employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        position TEXT NOT NULL,
        hire_date DATE NOT NULL,
        email TEXT UNIQUE NOT NULL
    )
    ''')
    
    # Create attendance table
    cursor.execute('''
    CREATE TABLE attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        date DATE NOT NULL,
        check_in TIME,
        check_out TIME,
        hours_worked REAL DEFAULT 0,
        status TEXT NOT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )
    ''')
    
    # Create departments table
    cursor.execute('''
    CREATE TABLE departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        manager TEXT,
        location TEXT
    )
    ''')
    
    # Sample departments
    departments = [
        ('Information Technology', 'Ahmed Al-Rashid', 'Building A - Floor 3'),
        ('Human Resources', 'Fatima Al-Zahra', 'Building B - Floor 1'),
        ('Finance', 'Mohammed Al-Mansouri', 'Building A - Floor 2'),
        ('Marketing', 'Sarah Al-Khalil', 'Building C - Floor 1'),
        ('Operations', 'Omar Al-Thani', 'Building A - Floor 1')
    ]
    
    cursor.executemany('INSERT INTO departments (name, manager, location) VALUES (?, ?, ?)', departments)
    
    # Sample employees
    employees = [
        ('Ahmed Ali Hassan', 'Information Technology', 'Software Developer', '2023-01-15', 'ahmed.hassan@korev.com'),
        ('Fatima Mohammed Al-Zahra', 'Human Resources', 'HR Manager', '2022-03-10', 'fatima.zahra@korev.com'),
        ('Mohammed Omar Al-Rashid', 'Finance', 'Financial Analyst', '2023-02-20', 'mohammed.rashid@korev.com'),
        ('Sarah Abdullah Al-Khalil', 'Marketing', 'Marketing Specialist', '2022-11-05', 'sarah.khalil@korev.com'),
        ('Omar Hassan Al-Thani', 'Operations', 'Operations Manager', '2022-01-12', 'omar.thani@korev.com'),
        ('Aisha Ahmed Al-Mansouri', 'Information Technology', 'System Administrator', '2023-03-08', 'aisha.mansouri@korev.com'),
        ('Khalid Mohammed Al-Sabah', 'Finance', 'Accountant', '2022-09-15', 'khalid.sabah@korev.com'),
        ('Nour Ali Al-Hashimi', 'Marketing', 'Content Creator', '2023-04-12', 'nour.hashimi@korev.com'),
        ('Hassan Omar Al-Maktoum', 'Operations', 'Logistics Coordinator', '2022-07-20', 'hassan.maktoum@korev.com'),
        ('Layla Ahmed Al-Qasimi', 'Human Resources', 'HR Assistant', '2023-05-01', 'layla.qasimi@korev.com')
    ]
    
    cursor.executemany('INSERT INTO employees (name, department, position, hire_date, email) VALUES (?, ?, ?, ?, ?)', employees)
    
    # Generate sample attendance data for the last 30 days
    start_date = datetime.now() - timedelta(days=30)
    
    for day in range(30):
        current_date = start_date + timedelta(days=day)
        
        # Skip weekends (Friday and Saturday in Middle East)
        if current_date.weekday() in [4, 5]:  # Friday = 4, Saturday = 5
            continue
            
        for emp_id in range(1, 11):  # 10 employees
            # 85% attendance rate
            if random.random() < 0.85:
                # Normal working hours: 8:00 AM to 5:00 PM
                check_in_hour = random.randint(7, 9)  # Between 7-9 AM
                check_in_minute = random.randint(0, 59)
                check_in = f"{check_in_hour:02d}:{check_in_minute:02d}"
                
                # Work 7-9 hours
                work_hours = random.uniform(7.0, 9.0)
                check_out_time = datetime.strptime(check_in, "%H:%M") + timedelta(hours=work_hours)
                check_out = check_out_time.strftime("%H:%M")
                
                status = "Present"
                
                cursor.execute('''
                INSERT INTO attendance (employee_id, date, check_in, check_out, hours_worked, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (emp_id, current_date.date(), check_in, check_out, round(work_hours, 2), status))
            else:
                # Absent
                cursor.execute('''
                INSERT INTO attendance (employee_id, date, check_in, check_out, hours_worked, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (emp_id, current_date.date(), None, None, 0, "Absent"))
    
    conn.commit()
    conn.close()
    
    print(f"Sample database created successfully at: {database_path}")
    return database_path

if __name__ == "__main__":
    create_sample_database()
