"""
scraper.py — Instagram scraper con requests HTTP puros
======================================================
Sin Selenium, sin BeautifulSoup, sin Instaloader.
Solo requests + análisis manual de los endpoints de Instagram.

Estrategia:
  1. GET https://www.instagram.com/{username}/?__a=1&__d=dis
     → Instagram devuelve el perfil como JSON (endpoint no documentado)
  2. Para paginar posts se usa el endpoint GraphQL interno de Instagram
     con el cursor `end_cursor` que viene en cada respuesta.
  3. Headers y cookies reales del navegador para evitar bloqueos.
"""

import requests
import json
import time
import random
import os
import re

# ── Directorio de salida ──────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)


# ── Headers que imitan un navegador Chrome real ───────────────────────────────
# Instagram bloquea peticiones sin User-Agent válido.
# Estos headers son los mismos que envía Chrome 120 al visitar Instagram.
BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.instagram.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-IG-App-ID": "936619743392459",   # ID pública de la web app de Instagram
    "X-Requested-With": "XMLHttpRequest",
}


def _delay():
    """
    Pausa aleatoria entre peticiones.
    Imita el comportamiento humano y reduce la probabilidad de rate-limiting.
    """
    time.sleep(random.uniform(2.0, 4.5))


def _build_session(cookies_dict: dict = None) -> requests.Session:
    """
    Crea una sesión HTTP reutilizable con los headers base.
    Una sesión mantiene cookies automáticamente entre peticiones,
    igual que un navegador real.

    cookies_dict: opcional — cookies exportadas manualmente del navegador.
    Las cookies críticas de Instagram son:
      - sessionid   → identifica la sesión autenticada
      - csrftoken   → token anti-CSRF requerido en peticiones POST
      - ds_user_id  → ID numérico del usuario autenticado
    """
    session = requests.Session()
    session.headers.update(BASE_HEADERS)

    if cookies_dict:
        for name, value in cookies_dict.items():
            session.cookies.set(name, value, domain=".instagram.com")

    return session


def _extract_csrf(session: requests.Session) -> str:
    """
    Visita la página principal de Instagram para obtener el csrftoken.
    Este token es necesario para peticiones autenticadas.
    Lo extraemos de las cookies que Instagram setea en la respuesta.
    """
    try:
        resp = session.get("https://www.instagram.com/", timeout=15)
        token = session.cookies.get("csrftoken", "")
        if token:
            session.headers["X-CSRFToken"] = token
        return token
    except Exception:
        return ""


def fetch_profile(username: str, session: requests.Session) -> dict:
    """
    Obtiene los datos básicos del perfil usando el endpoint no documentado:
      GET /username/?__a=1&__d=dis

    Este endpoint devuelve un JSON con la estructura completa del perfil.
    Fue descubierto analizando el tráfico de red de Instagram con DevTools.

    Parámetros:
      __a=1    → indica que queremos respuesta JSON en lugar de HTML
      __d=dis  → desactiva redirecciones internas de Instagram
    """
    url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"

    try:
        resp = session.get(url, timeout=15)

        if resp.status_code == 404:
            return {"error": f"El perfil @{username} no existe."}
        if resp.status_code == 401:
            return {"error": "Acceso denegado. Se requieren cookies de sesión."}
        if resp.status_code == 429:
            return {"error": "Rate limit alcanzado. Espera unos minutos."}
        if resp.status_code != 200:
            return {"error": f"Error HTTP {resp.status_code}"}

        data = resp.json()

        # La estructura del JSON varía; Instagram usa "graphql" o "data"
        user = (
            data.get("graphql", {}).get("user") or
            data.get("data", {}).get("user") or
            data.get("user") or
            {}
        )

        if not user:
            return {"error": "No se pudo parsear el perfil. Instagram puede haber cambiado su estructura."}

        return {
            "id": user.get("id", ""),
            "username": user.get("username", username),
            "full_name": user.get("full_name", ""),
            "biography": user.get("biography", ""),
            "followers": user.get("edge_followed_by", {}).get("count", 0),
            "followees": user.get("edge_follow", {}).get("count", 0),
            "posts_count": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "is_private": user.get("is_private", False),
            "is_verified": user.get("is_verified", False),
            "profile_pic_url": user.get("profile_pic_url_hd") or user.get("profile_pic_url", ""),
            "external_url": user.get("external_url", ""),
            # Guardamos el end_cursor inicial para paginar posts después
            "_end_cursor": (
                user.get("edge_owner_to_timeline_media", {})
                    .get("page_info", {})
                    .get("end_cursor", "")
            ),
            "_has_next_page": (
                user.get("edge_owner_to_timeline_media", {})
                    .get("page_info", {})
                    .get("has_next_page", False)
            ),
            # Posts de la primera página (vienen incluidos en este request)
            "_initial_posts": (
                user.get("edge_owner_to_timeline_media", {})
                    .get("edges", [])
            ),
        }

    except requests.exceptions.ConnectionError:
        return {"error": "Sin conexión a internet."}
    except requests.exceptions.Timeout:
        return {"error": "Timeout. Instagram tardó demasiado en responder."}
    except json.JSONDecodeError:
        return {"error": "Instagram no devolvió JSON válido (posible bloqueo)."}


