import datetime

import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_admin(chat_id):
    user_id = get_user_id_by_chat_id(chat_id)
    if not user_id:
        return False
    conn = connect_to_database()
    cur = conn.cursor()
    cur.execute("SELECT role FROM medical_system.users WHERE id = %s", (user_id,))
    role = cur.fetchone()
    cur.close()
    conn.close()
    return role and role[0] == "admin"

def get_doctors_list():
    conn = connect_to_database()
    cur = conn.cursor()
    cur.execute("SELECT doc.id, doc.first_name, doc.last_name, doc.patronymic, hospitals.name, dc.category,doc.category_id,doc.hospital_id "
                "FROM medical_system.doctors doc "
                "JOIN medical_system.hospitals ON doc.hospital_id = hospitals.id "
                "JOIN medical_system.doctor_categories dc ON doc.category_id = dc.id;")
    doctors_info = cur.fetchall()
    cur.close()
    conn.close()
    return doctors_info



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
        #cur.execute("""
         #           CREATE TABLE IF NOT EXISTS medical_system.search_requests (
          #          id SERIAL PRIMARY KEY,
           #         user_id INTEGER NOT NULL,
            #        doctor_id INTEGER NOT NULL,
             #       search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              #      completed BOOLEAN DEFAULT FALSE,
               #     created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                #    modified TIMESTAMP
                #);
                #""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS medical_system.users (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL UNIQUE,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                patronymic VARCHAR(255),
                medical_policy VARCHAR(255),
                passport VARCHAR(255),
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                role VARCHAR(10) DEFAULT 'user' CHECK (role IN ('admin', 'user'))
            );
        """)
        cur.execute("""
                            CREATE TABLE IF NOT EXISTS medical_system.hospitals (
                                id SERIAL PRIMARY KEY,
                                name VARCHAR(255) NOT NULL,
                                address TEXT
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
                hospital_id INTEGER NOT NULL,
                FOREIGN KEY (category_id) REFERENCES medical_system.doctor_categories(id),
                FOREIGN KEY (hospital_id) REFERENCES medical_system.hospitals(id)
            );
        """)
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS medical_system.appointments (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        doctor_id INTEGER NOT NULL,
                        appointment_date TIMESTAMP NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES medical_system.users(id),
                        FOREIGN KEY (doctor_id) REFERENCES medical_system.doctors(id),
                        is_active BOOLEAN DEFAULT TRUE
                    );
                """)
        conn.commit()

        cur.close()
        conn.close()
    except psycopg2.Error as e:
        logger.error("Error executing SQL queries: %s", e)
        raise


def add_search_request(user_id, doctor_id, selected_date):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO medical_system.search_requests (user_id, doctor_id, search_date) VALUES (%s, %s, %s)",
            (user_id, doctor_id, selected_date))

        conn.commit()

        cur.close()
        conn.close()

        logger.info("Search request added to the database: user_id=%s, doctor_id=%s, selected_date=%s",
                    user_id, doctor_id, selected_date)
    except psycopg2.Error as e:
        logger.error("Error adding search request: %s", e)
        raise


def get_pending_search_requests():
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, user_id, doctor_id, search_date
            FROM medical_system.search_requests
            WHERE completed = FALSE
        """)

        pending_requests = cur.fetchall()

        cur.close()
        conn.close()

        return [{'id': request[0], 'user_id': request[1], 'doctor_id': request[2], 'selected_date': request[3]} for
                request in pending_requests]
    except psycopg2.Error as e:
        logger.error("Error retrieving pending search requests: %s", e)
        raise


def mark_request_completed(request_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            UPDATE medical_system.search_requests
            SET completed = TRUE, modified = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (request_id,))

        conn.commit()

        cur.close()
        conn.close()

        logger.info("Search request marked as completed: request_id=%s", request_id)
    except psycopg2.Error as e:
        logger.error("Error marking search request as completed: %s", e)
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


def add_user(chat_id, username, first_name, last_name, patronymic, medical_policy, passport):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO medical_system.users (chat_id, username, first_name, last_name, patronymic, medical_policy, passport) 
            VALUES (%s, %s, %s, %s, %s, %s, %s) 
            ON CONFLICT (chat_id) DO NOTHING
            """,
            (chat_id, username, first_name, last_name, patronymic, medical_policy, passport)
        )

        conn.commit()

        cur.close()
        conn.close()

        if cur.rowcount == 0:
            logger.info("User already exists in the database: chat_id=%s, username=%s", chat_id, username)
        else:
            logger.info("User added to the database: chat_id=%s, username=%s", chat_id, username)
    except psycopg2.Error as e:
        logger.error("Error adding user: %s", e)
        raise

