# easycancha-scraper

Bot de reserva automática de canchas en [easycancha.com](https://www.easycancha.com). Se programa para ejecutarse en el momento exacto en que los turnos se liberan, inicia sesión con tus credenciales y reserva el horario configurado.

---

## Stack

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| Automatización web | [Playwright](https://playwright.dev/python/) + Chromium |
| Parsing HTML | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) |
| Scheduling | [schedule](https://schedule.readthedocs.io/) |
| Variables de entorno | [python-dotenv](https://pypi.org/project/python-dotenv/) |
| Entorno local | venv + [mise](https://mise.jdx.dev/) |
| Contenedor | Docker + Docker Compose |

---

## Estructura del proyecto

```
easycancha-scraper/
├── services/
│   ├── auth.py         # Login a easycancha (sesión autenticada)
│   ├── booking.py      # Lógica de reserva (abstracta, configurable por .env)
│   ├── browser.py      # Fábrica del navegador Chromium (anti-detección + proxy)
│   ├── scheduler.py    # Scheduling — calcula el trigger y ejecuta el loop
│   └── logger.py       # Logger compartido
├── main.py             # Punto de entrada — dos líneas
├── requirements.txt  # Dependencias de producción
├── Dockerfile
├── docker-compose.yml
└── .env.example      # Plantilla de variables de entorno
```

---

## Variables de entorno

Copia `.env.example` a `.env` y completa tus datos:

```bash
cp .env.example .env
```

| Variable | Descripción | Ejemplo |
|---|---|---|
| `EMAIL` | Correo de tu cuenta easycancha | `tucorreo@gmail.com` |
| `PASSWORD` | Contraseña de tu cuenta easycancha | `MiClave123` |
| `BOOKING_URL` | URL del club y deporte en easycancha (ver abajo) | `https://www.easycancha.com/book/clubs/59/sports/1/filter` |
| `TARGET_DAY` | Día de la semana en inglés | `Saturday` |
| `TARGET_HOUR` | Hora del turno en formato 24h | `11:00` |
| `BOOKING_ADVANCE_DAYS` | Días de anticipación con que el club abre reservas | `7` |
| `BOOKING_RELEASE_HOUR` | Hora a la que se liberan los turnos (formato 24h) | `00:00` |
| `TZ` | Timezone del servidor — el scheduler usa el reloj local del contenedor | `America/Santiago` |
| `PROXY_SERVER` | Servidor proxy residencial (opcional, recomendado en cloud) | `http://proxy.ejemplo.io:9000` |
| `PROXY_USERNAME` | Usuario del proxy | `usuario_proxy` |
| `PROXY_PASSWORD` | Contraseña del proxy | `contrasena_proxy` |

> **Nota sobre `TZ`:** Los servidores cloud (Oracle, AWS, etc.) corren en UTC por defecto. Sin esta variable, `BOOKING_RELEASE_HOUR=00:00` dispararía a medianoche UTC — que en Chile equivale a las 21:00 del día anterior. Siempre define `TZ=America/Santiago`.

### Cómo encontrar tu BOOKING_URL

1. Entra a [easycancha.com](https://www.easycancha.com) desde el navegador.
2. Navega hasta el club y deporte que quieres reservar.
3. Cuando llegues a la pantalla de selección de fecha, copia la URL del navegador.
4. La URL tendrá el formato: `https://www.easycancha.com/book/clubs/<club_id>/sports/<sport_id>/filter`

---

## Setup local

### Requisitos

- Python 3.12 (se recomienda [mise](https://mise.jdx.dev/) para gestionar la versión)
- Docker (opcional, para despliegue)

### Instalación

```bash
# 1. Clonar el repositorio
git clone git@github.com:diegovaldiviac/easycancha-scraper.git
cd easycancha-scraper

# 2. Crear y activar el entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Instalar el navegador Chromium para Playwright
playwright install chromium

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus datos

# 6. Ejecutar
python main.py
```

### Prueba de reserva manual

Para disparar el scraper una vez sin esperar el scheduler:

```bash
python -c "from services.scheduler import _run; _run()"
```

---

## Deploy con Docker

```bash
# Construir y levantar el contenedor
docker compose up --build -d

# Ver logs en tiempo real
docker compose logs -f

# Detener
docker compose down
```

El contenedor se reinicia automáticamente (`restart: always`) y carga las variables desde el archivo `.env`.

---

## Cómo funciona el scheduling

El bot calcula automáticamente cuándo debe ejecutarse basándose en tres variables:

- `TARGET_DAY` — el día del turno que quieres reservar (ej: `Saturday`)
- `BOOKING_ADVANCE_DAYS` — cuántos días antes abre el club las reservas (ej: `7`)
- `BOOKING_RELEASE_HOUR` — a qué hora se liberan los turnos (ej: `00:00`)

**Ejemplo con los valores por defecto:**
> Quiero reservar el **sábado a las 11:00**. El club abre reservas **7 días antes** a **medianoche**.
> → El bot se programa para ejecutarse cada **sábado a las 00:00** (exactamente 7 días antes del sábado siguiente).

---

## Adaptación para otro club o deporte

Solo es necesario cambiar el `.env` — no se modifica código:

1. Cambia `BOOKING_URL` por la URL de tu club/deporte.
2. Ajusta `TARGET_DAY` y `TARGET_HOUR` a tu horario.
3. Actualiza `BOOKING_ADVANCE_DAYS` y `BOOKING_RELEASE_HOUR` según las reglas del club.
