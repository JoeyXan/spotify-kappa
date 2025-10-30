#!/bin/bash

# Script de inicio para Arquitectura Kappa
# Para ejecutar en servidor Ubuntu sin Docker

echo "=== Sistema de Recomendación - Arquitectura Kappa ==="
echo ""

# Verificar si Kafka está instalado
if ! command -v kafka-server-start.sh &> /dev/null; then
    echo "ERROR: Kafka no está instalado"
    echo "Instala Kafka desde: https://kafka.apache.org/downloads"
    exit 1
fi

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 no está instalado"
    exit 1
fi

# Instalar dependencias Python
echo "Instalando dependencias Python..."
pip3 install -r requirements.txt

# Iniciar Zookeeper
echo "Iniciando Zookeeper..."
zookeeper-server-start.sh -daemon /etc/kafka/zookeeper.properties
sleep 5

# Iniciar Kafka
echo "Iniciando Kafka..."
kafka-server-start.sh -daemon /etc/kafka/server.properties
sleep 10

# Crear topic si no existe
echo "Creando topic user-interactions..."
kafka-topics.sh --create --if-not-exists \
    --bootstrap-server localhost:9092 \
    --topic user-interactions \
    --partitions 3 \
    --replication-factor 1

# Iniciar API
echo "Iniciando API Server..."
python3 src/api_server.py &
API_PID=$!

echo ""
echo "=== Sistema iniciado correctamente ==="
echo "API disponible en: http://localhost:5000"
echo ""
echo "Para detener el sistema:"
echo "  kill $API_PID"
echo "  kafka-server-stop.sh"
echo "  zookeeper-server-stop.sh"
echo ""

# Mantener el script corriendo
wait $API_PID
