import MySQLdb
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return MySQLdb.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        passwd=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )

def get_admin_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM admin WHERE email = %s", (email,))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()
    return admin
