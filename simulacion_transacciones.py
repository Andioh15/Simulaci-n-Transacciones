import psycopg2
import psycopg2.errors
import threading
import time

# Configuración de la base de datos
DB_CONFIG = {
    "dbname": "DB",
    "user": "postgres",
    "password": "1234", 
    "host": "localhost",
    "port": "5432"
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def setup_database():
    """Crea las tablas y las puebla con datos iniciales."""
    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("--- Configurando Base de Datos ---")
    cursor.execute("DROP TABLE IF EXISTS transportes, hoteles, vuelos CASCADE;")
    
    cursor.execute("""
        CREATE TABLE vuelos (id SERIAL PRIMARY KEY, destino VARCHAR(50), asientos INT);
        CREATE TABLE hoteles (id SERIAL PRIMARY KEY, nombre VARCHAR(50), habitaciones INT);
        CREATE TABLE transportes (id SERIAL PRIMARY KEY, tipo VARCHAR(50), vehiculos INT);
    """)
    
    # Insertamos datos de prueba (Hotel con 0 habitaciones para forzar el fallo)
    cursor.execute("INSERT INTO vuelos (destino, asientos) VALUES ('Galapagos', 10);")
    cursor.execute("INSERT INTO hoteles (nombre, habitaciones) VALUES ('Hotel Tortuga', 0);") 
    cursor.execute("INSERT INTO transportes (tipo, vehiculos) VALUES ('Transfer Privado', 10);")
    
    print("Tablas creadas y pobladas. (Hotel intencionalmente sin cupo para probar savepoints).\n")
    cursor.close()
    conn.close()

def simular_reserva_con_savepoints():
    """Simula una transacción con savepoint y compensación."""
    print("--- Iniciando Simulación de Reserva (Savepoints) ---")
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN;")
        
        # Paso 1: Vuelo
        print("Paso 1: Reservando vuelo...")
        cursor.execute("UPDATE vuelos SET asientos = asientos - 1 WHERE id = 1 RETURNING asientos;")
        print(f"Vuelo reservado. Asientos restantes: {cursor.fetchone()[0]}")
        
        # Creamos el Savepoint antes del hotel
        cursor.execute("SAVEPOINT antes_del_hotel;")
        print("SAVEPOINT 'antes_del_hotel' creado.")
        time.sleep(2) # Pausa manual para observar el proceso
        
        # Paso 2: Hotel (Fallará porque hay 0 habitaciones y pondremos un CHECK temporal para simular el error de aplicación)
        print("Paso 2: Intentando reservar hotel...")
        cursor.execute("SELECT habitaciones FROM hoteles WHERE id = 1 FOR UPDATE;")
        habs = cursor.fetchone()[0]
        
        if habs <= 0:
            raise Exception("No hay cupo en el hotel.")
            
        cursor.execute("UPDATE hoteles SET habitaciones = habitaciones - 1 WHERE id = 1;")
        
        # Paso 3: Transporte
        cursor.execute("UPDATE transportes SET vehiculos = vehiculos - 1 WHERE id = 1;")
        
        conn.commit()
        print("Reserva completada con éxito.")
        
    except Exception as e:
        print(f"Error detectado: {e}")
        print("Ejecutando ROLLBACK al savepoint 'antes_del_hotel'...")
        cursor.execute("ROLLBACK TO SAVEPOINT antes_del_hotel;")
        
        print("Ejecutando transacción de compensación (cancelando vuelo)...")
        # Compensación: devolver el asiento
        cursor.execute("UPDATE vuelos SET asientos = asientos + 1 WHERE id = 1 RETURNING asientos;")
        print(f"Compensación exitosa. Vuelo cancelado. Asientos actuales: {cursor.fetchone()[0]}")
        
        conn.commit()
        print("Estado final guardado en la base de datos.\n")
    finally:
        cursor.close()
        conn.close()

def transaccion_a():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN;")
        print("[TX-A] Bloqueando vuelos...")
        cursor.execute("UPDATE vuelos SET asientos = asientos - 1 WHERE id = 1;")
        time.sleep(3) # Pausa para forzar la concurrencia
        print("[TX-A] Intentando bloquear hoteles...")
        cursor.execute("UPDATE hoteles SET habitaciones = habitaciones - 1 WHERE id = 1;")
        conn.commit()
    except Exception as e:
        print(f"[TX-A] Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def transaccion_b():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN;")
        print("[TX-B] Bloqueando hoteles...")
        cursor.execute("UPDATE hoteles SET habitaciones = habitaciones - 1 WHERE id = 1;")
        time.sleep(3) # Pausa para forzar la concurrencia
        print("[TX-B] Intentando bloquear vuelos...")
        cursor.execute("UPDATE vuelos SET asientos = asientos - 1 WHERE id = 1;")
        conn.commit()
    except Exception as e:
        print(f"[TX-B] Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def simular_deadlock():
    print("--- Iniciando Simulación de Deadlock ---")
    print("Lanzando hilos concurrentes que acceden a recursos de forma cruzada...")
    t1 = threading.Thread(target=transaccion_a)
    t2 = threading.Thread(target=transaccion_b)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    print("Simulación de deadlock finalizada.\n")

def simular_timeout():
    print("--- Iniciando Simulación de Timeout ---")
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Configuramos el timeout de la transacción a 1 segundo
        cursor.execute("SET statement_timeout = '1s';")
        print("Timeout configurado a 1 segundo.")
        print("Ejecutando consulta pesada (pg_sleep de 3 segundos)...")
        
        cursor.execute("SELECT pg_sleep(3);")
        
    except psycopg2.errors.QueryCanceled as e:
        print(f"Excepción capturada con éxito: La consulta fue cancelada por timeout.")
        print(f"Detalle técnico: {e}")
    finally:
        cursor.close()
        conn.close()
        print("Simulación de timeout finalizada.\n")

if __name__ == "__main__":
    setup_database()
    simular_reserva_con_savepoints()
    simular_deadlock()
    simular_timeout()

#Resultado esperado:
#--- Configurando Base de Datos ---
#Tablas creadas y pobladas. (Hotel intencionalmente sin cupo para probar savepoints).
#
#--- Iniciando Simulación de Reserva (Savepoints) ---
#Paso 1: Reservando vuelo...
#Vuelo reservado. Asientos restantes: 9
#SAVEPOINT 'antes_del_hotel' creado.
#Paso 2: Intentando reservar hotel...
#Error detectado: No hay cupo en el hotel.
#Ejecutando ROLLBACK al savepoint 'antes_del_hotel'...
#Ejecutando transacción de compensación (cancelando vuelo)...
#Compensación exitosa. Vuelo cancelado. Asientos actuales: 10
#Estado final guardado en la base de datos.
#
#--- Iniciando Simulación de Deadlock ---
#Lanzando hilos concurrentes que acceden a recursos de forma cruzada...
#[TX-A] Bloqueando vuelos...
#[TX-B] Bloqueando hoteles...
#[TX-A] Intentando bloquear hoteles...
#[TX-B] Intentando bloquear vuelos...
#[TX-B] Error: deadlock detected
#DETAIL:  Process 15932 waits for ShareLock on transaction 913; blocked by process 16048.
#Process 16048 waits for ShareLock on transaction 914; blocked by process 15932.
#HINT:  See server log for query details.
#CONTEXT:  while updating tuple (0,3) in relation "vuelos"
#
#imulación de deadlock finalizada.
#
#--- Iniciando Simulación de Timeout ---
#Timeout configurado a 1 segundo.
#Ejecutando consulta pesada (pg_sleep de 3 segundos)...
#Excepción capturada con éxito: La consulta fue cancelada por timeout.
#Detalle técnico: canceling statement due to statement timeout
#
#Simulación de timeout finalizada.