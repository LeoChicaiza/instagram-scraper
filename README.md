# 📸 InstaScope — Instagram Profile Scraper

> Herramienta educativa para extracción de datos de perfiles públicos de Instagram sin usar la API oficial.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python) ![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask) ![Instaloader](https://img.shields.io/badge/Instaloader-4.x-orange) ![License](https://img.shields.io/badge/Licencia-Educativa-green)

---

## 🧠 ¿Cómo funciona el scraping?

### Método: Instaloader + HTTP directo

Esta herramienta utiliza **[Instaloader](https://instaloader.github.io/)**, una librería Python que replica las peticiones HTTP que hace el navegador web de Instagram, sin usar la API oficial de Meta.

### Flujo de extracción

```
Usuario ingresa @username
        │
        ▼
Flask API (POST /api/scrape)
        │
        ▼
Instaloader.context → GET https://www.instagram.com/{username}/
        │              (con headers y User-Agent de navegador real)
        ▼
Profile.from_username() → parsea el JSON embebido en el HTML
        │
        ▼
profile.get_posts() → itera publicaciones paginadas
        │              (añade delay aleatorio entre cada una)
        ▼
Serializa a JSON → guarda en /data/{username}_profile.json
        │
        ▼
Frontend recibe y renderiza la data
```

### ¿Por qué funciona sin API?

Instagram carga datos del perfil como un objeto JSON dentro del HTML de la página (`window.__additionalDataLoaded`). Instaloader extrae ese JSON directamente haciendo peticiones GET normales, igual que cualquier navegador. Para perfiles **públicos**, no se requiere autenticación.

### Uso de Cookies (Sesión)

Para evitar bloqueos por rate-limiting o acceder a más datos, se puede inyectar una sesión válida:

```python
# Opción 1: Login con usuario/contraseña (genera archivo de sesión)
L = instaloader.Instaloader()
L.login("tu_usuario", "tu_contraseña")
L.save_session_to_file("session_file")

# Opción 2: Cargar sesión existente
L.load_session_from_file("session_file")
```

También puedes exportar las cookies de tu navegador con extensiones como **Cookie-Editor** o **EditThisCookie** y cargarlas como diccionario en el contexto de Instaloader.

---

## 📁 Estructura del proyecto

```
instagram-scraper/
├── backend/
│   └── app.py              # API Flask con lógica de scraping
├── frontend/
│   └── index.html          # Dashboard visual (HTML/CSS/JS puro)
├── data/                   # JSONs generados (gitignored)
│   └── {username}_profile.json
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🚀 Instalación y ejecución

### Prerrequisitos
- Python 3.8+
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/instagram-scraper.git
cd instagram-scraper

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar el backend
python backend/app.py

# 4. Abrir el frontend
#    Abre en tu navegador: frontend/index.html
#    O usa un servidor local:
cd frontend && python -m http.server 3000
```

Luego abre `http://localhost:3000` en tu navegador.

---

## 🔌 API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/scrape` | Inicia extracción de un perfil |
| `GET` | `/api/profiles` | Lista perfiles ya extraídos |
| `GET` | `/api/profile/{username}` | Devuelve datos de perfil guardado |
| `GET` | `/api/health` | Estado del servidor |

### Ejemplo de request

```bash
curl -X POST http://localhost:5000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"username": "natgeo", "max_posts": 10}'
```

### Ejemplo de respuesta

```json
{
  "success": true,
  "data": {
    "username": "natgeo",
    "full_name": "National Geographic",
    "biography": "...",
    "followers": 283000000,
    "followees": 150,
    "posts_count": 32400,
    "is_private": false,
    "is_verified": true,
    "scraped_at": "2025-01-15T14:30:00Z",
    "posts": [
      {
        "shortcode": "ABC123",
        "url": "https://www.instagram.com/p/ABC123/",
        "date": "2025-01-14T18:00:00",
        "likes": 84231,
        "comments": 412,
        "caption": "...",
        "media_type": "Image",
        "thumbnail_url": "https://...",
        "hashtags": ["nature", "photography"],
        "mentions": []
      }
    ]
  }
}
```

---

## 🛡️ Anti-detección implementada

| Técnica | Implementación |
|---------|----------------|
| User-Agent real | `Mozilla/5.0 Chrome/120` |
| Delays aleatorios | `random.uniform(1.5, 3.0)` segundos entre posts |
| Sin descarga de media | Solo metadata, no imágenes/videos |
| Sesión opcional | Carga cookies para simular usuario real |

---

## ⚠️ Aviso Legal

Este proyecto es **exclusivamente educativo**. El scraping de Instagram puede violar los [Términos de Servicio de Meta](https://help.instagram.com/581066165581870). Úsalo únicamente con fines de aprendizaje sobre web scraping y extracción de datos. No scrapes perfiles privados ni uses los datos con fines comerciales.

---

## 👥 Equipo

| Nombre | Rol |
|--------|-----|
| — | Backend / Scraping |
| — | Frontend / UI |
| — | Documentación |

---

## 📦 Dependencias

```
instaloader>=4.13
flask>=3.0
flask-cors>=4.0
```