def user_exists(chat_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("SELECT id FROM medical_system.users WHERE chat_id = %s", (chat_id,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        return user is not None
    except psycopg2.Error as e:
        logger.error("Error checking if user exists: %s", e)
        raise

def get_hospitals_by_category(category):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, name
            FROM medical_system.hospitals
            WHERE id IN (
                SELECT DISTINCT hospital_id 
                FROM medical_system.doctors 
                WHERE category_id = (
                    SELECT id FROM medical_system.doctor_categories WHERE category = %s
                )
            )
        """, (category,))

        hospitals = cur.fetchall()

        cur.close()
        conn.close()

        return [{'id': hospital[0], 'name': hospital[1]} for hospital in hospitals]
    except psycopg2.Error as e:
        logger.error("Error retrieving hospitals by category: %s", e)
        raise


def get_doctors_by_category_and_hospital(category, hospital_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, first_name, last_name
            FROM medical_system.doctors
            WHERE category_id = (
                SELECT id FROM medical_system.doctor_categories WHERE category = %s
            ) AND hospital_id = %s
        """, (category, hospital_id))

        doctors = cur.fetchall()

        cur.close()
        conn.close()

        return [{'id': doctor[0], 'first_name': doctor[1], 'last_name': doctor[2]} for doctor in doctors]
    except psycopg2.Error as e:
        logger.error("Error retrieving doctors by category and hospital: %s", e)
        raise


def get_doctor_info(doctor_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT first_name, last_name, hospital_id
            FROM medical_system.doctors
            WHERE id = %s
        """, (doctor_id,))

        doctor_info = cur.fetchone()

        cur.close()
        conn.close()

        if doctor_info:
            return {'first_name': doctor_info[0], 'last_name': doctor_info[1], 'hospital_id': doctor_info[2]}
        else:
            return None
    except psycopg2.Error as e:
        logger.error("Error retrieving doctor info: %s", e)
        raise


def get_hospital_info(hospital_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT name
            FROM medical_system.hospitals
            WHERE id = %s
        """, (hospital_id,))

        hospital_info = cur.fetchone()

        cur.close()
        conn.close()

        if hospital_info:
            return {'name': hospital_info[0]}
        else:
            return None
    except psycopg2.Error as e:
        logger.error("Error retrieving hospital info: %s", e)
        raise


def add_appointment(user_id, doctor_id, appointment_datetime):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO medical_system.appointments (user_id, doctor_id, appointment_date) VALUES (%s, %s, %s)",
            (user_id, doctor_id, appointment_datetime))

        conn.commit()

        cur.close()
        conn.close()

        logger.info("Appointment added to the database: user_id=%s, doctor_id=%s, appointment_datetime=%s",
                    user_id, doctor_id, appointment_datetime)
    except psycopg2.Error as e:
        logger.error("Error adding appointment: %s", e)
        raise

def get_chat_id_by_user_id(user_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("SELECT chat_id FROM medical_system.users WHERE id = %s", (user_id,))
        chat_id = cur.fetchone()

        cur.close()
        conn.close()

        return chat_id[0] if chat_id else None
    except psycopg2.Error as e:
        logger.error("Error retrieving chat ID by user ID: %s", e)
        raise

def get_user_id_by_chat_id(chat_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("SELECT id FROM medical_system.users WHERE chat_id = %s", (chat_id,))

        user_id = cur.fetchone()

        cur.close()
        conn.close()

        return user_id[0] if user_id else None
    except psycopg2.Error as e:
        logger.error("Error retrieving user id by chat id: %s", e)
        raise


def get_booked_dates(doctor_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT DATE(appointment_date) 
            FROM medical_system.appointments 
            WHERE doctor_id = %s
        """, (doctor_id,))

        booked_dates = cur.fetchall()

        cur.close()
        conn.close()

        return [date[0] for date in booked_dates]
    except psycopg2.Error as e:
        logger.error("Error retrieving booked dates for doctor: %s", e)
        raise


def get_user_appointments_info(user_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT a.id, d.first_name, d.last_name, h.name, h.address, a.appointment_date
            FROM medical_system.appointments a
            JOIN medical_system.doctors d ON a.doctor_id = d.id
            JOIN medical_system.hospitals h ON d.hospital_id = h.id
            WHERE a.user_id = %s AND a.is_active = TRUE
        """, (user_id,))

        appointments_info = cur.fetchall()

        cur.close()
        conn.close()

        return appointments_info
    except psycopg2.Error as e:
        logger.error("Error retrieving user appointments info: %s", e)
        raise

def available_slots_found(selected_date, doctor_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*) 
            FROM medical_system.appointments 
            WHERE DATE(appointment_date) = %s AND doctor_id = %s AND is_active = TRUE
        """, (selected_date, doctor_id))

        appointment_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        # If there are available slots, return True
        return appointment_count < 6  # Assuming there are maximum 6 appointments allowed per day

    except psycopg2.Error as e:
        logger.error("Error checking available slots: %s", e)
        raise

def get_booked_hours(selected_date, doctor_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT EXTRACT(HOUR FROM appointment_date) 
            FROM medical_system.appointments 
            WHERE DATE(appointment_date) = %s AND doctor_id = %s AND is_active = TRUE
        """, (selected_date, doctor_id))

        booked_hours = cur.fetchall()

        cur.close()
        conn.close()

        return [datetime.time(int(hour[0])) for hour in booked_hours]
    except psycopg2.Error as e:
        logger.error("Error retrieving booked hours for selected date and doctor: %s", e)
        raise


def get_appointment_info(appointment_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT a.doctor_id, a.appointment_date, d.first_name, d.last_name
            FROM medical_system.appointments a
            JOIN medical_system.doctors d ON a.doctor_id = d.id
            WHERE a.id = %s
        """, (appointment_id,))

        appointment_info = cur.fetchone()

        cur.close()
        conn.close()

        if appointment_info:
            return {'doctor_id': appointment_info[0], 'appointment_date': appointment_info[1],
                    'doctor_name': f"{appointment_info[2]} {appointment_info[3]}"}
        else:
            return None
    except psycopg2.Error as e:
        logger.error("Error retrieving appointment info: %s", e)
        raise


def cancel_appointment_by_id(appointment_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()

        cur.execute("""
            UPDATE medical_system.appointments
            SET is_active = FALSE
            WHERE id = %s
        """, (appointment_id,))

        conn.commit()

        cur.close()
        conn.close()

        logger.info("Appointment with ID %s has been canceled.", appointment_id)
    except psycopg2.Error as e:
        logger.error("Error canceling appointment: %s", e)
        raise
