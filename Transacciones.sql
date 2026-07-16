-- Transacciones.sql
-- Script de inicialización para el sistema de reservas turísticas

-- Limpiar el esquema si ya existen las tablas
DROP TABLE IF EXISTS transportes CASCADE;
DROP TABLE IF EXISTS hoteles CASCADE;
DROP TABLE IF EXISTS vuelos CASCADE;

-- Creación de tabla Vuelos
CREATE TABLE vuelos (
    id SERIAL PRIMARY KEY, 
    destino VARCHAR(50) NOT NULL, 
    asientos INT NOT NULL CHECK (asientos >= 0)
);

-- Creación de tabla Hoteles
CREATE TABLE hoteles (
    id SERIAL PRIMARY KEY, 
    nombre VARCHAR(50) NOT NULL, 
    habitaciones INT NOT NULL
);

-- Creación de tabla Transportes
CREATE TABLE transportes (
    id SERIAL PRIMARY KEY, 
    tipo VARCHAR(50) NOT NULL, 
    vehiculos INT NOT NULL CHECK (vehiculos >= 0)
);

-- Poblado de datos iniciales
-- El hotel tiene 0 habitaciones para que falle el Paso 2 de la reserva y se active el SAVEPOINT
INSERT INTO vuelos (destino, asientos) VALUES ('Galápagos', 10);
INSERT INTO hoteles (nombre, habitaciones) VALUES ('Hotel Tortuga', 0);
INSERT INTO transportes (tipo, vehiculos) VALUES ('Transfer Privado', 10);