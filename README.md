# Sistema de Recomendación de Música - Arquitectura Kappa

Sistema de recomendación de música en tiempo real basado en Arquitectura Kappa, que procesa eventos de interacciones de usuario mediante Apache Kafka y actualiza el modelo de forma continua.

## Arquitectura Kappa

A diferencia de la Arquitectura Lambda que separa procesamiento batch y velocidad, la Arquitectura Kappa utiliza un único flujo de procesamiento en tiempo real:

```
Eventos de Usuario → Kafka Stream → Procesador → Modelo Actualizado → API REST
```

### Ventajas de Kappa

- Arquitectura más simple (una sola capa de procesamiento)
- Todo el procesamiento es en tiempo real
- Menor complejidad operacional
- Modelo siempre actualizado con los últimos datos

### Componentes

1. **Apache Kafka**: Message broker para streaming de eventos
2. **Stream Processor**: Procesa eventos y actualiza modelo en tiempo real
3. **API REST**: Expone endpoints para consultas y registro de interacciones
4. **Dashboard Web**: Interfaz para visualizar estadísticas

## Requisitos

### Opción 1: Con Docker (Recomendado)

- Docker 20.10+
- Docker Compose 2.0+
- 4 GB RAM mínimo
- 10 GB espacio en disco

### Opción 2: Sin Docker

- Ubuntu 20.04+ o similar
- Python 3.8+
- Apache Kafka 3.0+
- Java 11+ (para Kafka)
- 4 GB RAM mínimo

## Instalación y Ejecución

### Opción 1: Con Docker Compose (Recomendado)

```bash
# 1. Clonar o copiar el proyecto
cd spotify-kappa

# 2. Ejecutar script de inicio
./start-docker.sh

# 3. Acceder a la API
# http://localhost:5000
```

El script automáticamente:
- Inicia Zookeeper
- Inicia Kafka
- Crea el topic necesario
- Inicia la API

### Opción 2: Sin Docker

#### Paso 1: Instalar Kafka

```bash
# Descargar Kafka
wget https://downloads.apache.org/kafka/3.6.0/kafka_2.13-3.6.0.tgz
tar -xzf kafka_2.13-3.6.0.tgz
sudo mv kafka_2.13-3.6.0 /opt/kafka

# Configurar variables de entorno
echo 'export PATH=$PATH:/opt/kafka/bin' >> ~/.bashrc
source ~/.bashrc
```

#### Paso 2: Instalar dependencias Python

```bash
pip3 install -r requirements.txt
```

#### Paso 3: Iniciar el sistema

```bash
./start.sh
```

O manualmente:

```bash
# Terminal 1: Zookeeper
zookeeper-server-start.sh /opt/kafka/config/zookeeper.properties

# Terminal 2: Kafka
kafka-server-start.sh /opt/kafka/config/server.properties

# Terminal 3: Crear topic
kafka-topics.sh --create --bootstrap-server localhost:9092 \
    --topic user-interactions --partitions 3 --replication-factor 1

# Terminal 4: API
python3 src/api_server.py
```

## Uso de la API

### Dashboard Web

Abre en tu navegador:
```
http://localhost:5000
```

### Endpoints Disponibles

#### 1. Obtener estadísticas del sistema

```bash
curl http://localhost:5000/api/stats
```

Respuesta:
```json
{
  "total_tracks": 4832,
  "total_users": 15,
  "total_interactions": 234,
  "track_popularity_count": 156
}
```

#### 2. Buscar canciones

```bash
curl "http://localhost:5000/api/search?q=love"
```

#### 3. Obtener recomendaciones

```bash
curl -X POST http://localhost:5000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "track_id": "5SuOikwiRyPMVoIQDJUgSV",
    "user_id": "user_1",
    "top_n": 10
  }'
```

Respuesta:
```json
{
  "track_id": "5SuOikwiRyPMVoIQDJUgSV",
  "user_id": "user_1",
  "recommendations": [
    {
      "track_id": "...",
      "track_name": "Canción Similar",
      "artists": "Artista",
      "track_genre": "pop",
      "score": 0.95,
      "popularity": 12
    }
  ]
}
```

#### 4. Registrar interacción

```bash
curl -X POST http://localhost:5000/api/interact \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_1",
    "track_id": "5SuOikwiRyPMVoIQDJUgSV",
    "interaction_type": "like"
  }'
```

Tipos de interacción:
- `play`: Reproducción
- `like`: Me gusta
- `skip`: Saltar

#### 5. Ver trending tracks

```bash
curl "http://localhost:5000/api/trending?top_n=10"
```

#### 6. Obtener perfil de usuario

```bash
curl http://localhost:5000/api/user/user_1
```

## Simular Actividad de Usuarios

Para probar el sistema con datos simulados:

```bash
python3 src/event_producer.py
```

Esto generará eventos aleatorios de usuarios interactuando con canciones.

