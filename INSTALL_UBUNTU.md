# Guía de Instalación en Servidor Ubuntu

Esta guía te ayudará a instalar y ejecutar el sistema de recomendación con Arquitectura Kappa en tu servidor Ubuntu.

## Requisitos del Servidor

- Ubuntu 20.04 LTS o superior
- 4 GB RAM mínimo (8 GB recomendado)
- 10 GB espacio en disco
- Acceso root o sudo
- Conexión a internet

## Opción 1: Instalación con Docker (Recomendado)

Esta es la forma más simple y confiable.

### Paso 1: Instalar Docker

```bash
# Actualizar paquetes
sudo apt-get update

# Instalar dependencias
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Agregar clave GPG de Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Agregar repositorio
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verificar instalación
sudo docker --version
```

### Paso 2: Instalar Docker Compose

```bash
# Docker Compose v2 ya viene con docker-compose-plugin
# Verificar
docker compose version

# Si no está instalado, instalar manualmente:
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Paso 3: Configurar permisos

```bash
# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Aplicar cambios (o cerrar sesión y volver a entrar)
newgrp docker

# Verificar
docker ps
```

### Paso 4: Copiar proyecto al servidor

```bash
# Opción A: Desde tu máquina local
scp -r spotify-kappa usuario@tu-servidor:/home/usuario/

# Opción B: Clonar desde repositorio
git clone https://github.com/tu-usuario/spotify-kappa.git
cd spotify-kappa
```

### Paso 5: Ejecutar el sistema

```bash
cd spotify-kappa

# Dar permisos de ejecución
chmod +x start-docker.sh

# Iniciar sistema
./start-docker.sh
```

### Paso 6: Verificar que funciona

```bash
# Ver logs
docker-compose logs -f

# Verificar servicios
docker-compose ps

# Probar API
curl http://localhost:5000/api/stats
```

### Paso 7: Acceder desde fuera del servidor

Si quieres acceder desde tu navegador:

```bash
# Opción A: Túnel SSH
ssh -L 5000:localhost:5000 usuario@tu-servidor

# Luego abre en tu navegador: http://localhost:5000

# Opción B: Configurar firewall
sudo ufw allow 5000/tcp
sudo ufw reload

# Luego abre: http://IP-DE-TU-SERVIDOR:5000
```

## Opción 2: Instalación Sin Docker

Si no puedes usar Docker, sigue estos pasos.

### Paso 1: Instalar Java

```bash
sudo apt-get update
sudo apt-get install -y openjdk-11-jdk

# Verificar
java -version
```

### Paso 2: Instalar Kafka

```bash
# Descargar Kafka
cd /tmp
wget https://downloads.apache.org/kafka/3.6.0/kafka_2.13-3.6.0.tgz

# Extraer
tar -xzf kafka_2.13-3.6.0.tgz

# Mover a /opt
sudo mv kafka_2.13-3.6.0 /opt/kafka

# Configurar PATH
echo 'export PATH=$PATH:/opt/kafka/bin' >> ~/.bashrc
source ~/.bashrc

# Verificar
kafka-topics.sh --version
```

### Paso 3: Instalar Python y dependencias

```bash
# Instalar Python 3.11
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Crear entorno virtual
cd spotify-kappa
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 4: Configurar Kafka como servicio

```bash
# Crear servicio de Zookeeper
sudo nano /etc/systemd/system/zookeeper.service
```

Contenido:
```ini
[Unit]
Description=Apache Zookeeper
After=network.target

[Service]
Type=simple
User=ubuntu
ExecStart=/opt/kafka/bin/zookeeper-server-start.sh /opt/kafka/config/zookeeper.properties
ExecStop=/opt/kafka/bin/zookeeper-server-stop.sh
Restart=on-abnormal

[Install]
WantedBy=multi-user.target
```

```bash
# Crear servicio de Kafka
sudo nano /etc/systemd/system/kafka.service
```

Contenido:
```ini
[Unit]
Description=Apache Kafka
After=zookeeper.service

[Service]
Type=simple
User=ubuntu
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-abnormal

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar servicios
sudo systemctl daemon-reload
sudo systemctl enable zookeeper
sudo systemctl enable kafka

# Iniciar servicios
sudo systemctl start zookeeper
sleep 5
sudo systemctl start kafka
sleep 10

# Verificar
sudo systemctl status zookeeper
sudo systemctl status kafka
```

### Paso 5: Crear topic de Kafka

