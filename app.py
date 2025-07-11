from flask import Flask, jsonify, render_template, request, redirect, session, url_for
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'mysql',
    'database': 'flaskdb'
}

def init_db():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS flaskdb")
        conn.database = db_config['database']

        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            role ENUM('Admin', 'Contractor') NOT NULL
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            notes TEXT NOT NULL,
            details TEXT NOT NULL,
            contractor_id INT NOT NULL,
            status ENUM('Pending', 'Accepted', 'Rejected') DEFAULT 'Pending',
            FOREIGN KEY (contractor_id) REFERENCES users(id) ON DELETE CASCADE
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            contractor_id INT NOT NULL,
            project_id INT NOT NULL,
            message TEXT NOT NULL,
            status ENUM('Unread', 'Accepted', 'Rejected') DEFAULT 'Unread',
            FOREIGN KEY (contractor_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS scheduled_dates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            contractor_id INT NOT NULL,
            scheduled_date DATE NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (contractor_id) REFERENCES users(id) ON DELETE CASCADE
        )''')

        conn.commit()
    except Error as e:
        print(f"Error while initializing database: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

init_db()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']  

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO users (username, email, password, role)
                               VALUES (%s, %s, %s, %s)''', (username, email, password, role))
            conn.commit()
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            return "Username already exists!"
        finally:
            cursor.close()
            conn.close()

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                print(f"User {username} logged in successfully.")  # Debugging
                return redirect(url_for('admin_dashboard' if user['role'] == 'Admin' else 'contractor_dashboard'))
            else:
                return "Invalid credentials!"
        except Error as e:
            print(f"Error during login: {e}")
            return "An error occurred while trying to log in."
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return render_template('login.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', username=session['username'])

@app.route('/contractor_dashboard')
def contractor_dashboard():
    if 'role' not in session or session['role'] != 'Contractor':
        return redirect(url_for('login'))
    return render_template('contractor_dashboard.html', username=session['username'])


@app.route('/assign_project', methods=['GET', 'POST'])
def assign_project():
    if 'role' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, username FROM users WHERE role = "Contractor"')
        contractors = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if request.method == 'POST':
        title = request.form['title']
        notes = request.form['notes']
        details = request.form['details']
        contractor_id = request.form['contractor_id']

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            cursor.execute('INSERT INTO projects (title, notes, details, contractor_id) VALUES (%s, %s, %s, %s)', 
                           (title, notes, details, contractor_id))
            project_id = cursor.lastrowid

            message_text = f"New Project Assigned: {title}"
            cursor.execute('INSERT INTO messages (contractor_id, project_id, message, status) VALUES (%s, %s, %s, %s)', 
                           (contractor_id, project_id, message_text, 'Unread'))
            conn.commit()
            print(f"Project assigned: {title}, Message inserted: {message_text}")  
        except Error as e:
            print(f"Error in assign_project: {e}")  
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin_dashboard'))

    return render_template('assign_project.html', contractors=contractors)


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/status/<int:project_id>', methods=['GET', 'POST'])
def status(project_id):
    if 'username' not in session or session['role'] != 'Contractor':
        return redirect(url_for('login'))

    contractor_id = session['user_id']

    if request.method == 'POST':
        day = request.form['day']
        progress = request.form['progress']
        file = request.files['image']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_url = url_for('static', filename=f'uploads/{filename}')
        else:
            image_url = None

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO daily_progress (project_id, contractor_id, day, progress, image_path)
                VALUES (%s, %s, %s, %s, %s)
            ''', (project_id, contractor_id, day, progress, image_url))
            conn.commit()
        except Error as e:
            print(f"Error in status: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

        return redirect(url_for('status', project_id=project_id))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT * FROM daily_progress
            WHERE project_id = %s AND contractor_id = %s
            ORDER BY day ASC
        ''', (project_id, contractor_id))
        progress_entries = cursor.fetchall()
    except Error as e:
        print(f"Error in status: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('status.html', project_id=project_id, progress_entries=progress_entries)


@app.route('/admin_notifications')
def admin_notifications():
    if 'role' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT sd.id, sd.scheduled_date, p.title, u.username AS contractor_name, sd.contractor_id
            FROM scheduled_dates sd
            JOIN projects p ON sd.project_id = p.id
            JOIN users u ON sd.contractor_id = u.id
        ''')
        notifications = cursor.fetchall()
    except Error as e:
        print(f"Error in admin_notifications: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('project_notifications.html', notifications=notifications)


@app.route('/project_progress')
def project_progress():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT p.id, p.title, p.notes, p.details, p.status, 
                   u.username AS contractor_name, u.email AS contractor_email
            FROM projects p
            JOIN users u ON p.contractor_id = u.id
        ''')
        projects = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template('project_progress.html', projects=projects)

