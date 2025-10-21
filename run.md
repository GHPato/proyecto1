# 🚀 Guía de Ejecución - Sistema de Inventario Distribuido

Esta guía te permitirá ejecutar el sistema de inventario distribuido en **Windows**, **Linux** y **macOS**.

## 📋 Prerrequisitos

### Software Requerido
- **Docker** ([Descargar](https://www.docker.com/products/docker-desktop/))
- **Docker Compose** (incluido con Docker Desktop)

### Verificar Instalaciones
```bash
# Verificar Docker
docker --version
docker-compose --version
```

## 🛠️ Configuración Inicial

### 1. Extraer el Proyecto
```bash
# Extraer el archivo .zip en tu directorio de trabajo
# El proyecto se extraerá en la carpeta 'hackerrank-challenge'
cd hackerrank-challenge
```

## 🐳 Ejecución con Docker (Recomendado)

### 1. Levantar Servicios
```bash
# Reconstruir la imagen Docker (importante para obtener los últimos cambios)
docker-compose build --no-cache

# Levantar todos los servicios (FastAPI + Redis + SQLite)
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Verificar que todos los servicios estén corriendo
docker-compose ps
```

### 2. Verificar Servicios
```bash
# Verificar que la API esté funcionando
curl http://localhost:8000/health/ready
```

### 3. Base de Datos (Automático)
```bash
# La base de datos se crea y puebla automáticamente al levantar los servicios
# Proceso automático:
# 1. Crear directorio de datos
# 2. Esperar a que Redis esté listo
# 3. Crear tablas de la base de datos
# 4. Poblar con datos de ejemplo
# 5. Iniciar la aplicación
```


## 🧪 Ejecutar Tests

### Tests con Docker (Recomendado)
```bash
# Ejecutar todos los tests
docker-compose exec api python -m pytest src/tests/ -v
```

### Tests Locales (Solo si no usas Docker)
```bash
# Requiere Python instalado localmente
python -m pytest src/tests/ -v
```

## 📊 Verificar Funcionamiento

### 1. Health Checks
```bash
# Verificar estado del sistema
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/live
curl http://localhost:8000/metrics
```

### 2. API Endpoints
```bash
# Ver documentación de la API
# Abrir en navegador: http://localhost:8000/docs

# Ver inventario
curl http://localhost:8000/inventory/all

# Ver tiendas
curl http://localhost:8000/stores/all
```

### 3. Subscribirse a Eventos en Tiempo Real
```bash
# Conectar a Redis y subscribirse a eventos
docker-compose exec redis redis-cli

# Dentro de Redis CLI, subscribirse al topic de eventos
SUBSCRIBE inventory_events

# Ahora verás todos los eventos en tiempo real cuando se publiquen
# Ejemplo de eventos que verás:
# - stock_reserved
# - stock_updated  
# - reservation_confirmed
# - reservation_cancelled
```

### 4. Ejemplo de Uso Completo
```bash
# 1. Subscribirse a eventos (en otra terminal)
docker-compose exec redis redis-cli
SUBSCRIBE inventory_events

# 2. Reservar stock (esto publicará un evento)
curl -X POST "http://localhost:8000/inventory/reserve" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORDER-123",
    "product_id": "123e4567-e89b-12d3-a456-426614174000",
    "store_id": "123e4567-e89b-12d3-a456-426614174001",
    "quantity": 2,
    "ttl_minutes": 30
  }'

# 3. Verás el evento "stock_reserved" en Redis CLI
```


## 🔧 Comandos Útiles

### Docker
```bash
# Ver logs de un servicio específico
docker-compose logs api
docker-compose logs redis

# Reiniciar servicios
docker-compose restart

# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v

# Reconstruir imágenes
docker-compose build --no-cache

# Reset completo del entorno (Linux/macOS)
./reset-docker.sh

# Reset completo del entorno (Windows)
# Ejecutar los comandos del script manualmente o usar WSL
```


## 🐛 Solución de Problemas

### Puerto 8000 en Uso
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:8000 | xargs kill -9
```

### Puerto 6379 en Uso (Redis)
```bash
# Windows
netstat -ano | findstr :6379
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:6379 | xargs kill -9
```

### Problemas con Docker
```bash
# Limpiar contenedores y volúmenes
docker system prune -a
docker volume prune

# Reiniciar Docker Desktop (Windows/macOS)
# O reiniciar servicio Docker (Linux)
sudo systemctl restart docker
```

### Problemas con Python
```bash
# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall

# Verificar versión de Python
python --version
# Debe ser 3.11 o superior
```

## 📱 Acceso a la Aplicación

- **API**: http://localhost:8000
- **Documentación Swagger**: http://localhost:8000/docs
- **Documentación ReDoc**: http://localhost:8000/redoc
- **Métricas**: http://localhost:8000/metrics
- **Health Check**: http://localhost:8000/health/ready


## 🚨 Solución de Problemas

### Error: "No such file or directory" para scripts
```bash
# Si ves errores como "can't open file /app/scripts/init_database.py"
# Reconstruir la imagen Docker con los últimos cambios
docker-compose build --no-cache
docker-compose up -d
```

### Error: "no such table: products"
```bash
# Si la base de datos no se inicializa correctamente
docker-compose down -v
docker-compose up -d
```

## 📞 Soporte

Si encuentras problemas:

1. Verifica que todos los prerrequisitos estén instalados
2. Revisa los logs con `docker-compose logs`
3. Verifica que los puertos 8000 y 6379 estén disponibles
4. Asegúrate de que Python sea versión 3.11+
5. Revisa que Docker esté funcionando correctamente