```bash
kafka-topics.sh --create --if-not-exists \
    --bootstrap-server localhost:9092 \
    --topic user-interactions \
    --partitions 3 \
    --replication-factor 1

# Verificar
kafka-topics.sh --list --bootstrap-server localhost:9092
```

### Paso 6: Crear servicio para la API

```bash
sudo nano /etc/systemd/system/kappa-api.service
```

Contenido:
```ini
[Unit]
Description=Kappa API Server
After=kafka.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/spotify-kappa
Environment="PATH=/home/ubuntu/spotify-kappa/venv/bin"
ExecStart=/home/ubuntu/spotify-kappa/venv/bin/python src/api_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar e iniciar
sudo systemctl daemon-reload
sudo systemctl enable kappa-api
sudo systemctl start kappa-api

# Verificar
sudo systemctl status kappa-api
```

### Paso 7: Verificar instalación

```bash
# Ver logs
sudo journalctl -u kappa-api -f

# Probar API
curl http://localhost:5000/api/stats
```

## Configuración de Firewall

```bash
# Permitir puerto de la API
sudo ufw allow 5000/tcp

# Si quieres acceso externo a Kafka (no recomendado)
sudo ufw allow 9092/tcp

# Recargar firewall
sudo ufw reload
```

## Configuración de Nginx (Opcional)

Para usar un dominio y HTTPS:

```bash
# Instalar Nginx
sudo apt-get install -y nginx

# Crear configuración
sudo nano /etc/nginx/sites-available/kappa-api
```

Contenido:
```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/kappa-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Monitoreo

### Ver logs en tiempo real

```bash
# Con Docker
docker-compose logs -f api

# Sin Docker
sudo journalctl -u kappa-api -f
```

### Ver uso de recursos

```bash
# CPU y memoria
htop

# Espacio en disco
df -h

# Con Docker
docker stats
```

### Ver mensajes de Kafka

```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic user-interactions --from-beginning
```

## Mantenimiento

### Reiniciar servicios

```bash
# Con Docker
docker-compose restart

# Sin Docker
sudo systemctl restart zookeeper
sudo systemctl restart kafka
sudo systemctl restart kappa-api
```

### Limpiar logs antiguos de Kafka

```bash
# Editar configuración de Kafka
sudo nano /opt/kafka/config/server.properties

# Agregar/modificar:
log.retention.hours=168  # 7 días
log.segment.bytes=1073741824  # 1 GB
```

### Backup del estado del modelo

```bash
# El archivo model_state.pkl contiene el estado
cp model_state.pkl model_state_backup_$(date +%Y%m%d).pkl
```

## Troubleshooting

### Error: "Connection refused"

```bash
# Verificar que Kafka esté corriendo
sudo systemctl status kafka

# Ver logs de Kafka
sudo journalctl -u kafka -n 50
```

### Error: "Out of memory"

```bash
# Aumentar memoria de Kafka
sudo nano /opt/kafka/bin/kafka-server-start.sh

# Cambiar:
export KAFKA_HEAP_OPTS="-Xmx2G -Xms2G"
```

### API no responde

```bash
# Ver logs
sudo journalctl -u kappa-api -n 100

# Verificar puerto
sudo netstat -tulpn | grep 5000
```

## Desinstalación

### Con Docker

```bash
docker-compose down -v
docker system prune -a
```

### Sin Docker

```bash
# Detener servicios
sudo systemctl stop kappa-api
sudo systemctl stop kafka
sudo systemctl stop zookeeper

# Deshabilitar servicios
sudo systemctl disable kappa-api
sudo systemctl disable kafka
sudo systemctl disable zookeeper

# Eliminar archivos
sudo rm /etc/systemd/system/kappa-api.service
sudo rm /etc/systemd/system/kafka.service
sudo rm /etc/systemd/system/zookeeper.service
sudo rm -rf /opt/kafka
sudo rm -rf ~/spotify-kappa

# Recargar systemd
sudo systemctl daemon-reload
```

## Resumen de Comandos Útiles

```bash
# Iniciar sistema (Docker)
cd spotify-kappa && ./start-docker.sh

# Ver logs (Docker)
docker-compose logs -f

# Detener sistema (Docker)
docker-compose down

# Iniciar sistema (Sin Docker)
sudo systemctl start zookeeper kafka kappa-api

# Ver estado (Sin Docker)
sudo systemctl status kappa-api

# Probar API
curl http://localhost:5000/api/stats
```
