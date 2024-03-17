import json
import psycopg2
import hashlib
import os 


# Update the connection parameters
DATABASE_NAME = 'postgres'
DATABASE_USER = 'myuser'
DATABASE_PASSWORD = 'mypassword'
DATABASE_HOST = 'localhost'
DATABASE_PORT = '5432'

# Establish a database connection
def get_db_connection():
    conn = psycopg2.connect(
        database=DATABASE_NAME,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
        host=DATABASE_HOST
    )
    return conn

def show_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users LIMIT(10);')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users



users = show_all_users()

json_data = [
    {'id': row[0], 'email': row[1], 'password': row[2], 'created_at': row[3].isoformat()}
    for row in users
]

# Convert list of dictionaries to JSON string
json_string = json.dumps(json_data, indent=4)

print(json_string)


def register_user(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hash the password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    cursor.execute('INSERT INTO users (email, password) VALUES (%s, %s);', (email, hashed_password))
    conn.commit()
    cursor.close()
    conn.close()

def login_user(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hash the password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s;', (email, hashed_password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def get_user_projects(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT DISTINCT p.id AS project_id, p.name AS project_name
        FROM projects p
        JOIN files f ON p.id = f.project_id
        WHERE EXISTS (
            -- Direct permission to user on any file within the project
            SELECT 1 FROM file_permissions_users fpu
            WHERE fpu.file_id = f.id AND fpu.user_id = %s
        )
        OR EXISTS (
            -- Permission through group on any file within the project
            SELECT 1 FROM file_permissions_groups fpg
            JOIN user_groups ug ON fpg.group_id = ug.group_id
            WHERE fpg.file_id = f.id AND ug.user_id = %s
        );
    ''', (user_id, user_id))

    projects = cursor.fetchall()
    cursor.close()
    conn.close()
    return projects

user_id = 1
projects = get_user_projects(user_id)

json_data = [
    {'project_id': row[0], 'project_name': row[1]}
    for row in projects
]

# Convert list of dictionaries to JSON string
json_string = json.dumps(json_data, indent=4)
project_id = json_data[0]['project_id']

print(json_string)



def check_user_project_access(user_id, project_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT EXISTS (
            -- Check direct user permissions for files within the project
            SELECT 1
            FROM file_permissions_users fpu
            INNER JOIN files f ON fpu.file_id = f.id
            WHERE f.project_id = %s
            AND fpu.user_id = %s
            
            UNION
            
            -- Check group permissions for files within the project
            SELECT 1
            FROM file_permissions_groups fpg
            INNER JOIN files f ON fpg.file_id = f.id
            INNER JOIN user_groups ug ON fpg.group_id = ug.group_id
            WHERE f.project_id = %s
            AND ug.user_id = %s
        );
    ''', (project_id, user_id, project_id, user_id))

    access_exists = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return access_exists

access_exists = check_user_project_access(user_id, project_id)
print(access_exists)