## Arquitectura Técnica

### Flujo de Datos

```
1. Usuario interactúa con canción
   ↓
2. Evento enviado a Kafka topic "user-interactions"
   ↓
3. Stream Processor consume evento
   ↓
4. Modelo se actualiza en tiempo real
   - Actualiza popularidad de tracks
   - Actualiza historial de usuario
   - Recalcula recomendaciones si es necesario
   ↓
5. API consulta modelo actualizado
   ↓
6. Usuario recibe recomendaciones personalizadas
```

### Procesamiento en Tiempo Real

El sistema mantiene:
- Matriz de similitud entre canciones (basada en características de audio)
- Historial de interacciones por usuario (últimas 100)
- Popularidad de cada canción (actualizada continuamente)
- Preferencias de usuario (géneros, artistas)

Cada nuevo evento actualiza estos componentes inmediatamente.

### Características de Audio

El modelo usa 11 características de Spotify:
- danceability: Qué tan bailable es
- energy: Intensidad y actividad
- valence: Positividad musical
- acousticness: Nivel acústico
- instrumentalness: Contenido instrumental
- speechiness: Presencia de voz hablada
- liveness: Grabación en vivo
- tempo: Velocidad (BPM)
- loudness: Volumen (dB)
- key: Tonalidad
- mode: Mayor/menor

## Persistencia

El sistema guarda su estado periódicamente en `model_state.pkl`:
- Matriz de similitud
- Historial de usuarios
- Popularidad de tracks

Al reiniciar, carga el estado previo y continúa procesando.

## Monitoreo

### Ver logs en Docker

```bash
# Todos los servicios
docker-compose logs -f

# Solo API
docker-compose logs -f api

# Solo Kafka
docker-compose logs -f kafka
```

### Ver topics de Kafka

```bash
# Listar topics
kafka-topics.sh --list --bootstrap-server localhost:9092

# Ver mensajes del topic
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic user-interactions --from-beginning
```

## Detener el Sistema

### Con Docker

```bash
docker-compose down
```

### Sin Docker

```bash
# Detener API (Ctrl+C en la terminal)

# Detener Kafka
kafka-server-stop.sh

# Detener Zookeeper
zookeeper-server-stop.sh
```

## Estructura del Proyecto

```
spotify-kappa/
├── src/
│   ├── stream_processor.py    # Procesador de streams Kafka
│   ├── event_producer.py      # Generador de eventos
│   └── api_server.py          # API REST con Flask
├── data/
│   └── dataset.csv            # Dataset de Spotify
├── docker/
├── config/
├── docker-compose.yml         # Configuración Docker
├── Dockerfile                 # Imagen de la aplicación
├── requirements.txt           # Dependencias Python
├── start.sh                   # Script de inicio sin Docker
├── start-docker.sh            # Script de inicio con Docker
└── README.md                  # Este archivo
```

## Dataset

**Fuente**: Spotify Tracks Dataset - Kaggle

**Características**:
- 114,000 canciones
- 125 géneros musicales
- 11 características de audio por canción

## Diferencias con Arquitectura Lambda

| Aspecto | Lambda | Kappa |
|---------|--------|-------|
| Capas | Batch + Velocidad + Servicio | Solo Stream |
| Complejidad | Alta | Media |
| Latencia | Media (batch periódico) | Baja (siempre real-time) |
| Reprocesamiento | Fácil (re-run batch) | Difícil (replay stream) |
| Consistencia | Eventual | Inmediata |
| Uso de recursos | Alto | Medio |

## Troubleshooting

### Error: "Connection refused" al iniciar

Kafka no está listo. Espera 10-15 segundos después de iniciar Kafka antes de iniciar la API.

### Error: "Topic does not exist"

Crea el topic manualmente:
```bash
kafka-topics.sh --create --bootstrap-server localhost:9092 \
    --topic user-interactions --partitions 3 --replication-factor 1
```

### API no responde

Verifica que todos los servicios estén corriendo:
```bash
docker-compose ps  # Con Docker
# o
ps aux | grep kafka  # Sin Docker
```

### Modelo no se actualiza

Verifica que los eventos lleguen a Kafka:
```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic user-interactions --from-beginning
```

## Escalabilidad

Para escalar el sistema:

1. **Aumentar particiones de Kafka**:
```bash
kafka-topics.sh --alter --bootstrap-server localhost:9092 \
    --topic user-interactions --partitions 10
```

2. **Múltiples instancias del procesador**:
```bash
docker-compose up --scale api=3
```

3. **Cluster de Kafka**:
Modificar `docker-compose.yml` para agregar más brokers.

## Licencia

Dataset bajo licencia ODbL-1.0 (Open Database License).

## Autor

Desarrollado como proyecto educativo de Arquitectura Kappa aplicada a sistemas de recomendación en tiempo real.
