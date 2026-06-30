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

booking_files=()
for f in .env.booking*; do
    [[ "$f" == *.example ]] && continue
    [ -e "$f" ] && booking_files+=("$f")
done

if [ ${#booking_files[@]} -eq 0 ]; then
    handle_error "No se encontró ningún .env.bookingN (ej: .env.booking1)"
fi
log "Reservas encontradas: ${booking_files[*]}"

# Crear directorio remoto si no existe
log "Creando directorio remoto..."
ssh "$SERVER_USER@$SERVER_IP" "sudo mkdir -p $REMOTE_DIR && sudo chown opc:opc $REMOTE_DIR" || handle_error "No se pudo crear el directorio remoto"

# Copiar archivos al servidor
log "Copiando archivos al servidor..."
temp_dir=$(mktemp -d)
cp -r services main.py Dockerfile requirements.txt "$temp_dir"
cp .env "$temp_dir/.env"
cp "${booking_files[@]}" "$temp_dir/"

scp -r "$temp_dir"/* "$SERVER_USER@$SERVER_IP:$REMOTE_DIR" || handle_error "No se pudieron copiar los archivos al servidor"
scp "$temp_dir/.env" "$temp_dir"/.env.booking* "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/" || handle_error "No se pudo copiar .env al servidor"

rm -rf "$temp_dir"

# Verificar que .env llegó al servidor
log "Verificando .env en servidor..."
ssh "$SERVER_USER@$SERVER_IP" "test -f $REMOTE_DIR/.env" || handle_error ".env no existe en el servidor después de la copia"

# Escribir script remoto y copiarlo al servidor
log "Preparando script remoto..."
cat > /tmp/remote_deploy.sh << 'EOC'
#!/bin/bash
set -e

log() { echo -e "\033[0;32m$1\033[0m"; }
err() { echo -e "\033[0;31mError: $1\033[0m"; exit 1; }

cd /app

# Crear swap si no existe (evita OOM killer durante instalación de paquetes)
if ! swapon --show | grep -q '/swapfile'; then
    log "Creando swap de 2GB..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    log "Swap activo"
fi

# Instalar podman si no está disponible
if ! command -v podman &> /dev/null; then
    log "Podman no encontrado — instalando..."
    if command -v dnf &> /dev/null; then
        sudo dnf install -y podman || err "No se pudo instalar Podman con dnf"
    elif command -v apt-get &> /dev/null; then
        sudo apt-get update -y && sudo apt-get install -y podman || err "No se pudo instalar Podman con apt"
    else
        err "No se encontró dnf ni apt-get para instalar Podman"
    fi
    log "Podman instalado correctamente"
fi

# Construir imagen (una sola vez, todas las reservas la comparten)
log "Limpiando imágenes anteriores..."
podman system prune -f

log "Construyendo imagen..."
podman build -t scraper /app || err "No se pudo construir la imagen"

# Un contenedor por archivo .env.bookingN
for env_file in /app/.env.booking*; do
    [[ "$env_file" == *.example ]] && continue
    [ -e "$env_file" ] || continue

    name=$(basename "$env_file" | sed 's/\.env\.//')

    log "Deteniendo contenedor existente: $name"
    podman stop "$name" 2>/dev/null || true
    podman rm "$name" 2>/dev/null || true

    log "Iniciando contenedor: $name"
    podman run -d \
      --name "$name" \
      --restart always \
      --env-file /app/.env \
      --env-file "$env_file" \
      scraper || err "No se pudo iniciar el contenedor $name"
done

sleep 5

log "Contenedores en ejecución:"
podman ps

for env_file in /app/.env.booking*; do
    [[ "$env_file" == *.example ]] && continue
    [ -e "$env_file" ] || continue
    name=$(basename "$env_file" | sed 's/\.env\.//')
    if ! podman ps | grep -q "$name"; then
        err "El contenedor $name no está en ejecución"
    fi
    log "Logs de $name:"
    podman logs --tail=30 "$name"
done

log "¡Despliegue completado exitosamente!"
EOC

scp /tmp/remote_deploy.sh "$SERVER_USER@$SERVER_IP:/tmp/remote_deploy.sh" || handle_error "No se pudo copiar el script remoto"
rm /tmp/remote_deploy.sh

# Desplegar en el servidor
log "Conectando al servidor para desplegar..."
ssh -t "$SERVER_USER@$SERVER_IP" "bash /tmp/remote_deploy.sh"

if [ $? -ne 0 ]; then
    handle_error "Error durante la ejecución de comandos en el servidor"
fi

log "¡Despliegue completado exitosamente!"