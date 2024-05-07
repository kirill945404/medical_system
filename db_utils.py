import psycopg2
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect_to_database():
    try:
        conn = psycopg2.connect(
            "postgresql://gen_user:6%3A%5Cp%5C.RS%7B%7Cev9E@93.93.207.138:5432/default_db"
        )
        return conn
    except psycopg2.Error as e:
        logger.error("Error connecting to the database: %s", e)
        raise

def execute_sql():
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        # Create tables if not exists
        cur.execute("CREATE SCHEMA IF NOT EXISTS medical_system;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS medical_system.doctor_categories (
                id SERIAL PRIMARY KEY,
                category VARCHAR(255) NOT NULL
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS medical_system.users (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL UNIQUE,
                username VARCHAR(255),
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS medical_system.doctors (
                        id SERIAL PRIMARY KEY,
                        first_name VARCHAR(100) NOT NULL,
                        last_name VARCHAR(100) NOT NULL,
                        patronymic VARCHAR(100),
                        experience_years INTEGER,
                        category_id INTEGER NOT NULL,
                        FOREIGN KEY (category_id) REFERENCES medical_system.doctor_categories(id)
                    );
                """)

        conn.commit()

        cur.close()
        conn.close()
    except psycopg2.Error as e:
        logger.error("Error executing SQL queries: %s", e)
        raise

def get_doctor_categories():
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("SELECT category FROM medical_system.doctor_categories")

        categories = cur.fetchall()

        cur.close()
        conn.close()

        return [category[0] for category in categories]
    except psycopg2.Error as e:
        logger.error("Error retrieving doctor categories: %s", e)
        raise

def add_user(chat_id, username=None):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("INSERT INTO medical_system.users (chat_id, username) VALUES (%s, %s) ON CONFLICT (chat_id) DO NOTHING", (chat_id, username))

        conn.commit()

        cur.close()
        conn.close()
        logger.info("User added to the database: chat_id=%s, username=%s", chat_id, username)
    except psycopg2.Error as e:
        logger.error("Error adding user: %s", e)
        raise
def get_doctors_by_category(category):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, first_name, last_name
            FROM medical_system.doctors
            WHERE category_id = (
                SELECT id FROM medical_system.doctor_categories WHERE category = %s
            )
        """, (category,))

        doctors = cur.fetchall()

        cur.close()
        conn.close()

        return [{'id': doctor[0], 'first_name': doctor[1], 'last_name': doctor[2]} for doctor in doctors]
    except psycopg2.Error as e:
        logger.error("Error retrieving doctors by category: %s", e)
        raise