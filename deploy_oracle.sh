#!/bin/bash

# Configuración
if [ -f ".env" ]; then
  source .env
else
  echo -e "\033[0;31mError: .env file not found. SERVER_IP is required.\033[0m"
  exit 1
fi

if [ -z "$SERVER_IP" ]; then
  echo -e "\033[0;31mError: SERVER_IP not defined in .env file\033[0m"
  exit 1
fi

SERVER_USER="opc"
REMOTE_DIR="/app"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${2:-$GREEN}$1${NC}"
}

handle_error() {
    log "Error: $1" "$RED"
    exit 1
}

log "Iniciando despliegue en $SERVER_IP..."

# Verificar archivos locales
log "Verificando archivos locales..."
missing_files=false

required_files=(
    "services"
    "main.py"
    "Dockerfile"
    "requirements.txt"
    ".env"
)

for file in "${required_files[@]}"; do
    if [ ! -e "$file" ]; then
        log "Error: '$file' no encontrado" "$RED"
        missing_files=true
    fi
done

if [ "$missing_files" = true ]; then
    handle_error "Faltan archivos necesarios"
fi

# Crear directorio remoto si no existe
log "Creando directorio remoto..."
ssh "$SERVER_USER@$SERVER_IP" "sudo mkdir -p $REMOTE_DIR && sudo chown opc:opc $REMOTE_DIR" || handle_error "No se pudo crear el directorio remoto"

# Copiar archivos al servidor
log "Copiando archivos al servidor..."
temp_dir=$(mktemp -d)
cp -r services main.py Dockerfile requirements.txt "$temp_dir"
cp .env "$temp_dir/.env"

scp -r "$temp_dir"/* "$SERVER_USER@$SERVER_IP:$REMOTE_DIR" || handle_error "No se pudieron copiar los archivos al servidor"
scp "$temp_dir/.env" "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/.env" || handle_error "No se pudo copiar .env al servidor"

rm -rf "$temp_dir"

# Verificar que .env llegó al servidor
log "Verificando .env en servidor..."
ssh "$SERVER_USER@$SERVER_IP" "test -f $REMOTE_DIR/.env" || handle_error ".env no existe en el servidor después de la copia"

# Desplegar en el servidor
log "Conectando al servidor para desplegar..."
ssh "$SERVER_USER@$SERVER_IP" << 'EOC'
cd /app

log() { echo -e "\033[0;32m$1\033[0m"; }
handle_error() { echo -e "\033[0;31mError: $1\033[0m"; exit 1; }

# Verificar podman
if ! command -v podman &> /dev/null; then
    handle_error "Podman no está instalado."
fi

# Crear directorios y archivos necesarios
log "Creando directorios necesarios..."
mkdir -p /app/data /app/logs /app/backups
touch /app/already_seen.json
chmod 666 /app/already_seen.json

# Detener y eliminar contenedor existente
log "Deteniendo contenedor existente..."
podman stop scraper 2>/dev/null
podman rm scraper 2>/dev/null

# Limpiar imágenes anteriores
log "Limpiando imágenes anteriores..."
podman system prune -f

# Construir imagen
log "Construyendo imagen..."
podman build -t scraper /app || handle_error "No se pudo construir la imagen"

# Iniciar contenedor
log "Iniciando contenedor..."
podman run -d \
  --name scraper \
  --restart always \
  -v /app/already_seen.json:/app/already_seen.json \
  --env-file /app/.env \
  scraper || handle_error "No se pudo iniciar el contenedor"

sleep 5

# Verificar que está corriendo
if ! podman ps | grep -q "scraper"; then
    handle_error "El contenedor no está en ejecución"
fi

log "Logs del contenedor..."
podman logs --tail=50 scraper

log "¡Despliegue completado exitosamente!"
EOC

if [ $? -ne 0 ]; then
    handle_error "Error durante la ejecución de comandos en el servidor"
fi

log "¡Despliegue completado exitosamente!"