@app.route('/contractor/view_projects')
def view_projects():
    if 'username' not in session or session['role'] != 'Contractor':
        return redirect(url_for('login'))

    contractor_id = session['user_id']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT p.id, p.title, p.notes, p.details, p.status, 
                   u.username AS admin_name, u.email AS admin_email
            FROM projects p
            JOIN users u ON p.contractor_id = u.id
            WHERE p.contractor_id = %s
        ''', (contractor_id,))
        projects = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template('view_projects.html', projects=projects)

@app.route('/schedule')
def view_schedule():
    if 'username' not in session or session['role'] != 'Contractor':
        return redirect(url_for('login'))

    contractor_id = session['user_id']
    projects = []  

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = '''
            SELECT p.id, p.title, p.details, p.status, 
                   p.assigned_at AS assigned_date, p.due_date
            FROM projects p
            WHERE p.contractor_id = %s AND p.status = 'Accepted'
        '''
        print(f"Executing query: {query} with contractor_id: {contractor_id}")

        cursor.execute(query, (contractor_id,))
        projects = cursor.fetchall()

        print(f"Fetched projects: {projects}")

    except Error as e:
        print(f"Error in view_schedule: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('view_schedule.html', projects=projects)


@app.route('/schedule_completion/<int:project_id>', methods=['POST'])
def schedule_completion(project_id):
    if 'role' not in session or session['role'] != 'Contractor':
        return redirect(url_for('login'))

    completion_date = request.form['completion_date']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE projects 
            SET due_date = %s 
            WHERE id = %s AND contractor_id = %s
        ''', (completion_date, project_id, session['user_id']))

        cursor.execute('''
            INSERT INTO scheduled_dates (project_id, contractor_id, scheduled_date)
            VALUES (%s, %s, %s)
        ''', (project_id, session['user_id'], completion_date))

        conn.commit()
        print(f"Project {project_id} due date updated to {completion_date}")
    except Error as e:
        print(f"Error in schedule_completion: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return redirect(url_for('view_schedule'))

@app.route('/taskboard')
def taskboard():
    if 'username' not in session or session['role'] != 'Contractor':
        return redirect(url_for('login'))

    contractor_id = session['user_id']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT username, email FROM users WHERE id = %s', (contractor_id,))
        contractor = cursor.fetchone()

        cursor.execute('''
            SELECT p.id, p.title, p.status, p.due_date, p.progress
            FROM projects p
            WHERE p.contractor_id = %s AND p.status = 'Accepted'
        ''', (contractor_id,))
        projects = cursor.fetchall()

    except Error as e:
        print(f"Error in taskboard: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('taskboard.html', contractor=contractor, projects=projects if projects else [])


@app.route('/taskboard/<int:contractor_id>', endpoint='taskboard_for_contractor')
def taskboard_for_contractor(contractor_id):
    if 'username' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT username, email FROM users WHERE id = %s', (contractor_id,))
        contractor = cursor.fetchone()

        cursor.execute('''
            SELECT p.id, p.title, p.status, p.due_date, p.progress
            FROM projects p
            WHERE p.contractor_id = %s AND p.status = 'Accepted'
        ''', (contractor_id,))
        projects = cursor.fetchall()

    except Error as e:
        print(f"Error in taskboard_for_contractor: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('taskboard.html', contractor=contractor, projects=projects, is_admin=True)


@app.route('/alerts')
def alerts():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    contractor_id = request.args.get('contractor_id')
    return render_template('alerts.html', contractor_id=contractor_id)


@app.route('/api/deadline')
def get_deadline():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    role = session['role']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        if role == 'Admin':
            contractor_id = request.args.get('contractor_id')
            if not contractor_id:
                return jsonify({'message': 'No contractor selected'}), 200

            
            cursor.execute('''
                SELECT p.due_date AS deadline
                FROM projects p
                WHERE p.contractor_id = %s AND p.status = 'Accepted'
                ORDER BY p.due_date ASC
                LIMIT 1
            ''', (contractor_id,))
        else:
            cursor.execute('''
                SELECT p.due_date AS deadline
                FROM projects p
                WHERE p.contractor_id = %s AND p.status = 'Accepted'
                ORDER BY p.due_date ASC
                LIMIT 1
            ''', (user_id,))

        deadline = cursor.fetchone()

        if deadline:
            return jsonify(deadline)
        else:
            return jsonify({'message': 'No deadline found'}), 200

    except Error as e:
        print(f"Error in get_deadline: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/view_messages')
def view_messages():
    if 'role' not in session or session['role'] != 'Contractor':
        return redirect(url_for('login'))

    contractor_id = session['user_id']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT m.id, m.message, p.title, p.details, p.id AS project_id
            FROM messages m
            JOIN projects p ON m.project_id = p.id
            WHERE m.contractor_id = %s AND (m.status = 'Unread' OR m.status IS NULL)
        ''', (contractor_id,))
        messages = cursor.fetchall()
        print(f"Messages fetched: {messages}")  
    except Error as e:
        print(f"Error in view_messages: {e}")  
    finally:
        cursor.close()
        conn.close()

    return render_template('view_messages.html', messages=messages)


@app.route('/accept_project', methods=['POST'])
def accept_project():
    if 'role' not in session or session['role'] != 'Contractor':
        return redirect(url_for('login'))

    contractor_id = session['user_id']
    project_id = request.form['project_id']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute('UPDATE projects SET status = "Accepted" WHERE id = %s AND contractor_id = %s',
                       (project_id, contractor_id))

        cursor.execute('UPDATE messages SET status = "Accepted" WHERE project_id = %s AND contractor_id = %s',
                       (project_id, contractor_id))

        conn.commit()
        print(f"Project {project_id} accepted by contractor {contractor_id}")  
    except Error as e:
        print(f"Error in accept_project: {e}")  
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('view_messages'))


@app.route('/reject_project', methods=['POST'])
def reject_project():
    if 'role' not in session or session['role'] != 'Contractor':
        return redirect(url_for('login'))

    contractor_id = session['user_id']
    project_id = request.form['project_id']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute('UPDATE projects SET status = "Rejected" WHERE id = %s AND contractor_id = %s',
                       (project_id, contractor_id))

        cursor.execute('UPDATE messages SET status = "Rejected" WHERE project_id = %s AND contractor_id = %s',
                       (project_id, contractor_id))

        conn.commit()
        print(f"Project {project_id} rejected by contractor {contractor_id}")  
    except Error as e:
        print(f"Error in reject_project: {e}")  
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('view_messages'))

@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    if 'role' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM projects WHERE id = %s', (project_id,))
        cursor.execute('DELETE FROM messages WHERE project_id = %s', (project_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('project_progress'))



@app.route('/settings/<int:project_id>')
def settings(project_id):
    if 'username' not in session:
        print("User not logged in. Redirecting to login.")  # Debugging
        return redirect(url_for('login'))
    print(f"User {session['username']} accessing settings for project {project_id}")  # Debugging
  

    contractor_id = session['user_id']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT username, email FROM users WHERE id = %s', (contractor_id,))
        contractor = cursor.fetchone()


        cursor.execute('SELECT username, email FROM users WHERE role = "Admin" LIMIT 1')
        admin = cursor.fetchone()

        cursor.execute('''
            SELECT p.id, p.title, p.details, p.status, p.due_date, p.progress
            FROM projects p
            WHERE p.id = %s AND p.contractor_id = %s
        ''', (project_id, contractor_id))
        project = cursor.fetchone()

        if not project:
            return "You are admin and don't  have access to see the settings of this project.", 404

    except Error as e:
        print(f"Error in settings: {e}")
        return "An error occurred while fetching project details.", 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('settings.html', contractor=contractor, admin=admin, project=project)


@app.route('/update_progress/<int:project_id>', methods=['POST'])
def update_progress(project_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    progress = request.form['progress']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('UPDATE projects SET progress = %s WHERE id = %s', (progress, project_id))
        conn.commit()
    except Error as e:
        print(f"Error in update_progress: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return redirect(url_for('settings', project_id=project_id))



@app.route('/reports/<int:project_id>')
def reports(project_id):
    if 'username' not in session:
        print("User not logged in. Redirecting to login.")  
        return redirect(url_for('login'))
    print(f"User {session['username']} accessing reports for project {project_id}")  
    

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            SELECT day, progress
            FROM daily_progress
            WHERE project_id = %s
            ORDER BY day ASC
        ''', (project_id,))
        progress_data = cursor.fetchall()

        for entry in progress_data:
            try:
                entry['progress'] = int(entry['progress'])
            except (ValueError, TypeError):
                entry['progress'] = 0  

        cursor.execute('''
            SELECT p.title, p.status, p.due_date
            FROM projects p
            WHERE p.id = %s
        ''', (project_id,))
        project = cursor.fetchone()

    except Error as e:
        print(f"Error in reports: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('reports.html', project=project, progress_data=progress_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    app.run(debug=True)

