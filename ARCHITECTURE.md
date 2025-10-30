# Arquitectura Kappa - Documentación Técnica

## Introducción

La Arquitectura Kappa es un patrón de procesamiento de datos que simplifica la Arquitectura Lambda eliminando la capa batch y manteniendo solo el procesamiento en tiempo real mediante streams.

## Principios Fundamentales

### 1. Todo es un Stream

En Kappa, todos los datos se tratan como eventos en un stream continuo. No hay distinción entre datos históricos y datos en tiempo real.

### 2. Procesamiento Único

Solo existe una capa de procesamiento que maneja todos los eventos, eliminando la complejidad de mantener dos sistemas separados (batch y velocidad).

### 3. Reprocesamiento mediante Replay

Si necesitas cambiar la lógica de procesamiento, simplemente reproduces (replay) el stream desde el principio con la nueva lógica.

## Comparación: Lambda vs Kappa

| Característica | Lambda | Kappa |
|---------------|--------|-------|
| **Capas** | Batch + Velocidad + Servicio | Solo Stream |
| **Complejidad** | Alta (3 capas) | Media (1 capa) |
| **Latencia** | Media (batch periódico) | Baja (siempre real-time) |
| **Consistencia** | Eventual | Inmediata |
| **Reprocesamiento** | Fácil (re-run batch) | Replay del stream |
| **Mantenimiento** | Complejo (2 códigos) | Simple (1 código) |
| **Uso de recursos** | Alto | Medio |
| **Casos de uso** | Análisis histórico + real-time | Solo real-time |

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    ARQUITECTURA KAPPA                        │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Interacciones   │  ← Usuarios interactúan con canciones
│  de Usuarios     │     (play, like, skip)
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│                    APACHE KAFKA                              │
│  Topic: user-interactions                                    │
│  - Particiones: 3                                            │
│  - Replicación: 1                                            │
│  - Retención: 7 días                                         │
└────────┬─────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│               STREAM PROCESSOR (Kappa)                       │
│                                                              │
│  Procesa cada evento en tiempo real:                        │
│  1. Actualiza historial de usuario                          │
│  2. Actualiza popularidad de tracks                         │
│  3. Recalcula preferencias de usuario                       │
│  4. Mantiene matriz de similitud                            │
│                                                              │
│  Estado en memoria:                                          │
│  - user_interactions: Dict[user_id, List[events]]          │
│  - track_popularity: Dict[track_id, score]                 │
│  - similarity_matrix: numpy.ndarray                         │
└────────┬─────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│                    API REST (Flask)                          │
│                                                              │
│  Endpoints:                                                  │
│  - GET  /api/stats          → Estadísticas                 │
│  - GET  /api/tracks         → Lista de canciones           │
│  - POST /api/recommend      → Recomendaciones              │
│  - POST /api/interact       → Registrar interacción        │
│  - GET  /api/trending       → Trending tracks              │
│  - GET  /api/user/<id>      → Perfil de usuario            │
└──────────────────────────────────────────────────────────────┘
```

## Componentes Detallados

### 1. Apache Kafka

**Rol**: Message broker para streaming de eventos

**Configuración**:
- Topic: `user-interactions`
- Particiones: 3 (permite procesamiento paralelo)
- Replicación: 1 (para desarrollo; 3 en producción)
- Retención: 7 días (permite replay reciente)

**Ventajas**:
- Alta throughput (millones de mensajes/segundo)
- Durabilidad (eventos persisten en disco)
- Escalabilidad horizontal
- Replay de eventos

### 2. Stream Processor

**Rol**: Procesa eventos y mantiene el modelo actualizado

**Clase**: `KappaStreamProcessor`

**Responsabilidades**:

#### a) Consumir eventos de Kafka

```python
consumer = KafkaConsumer(
    'user-interactions',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    event = message.value
    process_event(event)
```

#### b) Actualizar estado en tiempo real

```python
def process_event(event):
    user_id = event['user_id']
    track_id = event['track_id']
    interaction_type = event['interaction_type']
    
    # Actualizar historial de usuario
    self.user_interactions[user_id].append(event)
    
    # Actualizar popularidad
    weight = {'play': 1, 'like': 3, 'skip': -1}[interaction_type]
    self.track_popularity[track_id] += weight
```

#### c) Generar recomendaciones

```python
def get_recommendations(track_id, user_id, top_n=10):
    # 1. Obtener similitud base (matriz precalculada)
    sim_scores = similarity_matrix[track_idx]
    
    # 2. Aplicar boost de popularidad
    for idx, score in sim_scores:
        popularity_boost = track_popularity[track_id] * 0.01
        final_score = score + popularity_boost
    
    # 3. Personalizar por usuario
    if user_id in user_interactions:
        # Boost por géneros preferidos
        liked_genres = get_user_preferred_genres(user_id)
        if track_genre in liked_genres:
            final_score *= 1.2
    
    return top_n_recommendations
```

### 3. API REST

**Rol**: Interfaz para consultas y registro de eventos

**Framework**: Flask

**Endpoints**:

#### GET /api/stats
Retorna estadísticas del sistema en tiempo real

#### POST /api/recommend
Genera recomendaciones personalizadas

Flujo:
1. Recibe track_id y user_id
2. Consulta modelo en memoria
3. Aplica personalización
4. Retorna top N recomendaciones

#### POST /api/interact
Registra nueva interacción

Flujo:
1. Recibe evento de usuario
2. Envía a Kafka
3. Stream processor lo consume
4. Modelo se actualiza automáticamente

## Flujo de Datos Completo

### Caso de Uso: Usuario da "like" a una canción

```
1. Usuario hace clic en "like" en la interfaz
   ↓
2. Frontend envía POST /api/interact
   {
     "user_id": "user_123",
     "track_id": "abc...",
     "interaction_type": "like"
   }
   ↓
3. API envía evento a Kafka topic "user-interactions"
   ↓
4. Stream Processor consume el evento
   ↓
5. Actualiza estado en memoria:
   - user_interactions["user_123"].append(evento)
   - track_popularity["abc..."] += 3
   ↓
6. Próxima vez que user_123 pida recomendaciones:
   - Se consideran sus likes recientes
   - Se boostan canciones de géneros similares
   - Se retornan recomendaciones personalizadas
```

## Modelo de Recomendación

### Características de Audio

El modelo usa 11 características de Spotify Web API:

| Feature | Descripción | Rango |
|---------|-------------|-------|
| danceability | Qué tan bailable es | 0.0 - 1.0 |
| energy | Intensidad y actividad | 0.0 - 1.0 |
| valence | Positividad musical | 0.0 - 1.0 |
| acousticness | Nivel acústico | 0.0 - 1.0 |
| instrumentalness | Contenido instrumental | 0.0 - 1.0 |
| speechiness | Voz hablada | 0.0 - 1.0 |
| liveness | Grabación en vivo | 0.0 - 1.0 |
| tempo | Velocidad (BPM) | 60 - 200 |
| loudness | Volumen (dB) | -20 - 0 |
| key | Tonalidad | 0 - 11 |
| mode | Mayor/menor | 0 - 1 |

### Algoritmo de Similitud

```python
# 1. Normalizar características
scaler = StandardScaler()
features_scaled = scaler.fit_transform(features)

# 2. Calcular similitud coseno
similarity_matrix = cosine_similarity(features_scaled)

# 3. Para cada par de canciones (i, j):
similarity(i, j) = cos(θ) = (A · B) / (||A|| × ||B||)
```

### Personalización

```python
# Score base (similitud de audio)
base_score = similarity_matrix[track_i][track_j]

# Boost de popularidad global
popularity_boost = track_popularity[track_j] * 0.01

# Boost de preferencias de usuario
user_boost = 1.0
if track_genre in user_preferred_genres:
    user_boost = 1.2

# Score final
final_score = (base_score + popularity_boost) * user_boost
```

## Persistencia y Recuperación

### Guardar Estado

```python
def save_state():
    state = {
        'similarity_matrix': similarity_matrix,
        'scaler': scaler,
        'tracks_df': tracks_df,
        'user_interactions': dict(user_interactions),
        'track_popularity': dict(track_popularity)
    }
    pickle.dump(state, open('model_state.pkl', 'wb'))
```

### Cargar Estado

```python
def load_state():
    state = pickle.load(open('model_state.pkl', 'rb'))
    similarity_matrix = state['similarity_matrix']
    user_interactions = state['user_interactions']
    # ...
```

## Escalabilidad

### Escalar Horizontalmente

#### 1. Aumentar particiones de Kafka

```bash
kafka-topics.sh --alter --bootstrap-server localhost:9092 \
    --topic user-interactions --partitions 10
```

Permite hasta 10 consumidores en paralelo.

#### 2. Múltiples instancias del procesador

```bash
docker-compose up --scale api=3
```

Kafka distribuye particiones entre consumidores.

#### 3. Cluster de Kafka

Agregar más brokers para mayor throughput y tolerancia a fallos.

### Escalar Verticalmente

- Aumentar memoria para mantener más datos en RAM
- Más CPU para procesar eventos más rápido
- SSD para lectura/escritura más rápida

## Tolerancia a Fallos

### Durabilidad de Eventos

Kafka persiste eventos en disco. Si el procesador falla, los eventos no se pierden.

### Recuperación

1. Procesador se reinicia
2. Carga último estado guardado (`model_state.pkl`)
3. Continúa consumiendo desde último offset
4. Procesa eventos perdidos durante la caída

### Replicación

En producción, configurar replicación de Kafka:

```yaml
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
```

## Monitoreo y Métricas

### Métricas Clave

1. **Throughput**: Eventos procesados/segundo
2. **Latencia**: Tiempo desde evento hasta actualización
3. **Lag**: Diferencia entre offset actual y último mensaje
4. **Memoria**: Uso de RAM del procesador
5. **Popularidad**: Distribución de interacciones

### Herramientas

- Kafka Manager: UI para monitorear Kafka
- Prometheus + Grafana: Métricas y dashboards
- ELK Stack: Logs centralizados

## Ventajas de Kappa para este Caso de Uso

1. **Simplicidad**: Una sola capa de procesamiento
2. **Baja latencia**: Recomendaciones siempre actualizadas
3. **Escalabilidad**: Kafka maneja millones de eventos/seg
4. **Replay**: Fácil reprocesar con nueva lógica
5. **Consistencia**: No hay desfase entre batch y velocidad

## Limitaciones

1. **Reprocesamiento costoso**: Replay de todo el stream toma tiempo
2. **Estado en memoria**: Limitado por RAM disponible
3. **Complejidad de Kafka**: Requiere conocimiento de Kafka
4. **No apto para análisis histórico complejo**: Lambda es mejor para eso

## Conclusión

La Arquitectura Kappa es ideal para sistemas de recomendación que priorizan:
- Baja latencia
- Actualización continua
- Simplicidad operacional

Para este proyecto de recomendación de música, Kappa ofrece un balance óptimo entre rendimiento y complejidad.