def fetch_posts_graphql(user_id: str, end_cursor: str,
                        session: requests.Session, count: int = 12) -> dict:
    """
    Paginación de posts usando el endpoint GraphQL interno de Instagram.
    
    URL: GET /graphql/query/
    
    Parámetros descubiertos analizando el tráfico de red con Chrome DevTools:
      - query_hash: hash fijo que identifica la query de posts del perfil
      - variables: JSON con el user_id, cantidad, y cursor de paginación

    El cursor (end_cursor) es un string opaco que Instagram usa para saber
    desde qué punto continuar la paginación, similar a un offset pero más
    robusto frente a inserciones/eliminaciones.
    """
    # Este query_hash es el identificador de la query "ProfilePageContainer"
    # Se obtiene inspeccionando las peticiones XHR en Chrome DevTools
    QUERY_HASH = "e769aa130647d2354c40ea6a439bfc08"

    variables = json.dumps({
        "id": user_id,
        "first": count,
        "after": end_cursor
    })

    url = "https://www.instagram.com/graphql/query/"
    params = {
        "query_hash": QUERY_HASH,
        "variables": variables
    }

    try:
        resp = session.get(url, params=params, timeout=15)

        if resp.status_code == 429:
            return {"error": "Rate limit en GraphQL. Espera antes de continuar."}
        if resp.status_code != 200:
            return {"error": f"GraphQL error HTTP {resp.status_code}"}

        data = resp.json()
        media = (
            data.get("data", {})
                .get("user", {})
                .get("edge_owner_to_timeline_media", {})
        )

        return {
            "edges": media.get("edges", []),
            "end_cursor": media.get("page_info", {}).get("end_cursor", ""),
            "has_next_page": media.get("page_info", {}).get("has_next_page", False),
        }

    except json.JSONDecodeError:
        return {"error": "Respuesta GraphQL inválida."}
    except Exception as e:
        return {"error": str(e)}


def _parse_post(edge: dict) -> dict:
    """
    Extrae los campos relevantes de un nodo de post del JSON de Instagram.
    La estructura viene de edge > node en el JSON de GraphQL.
    """
    node = edge.get("node", {})

    # El caption puede venir anidado en edge_media_to_caption > edges > [0] > node > text
    caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
    caption = caption_edges[0]["node"]["text"] if caption_edges else ""

    # Extraer hashtags del caption con regex simple (sin BeautifulSoup)
    hashtags = re.findall(r"#(\w+)", caption)
    mentions = re.findall(r"@(\w+)", caption)

    return {
        "shortcode": node.get("shortcode", ""),
        "url": f"https://www.instagram.com/p/{node.get('shortcode', '')}/",
        "date": node.get("taken_at_timestamp", 0),
        "date_iso": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(node.get("taken_at_timestamp", 0))
        ),
        "likes": node.get("edge_liked_by", {}).get("count", 0),
        "comments": node.get("edge_media_to_comment", {}).get("count", 0),
        "media_type": "Video" if node.get("is_video") else "Image",
        "thumbnail_url": node.get("thumbnail_url") or node.get("display_url", ""),
        "dimensions": node.get("dimensions", {}),
        "caption": caption[:400],
        "hashtags": hashtags[:10],
        "mentions": mentions[:10],
        "location": node.get("location", {}).get("name") if node.get("location") else None,
        "accessibility_caption": node.get("accessibility_caption", ""),
    }


def scrape(username: str, max_posts: int = 10, cookies: dict = None) -> dict:
    """
    Función principal de scraping.
    Orquesta todas las peticiones para obtener perfil + posts.

    Flujo:
      1. Crear sesión HTTP con headers de navegador
      2. Visitar instagram.com para obtener csrftoken
      3. Llamar al endpoint ?__a=1 para obtener datos del perfil
      4. Parsear los posts de la primera página (vienen gratis en paso 3)
      5. Si necesitamos más posts → paginar con GraphQL usando end_cursor
      6. Serializar todo a JSON
    """
    username = username.strip().lstrip("@").lower()
    session = _build_session(cookies)

    # Paso 1: obtener csrf token visitando Instagram
    _extract_csrf(session)
    _delay()

    # Paso 2: datos del perfil
    profile = fetch_profile(username, session)
    if "error" in profile:
        return {"success": False, "error": profile["error"]}

    # Paso 3: posts de la primera página (ya vienen en la respuesta del perfil)
    posts = [_parse_post(e) for e in profile.pop("_initial_posts", [])]
    end_cursor = profile.pop("_end_cursor", "")
    has_next = profile.pop("_has_next_page", False)

    # Paso 4: paginar con GraphQL hasta llegar a max_posts
    while len(posts) < max_posts and has_next and end_cursor and profile.get("id"):
        _delay()
        needed = max_posts - len(posts)
        result = fetch_posts_graphql(
            profile["id"], end_cursor, session, count=min(needed, 12)
        )

        if "error" in result:
            # Registramos el error pero no abortamos — devolvemos lo que tenemos
            profile["_pagination_error"] = result["error"]
            break

        new_posts = [_parse_post(e) for e in result.get("edges", [])]
        posts.extend(new_posts)
        end_cursor = result.get("end_cursor", "")
        has_next = result.get("has_next_page", False)

    # Paso 5: construir objeto final
    output = {
        **profile,
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "posts_requested": max_posts,
        "posts_retrieved": len(posts[:max_posts]),
        "posts": posts[:max_posts],
    }

    # Guardar en disco
    out_path = os.path.join(DATA_DIR, f"{username}_profile.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return {"success": True, "data": output, "file": out_path}


# ── Ejecución directa desde CLI ───────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    user = sys.argv[1] if len(sys.argv) > 1 else input("Usuario de Instagram: ")
    n    = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    print(f"\n→ Scrapeando @{user} ({n} posts)...\n")
    result = scrape(user, n)
    if result["success"]:
        d = result["data"]
        print(f"✓ {d['full_name']} (@{d['username']})")
        print(f"  Seguidores : {d['followers']:,}")
        print(f"  Posts total: {d['posts_count']:,}")
        print(f"  Extraídos  : {d['posts_retrieved']}")
        print(f"  Guardado en: {result['file']}\n")
    else:
        print(f"✗ Error: {result['error']}\n")
