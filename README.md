# 📸 InstaScope — Instagram Scraper sin API oficial

> **Proyecto educativo** de web scraping sobre perfiles públicos de Instagram usando únicamente peticiones HTTP puras con `requests`. Sin Selenium, sin BeautifulSoup, sin librerías de automatización.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Requests](https://img.shields.io/badge/requests-2.x-orange)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![Sin API](https://img.shields.io/badge/API%20oficial-NO%20usada-red)

---

## 📋 Tabla de contenidos

1. [¿Cómo funciona el scraping?](#-cómo-funciona-el-scraping)
2. [Análisis de solicitudes web](#-análisis-de-solicitudes-web)
3. [Estrategia anti-bloqueo](#-estrategia-anti-bloqueo)
4. [Estructura del proyecto](#-estructura-del-proyecto)
5. [Instalación y uso](#-instalación-y-uso)
6. [API endpoints](#-api-endpoints)
7. [Desafíos encontrados](#-desafíos-encontrados)
8. [Aviso legal](#️-aviso-legal)

---

## 🧠 ¿Cómo funciona el scraping?

### Principio fundamental

Instagram es una Single Page Application (SPA). Cuando visitas un perfil en el navegador, Chrome realiza varias peticiones HTTP en segundo plano para traer los datos en formato JSON. **Este scraper replica exactamente esas mismas peticiones**, sin automatizar un navegador.

La diferencia con Selenium o BeautifulSoup es fundamental:
- **Selenium**: lanza un navegador real y lo controla → pesado, lento, detectable
- **BeautifulSoup**: parsea HTML estático → no sirve para SPAs con JS
- **Este proyecto**: envía peticiones HTTP directas, igual que `curl` → ligero, rápido, comprensible

### Flujo completo de extracción

```
[1] Crear sesión HTTP
        │  requests.Session() — mantiene cookies entre peticiones
        │  headers idénticos a Chrome 120
        ▼
[2] Obtener CSRF token
        │  GET https://www.instagram.com/
        │  Instagram setea 'csrftoken' en las cookies de respuesta
        │  Lo extraemos y lo añadimos al header X-CSRFToken
        ▼
[3] Petición principal del perfil
        │  GET https://www.instagram.com/{username}/?__a=1&__d=dis
        │  Instagram devuelve JSON con datos del usuario + primeros posts
        │  Parseamos manualmente el JSON con json.loads()
        ▼
[4] Paginación con GraphQL
        │  GET https://www.instagram.com/graphql/query/
        │  Parámetros: query_hash + variables (user_id, first, after)
        │  'after' es el end_cursor del lote anterior
        │  Repetimos hasta llegar al número de posts deseado
        ▼
[5] Serialización
           Guardamos en /data/{username}_profile.json
```

---

## 🔬 Análisis de solicitudes web

### ¿Cómo se descubrieron estos endpoints?

Usando **Chrome DevTools** (F12 → pestaña Network):

1. Abre Instagram en el navegador
2. Visita un perfil público
3. Filtra por `XHR` o `Fetch` en el panel Network
4. Busca peticiones a `/graphql/query/` o `?__a=1`
5. Inspecciona headers, cookies y estructura de la respuesta

### Endpoint 1: Perfil (`?__a=1`)

```
GET https://www.instagram.com/natgeo/?__a=1&__d=dis
```

| Parámetro | Valor | Significado |
|-----------|-------|-------------|
| `__a` | `1` | Solicita respuesta en JSON en vez de HTML |
| `__d` | `dis` | Desactiva redirecciones internas de IG |

**Estructura del JSON de respuesta:**
```json
{
  "graphql": {
    "user": {
      "id": "ID_NUMÉRICO",
      "username": "natgeo",
      "full_name": "National Geographic",
      "biography": "...",
      "edge_followed_by": { "count": 283000000 },
      "edge_follow": { "count": 150 },
      "edge_owner_to_timeline_media": {
        "count": 32400,
        "page_info": {
          "has_next_page": true,
          "end_cursor": "CURSOR_OPACO_BASE64"
        },
        "edges": [ /* primeros 12 posts */ ]
      }
    }
  }
}
```

### Endpoint 2: Paginación GraphQL

```
GET https://www.instagram.com/graphql/query/
    ?query_hash=e769aa130647d2354c40ea6a439bfc08
    &variables={"id":"ID","first":12,"after":"CURSOR"}
```

| Campo | Descripción |
|-------|-------------|
| `query_hash` | Hash fijo que identifica la query "ProfilePageContainer" |
| `id` | User ID obtenido del paso anterior |
| `first` | Cantidad de posts a traer (máx ~50) |
| `after` | Cursor de paginación del lote anterior |

### Headers críticos

```python
{
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120...",
    "X-IG-App-ID": "936619743392459",   # ID pública de la webapp de IG
    "X-CSRFToken": "TOKEN_OBTENIDO",    # Token anti-CSRF
    "Referer": "https://www.instagram.com/",
    "X-Requested-With": "XMLHttpRequest",
}
```

El `X-IG-App-ID` es el identificador público de la aplicación web de Instagram. Se obtiene inspeccionando cualquier petición XHR que hace IG desde el navegador.

### Cookies necesarias

Para perfiles públicos, las cookies son **opcionales** pero reducen bloqueos:

| Cookie | Descripción |
|--------|-------------|
| `sessionid` | Identifica la sesión autenticada del usuario |
| `csrftoken` | Token CSRF que debe coincidir con el header |
| `ds_user_id` | ID numérico del usuario autenticado |

Se obtienen desde Chrome DevTools → Application → Cookies → instagram.com

---

## 🛡️ Estrategia anti-bloqueo

Instagram detecta scrapers mediante varios mecanismos. Estas son las contramedidas implementadas:

| Mecanismo de IG | Contramedida implementada |
|-----------------|---------------------------|
| Detección de User-Agent de bot | User-Agent idéntico a Chrome 120 real |
| Rate limiting por IP | `time.sleep(random.uniform(2.0, 4.5))` entre requests |
| Falta de headers de navegador | Headers completos: Accept, Referer, Sec-Fetch-* |
| Ausencia de cookies | Extracción automática del csrftoken en primer request |
| Fingerprinting de la sesión | `requests.Session()` reutiliza la misma sesión TCP |
| Detección de patrones regulares | Delays **aleatorios** (no fijos) entre peticiones |

---

## 📁 Estructura del proyecto

```
instagram-scraper/
│
├── backend/
│   ├── scraper.py     ← Lógica de scraping (solo usa 'requests')
│   └── app.py         ← API Flask que expone el scraper
│
├── frontend/
│   └── index.html     ← Dashboard visual (HTML/CSS/JS puro)
│
├── data/              ← JSONs generados (ignorados por git)
│   └── .gitkeep
│
├── requirements.txt   ← Solo: requests, flask, flask-cors
├── .gitignore
├── start.sh           ← Inicio rápido Linux/Mac
├── start.bat          ← Inicio rápido Windows
└── README.md
```

---

## 🚀 Instalación y uso

### Prerrequisitos
- Python 3.8 o superior
- pip

### Pasos

```bash
# 1. Clonar
git clone https://github.com/LeoChicaiza/instagram-scraper.git
cd instagram-scraper

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Correr el backend
python backend/app.py

# 4. Abrir el frontend
#    Abre frontend/index.html en tu navegador
#    O usa servidor local:
python -m http.server 3000 --directory frontend
```

### Uso desde línea de comandos (sin frontend)

```bash
# Scrapear 10 posts del perfil 'natgeo'
python backend/scraper.py natgeo 10

# Resultado en: data/natgeo_profile.json
```

---

## 🔌 API endpoints

| Método | Ruta | Body/Params | Descripción |
|--------|------|-------------|-------------|
| `POST` | `/api/scrape` | `{username, max_posts, cookies?}` | Scrapea un perfil |
| `GET` | `/api/profiles` | — | Lista perfiles ya guardados |
| `GET` | `/api/profile/<user>` | — | Devuelve JSON de perfil guardado |
| `GET` | `/api/health` | — | Estado del servidor |

### Ejemplo cURL

```bash
# Sin cookies (perfil público)
curl -X POST http://localhost:5000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"username": "natgeo", "max_posts": 10}'

# Con cookies de sesión
curl -X POST http://localhost:5000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "username": "natgeo",
    "max_posts": 10,
    "cookies": {
      "sessionid": "TU_SESSION_ID",
      "csrftoken": "TU_CSRF_TOKEN"
    }
  }'
```

---

## ⚠️ Desafíos encontrados

### 1. Cambios frecuentes en la estructura del JSON
Instagram actualiza su estructura interna sin avisar. La solución fue hacer el parseo defensivo, intentando múltiples rutas en el JSON (`graphql.user`, `data.user`, `user`).

### 2. Rate limiting agresivo
Sin autenticación, Instagram bloquea después de pocas peticiones rápidas. Solución: delays aleatorios + session cookies opcionales.

### 3. El endpoint `?__a=1` se deprecó parcialmente
Instagram comenzó a restringir `?__a=1` para ciertas cuentas. Solución de respaldo: el endpoint GraphQL con `query_hash`.

### 4. CSRF token obligatorio
Las peticiones POST/GraphQL requieren el token CSRF. Solución: hacer primero un GET a la homepage para obtenerlo de las cookies de respuesta.

### 5. Imágenes con CORS bloqueado
Los thumbnails de Instagram tienen restricciones CORS en algunos navegadores. Solución: manejo de error en `<img>` con fallback a ícono.

---

## 📦 Dependencias

```
requests>=2.31   # HTTP puro — ÚNICA librería de scraping
flask>=3.0       # Servidor API
flask-cors>=4.0  # CORS para el frontend
```

**Ausencia intencional de:** `selenium`, `beautifulsoup4`, `playwright`, `scrapy`, `instaloader`

---

## ⚖️ Aviso Legal

Este proyecto es **exclusivamente educativo**, desarrollado para comprender el funcionamiento de las solicitudes HTTP y técnicas de web scraping. El uso de este código para scraping masivo, comercial o sobre perfiles privados puede violar los [Términos de Servicio de Meta](https://help.instagram.com/581066165581870). El autor no se responsabiliza del uso indebido.
