#!/bin/bash

# Script de inicio con Docker Compose
# Opción más simple y recomendada

echo "=== Sistema de Recomendación - Arquitectura Kappa (Docker) ==="
echo ""

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker no está instalado"
    echo "Instala Docker desde: https://docs.docker.com/engine/install/ubuntu/"
    exit 1
fi

# Verificar Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose no está instalado"
    exit 1
fi

# Detener contenedores previos
echo "Deteniendo contenedores previos..."
docker-compose down

# Construir e iniciar servicios
echo "Construyendo e iniciando servicios..."
docker-compose up --build -d

# Esperar a que Kafka esté listo
echo "Esperando a que Kafka esté listo..."
sleep 15

# Crear topic
echo "Creando topic user-interactions..."
docker exec kafka kafka-topics --create --if-not-exists \
    --bootstrap-server localhost:9092 \
    --topic user-interactions \
    --partitions 3 \
    --replication-factor 1

echo ""
echo "=== Sistema iniciado correctamente ==="
echo "API disponible en: http://localhost:5000"
echo ""
echo "Comandos útiles:"
echo "  Ver logs:     docker-compose logs -f"
echo "  Ver logs API: docker-compose logs -f api"
echo "  Detener:      docker-compose down"
echo ""
