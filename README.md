# Simulación de Transacciones - Sistema de Reservas

Este proyecto es una simulación práctica de operaciones transaccionales en bases de datos relacionales utilizando Python (psycopg2) y PostgreSQL.

## 1. Introducción Teórica

* **Transacciones anidadas y Savepoints:** Una transacción atómica asegura que un bloque de operaciones se ejecute completamente o no se ejecute en absoluto. Los *savepoints* (puntos de guardado) permiten segmentar esta transacción, logrando realizar *rollbacks* parciales sin deshacer todo el trabajo previo.
* **Deadlocks (Interbloqueos):** Ocurren en entornos concurrentes cuando dos o más transacciones se bloquean mutuamente porque cada una tiene un recurso que la otra necesita para continuar. La base de datos debe intervenir matando una de las transacciones.
* **Timeouts:** Es un límite de tiempo establecido para que una consulta o transacción se complete. Previene que recursos del sistema se queden bloqueados indefinidamente por consultas ineficientes o bloqueos de red.

## 2. Explicación del Escenario

El script modela una agencia de viajes que reserva un paquete turístico en 3 pasos secuenciales atómicos:
1.  Compra de pasaje de avión (tabla `vuelos`).
2.  Reserva de habitación (tabla `hoteles`).
3.  Reserva de vehículo (tabla `transportes`).

El escenario está preparado intencionalmente para que la tabla `hoteles` no tenga cupo. Al detectarse esto, el código vuelve al *savepoint* previo al hotel y lanza una "transacción de compensación", la cual se encarga de devolver el asiento de avión previamente reservado.

## 3. Preguntas de Reflexión

**¿Por qué es importante usar savepoints en transacciones largas? ¿Qué problema resuelven?**
Resuelven el problema del "todo o nada" estricto. En procesos largos (ej. facturación masiva, orquestación de microservicios mediante base de datos), si falla el paso 9 de 10, un rollback total eliminaría trabajo costoso y válido. Los savepoints permiten manejar excepciones lógicas, revertir solo el segmento problemático, y aplicar lógicas de compensación manteniendo la transacción activa.

**En el escenario de reserva, ¿qué pasaría si no usáramos savepoints y el hotel no tuviera cupo? ¿Cómo afectaría a la consistencia de los datos?**
Si no usáramos savepoints y la base de datos lanzara un error, toda la transacción haría un *rollback* automático (perdiendo la reserva del vuelo). Si el error fuera lógico (manejado por código sin rollback de DB), podríamos cometer el error de hacer un *commit* dejando al cliente con un vuelo pagado pero sin hotel. Los savepoints aseguran la integridad sin perder el control del flujo.

**¿Cómo se produce un deadlock en una base de datos? Explica el ejemplo que implementaste y cómo lo resolviste.**
Un deadlock ocurre por un "abrazo mortal" (circular wait). En mi script, la `Transacción A` bloquea la tabla *vuelos* y luego intenta bloquear *hoteles*. Al mismo tiempo, la `Transacción B` bloquea *hoteles* y busca bloquear *vuelos*. Ninguna puede avanzar. PostgreSQL detecta el ciclo automáticamente después de `deadlock_timeout` (usualmente 1s) y cancela una transacción, permitiendo que la otra finalice.

**¿Qué estrategias de mitigación existen para evitar deadlocks en sistemas concurrentes?**
1. **Ordenamiento estricto:** Asegurar que todas las transacciones soliciten los recursos en el mismo orden jerárquico (ej. siempre bloquear vuelos primero, hoteles después).
2. **Timeouts cortos:** Configurar `lock_timeout` para que los procesos se rindan rápido si no obtienen el recurso.
3. **Manejo de reintentos:** Implementar lógica en el backend (Python) para capturar el error `DeadlockDetected` y reintentar la transacción con un retraso exponencial (backoff).

**¿Qué sucede cuando una transacción alcanza el timeout? ¿Cómo afecta al usuario final y qué mecanismos se pueden implementar para manejar esta situación?**
Cuando se alcanza el `statement_timeout`, PostgreSQL aborta inmediatamente la consulta y hace rollback. El usuario final puede percibir esto como un error en la aplicación o una pantalla de carga que termina en "Fallo de conexión". Para manejarlo, se debe usar programación asíncrona en el frontend, colas de mensajería en el backend (ej. RabbitMQ) para procesar la petición en segundo plano, o notificar al usuario con un mensaje amigable invitándolo a intentar más tarde.
