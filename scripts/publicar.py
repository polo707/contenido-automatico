#!/usr/bin/env python3
"""
Publica automáticamente la próxima imagen de la carpeta `pendientes/`
en Instagram y TikTok. Destinos posibles (se usan los que tengan clave cargada):
  - Buffer (plan gratis)          -> Instagram + TikTok
  - API oficial de Meta (gratis)  -> Instagram
  - Upload-Post (pago)            -> TikTok y otras

Lo ejecuta GitHub Actions según el horario de .github/workflows/publicar.yml.
No hace falta tocar este archivo: todo se configura con Secrets y Variables
del repositorio (ver README.md).
"""

import csv
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

import requests
from PIL import Image, ImageFilter, ImageOps

try:  # fotos HEIC de iPhone
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:  # pragma: no cover
    pass

# ---------------------------------------------------------------- rutas
RAIZ = pathlib.Path(__file__).resolve().parent.parent
PENDIENTES = RAIZ / "pendientes"
PUBLICADAS = RAIZ / "publicadas"
CON_ERROR = RAIZ / "con_error"
TEXTOS = RAIZ / "textos.txt"
ESTADO = RAIZ / "estado.json"
REGISTRO = RAIZ / "registro.csv"
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".gif", ".tif", ".tiff"}

# ---------------------------------------------------------------- configuración
def _env(nombre, defecto=""):
    return (os.getenv(nombre) or defecto).strip()


IG_TOKEN = _env("IG_ACCESS_TOKEN")
BUFFER_KEY = _env("BUFFER_API_KEY")
BUFFER_REDES = [p.strip().lower() for p in _env("BUFFER_REDES", "instagram,tiktok").split(",") if p.strip()]
UP_KEY = _env("UPLOADPOST_API_KEY")
UP_USER = _env("UPLOADPOST_USER")
UP_PLATAFORMAS = [p.strip().lower() for p in _env("UPLOADPOST_PLATAFORMAS", "tiktok").split(",") if p.strip()]
TIKTOK_MUSICA = _env("TIKTOK_MUSICA", "si").lower() in ("si", "sí", "true", "1", "yes")
POR_EJECUCION = max(1, int(_env("IMAGENES_POR_EJECUCION", "1") or "1"))
MODO_PRUEBA = _env("MODO_PRUEBA", "no").lower() in ("si", "sí", "true", "1", "yes")
AVISO_POCAS = int(_env("AVISAR_CUANDO_QUEDEN", "8") or "8")
REPO = _env("GITHUB_REPOSITORY")
API_IG = "https://graph.instagram.com/v26.0"
API_UP = "https://api.upload-post.com/api/upload_photos"
API_BUFFER = "https://api.buffer.com"

# Evitar publicar dos veces en la misma red:
# prioridad Instagram -> 1) API de Meta  2) Buffer  3) Upload-Post
#           TikTok    -> 1) Buffer       2) Upload-Post
if IG_TOKEN and "instagram" in BUFFER_REDES:
    BUFFER_REDES.remove("instagram")
USAR_BUFFER = bool(BUFFER_KEY and BUFFER_REDES)
if IG_TOKEN and "instagram" in UP_PLATAFORMAS:
    UP_PLATAFORMAS.remove("instagram")
USAR_UPLOADPOST = bool(UP_KEY and UP_USER and UP_PLATAFORMAS)


def log(msg):
    print(msg, flush=True)


def aviso(msg):
    # Aparece resaltado en el resumen de GitHub Actions
    print(f"::warning::{msg}", flush=True)


def error(msg):
    print(f"::error::{msg}", flush=True)


# ---------------------------------------------------------------- git
def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=RAIZ, check=check, capture_output=True, text=True).stdout.strip()


def guardar_en_repo(mensaje):
    """Commit + push, reintentando por si subiste fotos mientras corría."""
    if MODO_PRUEBA:
        log(f"[prueba] commit: {mensaje}")
        return "PRUEBA"
    git("add", "-A")
    if git("status", "--porcelain"):
        git("commit", "-m", mensaje)
    for intento in range(5):
        git("pull", "--rebase", "--autostash", check=False)
        r = subprocess.run(["git", "push"], cwd=RAIZ, capture_output=True, text=True)
        if r.returncode == 0:
            return git("rev-parse", "HEAD")
        log(f"push falló (intento {intento + 1}): {r.stderr.strip()}")
        time.sleep(5 * (intento + 1))
    raise RuntimeError("No se pudo hacer push al repositorio")


# ---------------------------------------------------------------- estado / textos
def leer_estado():
    if ESTADO.exists():
        try:
            return json.loads(ESTADO.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"indice_texto": 0, "fallos": {}}


def escribir_estado(estado):
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def textos_disponibles():
    if not TEXTOS.exists():
        return []
    contenido = TEXTOS.read_text(encoding="utf-8")
    lineas = [l for l in contenido.splitlines() if not l.lstrip().startswith("#")]
    bloques = re.split(r"^\s*---\s*$", "\n".join(lineas), flags=re.M)
    return [b.strip() for b in bloques if b.strip()]


def orden_natural(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def imagenes_pendientes():
    if not PENDIENTES.exists():
        return []
    return sorted(
        (p for p in PENDIENTES.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONES),
        key=orden_natural,
    )


# ---------------------------------------------------------------- imágenes
def _con_fondo(im, ancho, alto):
    """Centra la imagen sobre un fondo desenfocado de ella misma."""
    fondo = ImageOps.fit(im, (ancho, alto), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
    copia = im.copy()
    copia.thumbnail((ancho, alto), Image.LANCZOS)
    fondo.paste(copia, ((ancho - copia.width) // 2, (alto - copia.height) // 2))
    return fondo


def abrir_rgb(origen):
    im = Image.open(origen)
    if getattr(im, "is_animated", False):
        im.seek(0)
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        blanco = Image.new("RGB", im.size, (255, 255, 255))
        blanco.paste(im, mask=im.split()[-1])
        return blanco
    return im.convert("RGB")


def guardar_jpg(im, destino):
    calidad = 92
    while True:
        im.save(destino, "JPEG", quality=calidad, optimize=True, progressive=True)
        if destino.stat().st_size <= 7_500_000 or calidad <= 60:
            return
        calidad -= 8


def version_instagram(im, destino):
    """Instagram exige JPEG, proporción entre 4:5 y 1.91:1 y 320–1440 px de ancho.
    Usamos 1080 de ancho máximo: es lo que recomienda Instagram y TikTok no acepta más de 1080p."""
    w, h = im.size
    r = w / h
    if r < 0.8:  # muy vertical (ej. 9:16) -> lienzo 4:5 sin recortar
        im = _con_fondo(im, round(h * 0.8), h)
    elif r > 1.91:  # muy horizontal -> lienzo 1.91:1
        im = _con_fondo(im, w, round(w / 1.91))
    if im.width > 1080:
        im = im.resize((1080, round(im.height * 1080 / im.width)), Image.LANCZOS)
    if im.width < 320:
        im = im.resize((320, round(im.height * 320 / im.width)), Image.LANCZOS)
    guardar_jpg(im, destino)


def version_tiktok(im, destino):
    """TikTok muestra fotos en vertical: lienzo 9:16 (1080x1920) sin recortar."""
    w, h = im.size
    if abs(w / h - 9 / 16) > 0.02:
        im = _con_fondo(im, 1080, 1920)
    else:
        im = im.resize((1080, 1920), Image.LANCZOS)
    guardar_jpg(im, destino)


# ---------------------------------------------------------------- Instagram
def ig_verificar():
    r = requests.get(f"{API_IG}/me", params={"fields": "user_id,username", "access_token": IG_TOKEN}, timeout=30)
    datos = r.json() if r.content else {}
    if r.status_code != 200 or "user_id" not in datos:
        raise RuntimeError(f"El token de Instagram no funciona (¿vencido?). Respuesta: {datos}")
    log(f"Instagram conectado: @{datos.get('username')}")
    return datos["user_id"]


def ig_publicar(ig_id, urls, caption):
    ultimo_error = None
    for url in urls:
        log(f"Instagram: creando post con {url}")
        r = requests.post(
            f"{API_IG}/{ig_id}/media",
            data={"image_url": url, "caption": caption, "access_token": IG_TOKEN},
            timeout=120,
        )
        datos = r.json()
        if "id" not in datos:
            ultimo_error = datos
            log(f"  no aceptó esa URL: {datos}")
            continue
        contenedor = datos["id"]
        for _ in range(30):  # espera hasta ~2.5 min
            est = requests.get(
                f"{API_IG}/{contenedor}", params={"fields": "status_code", "access_token": IG_TOKEN}, timeout=30
            ).json()
            codigo = est.get("status_code")
            if codigo == "FINISHED":
                break
            if codigo in ("ERROR", "EXPIRED"):
                ultimo_error = est
                break
            time.sleep(5)
        else:
            ultimo_error = {"error": "Instagram tardó demasiado en procesar la imagen"}
            continue
        if est.get("status_code") != "FINISHED":
            continue
        pub = requests.post(
            f"{API_IG}/{ig_id}/media_publish",
            data={"creation_id": contenedor, "access_token": IG_TOKEN},
            timeout=120,
        ).json()
        if "id" in pub:
            link = ""
            try:
                link = requests.get(
                    f"{API_IG}/{pub['id']}", params={"fields": "permalink", "access_token": IG_TOKEN}, timeout=30
                ).json().get("permalink", "")
            except Exception:
                pass
            return f"OK {link or pub['id']}"
        ultimo_error = pub
    raise RuntimeError(f"Instagram falló: {ultimo_error}")


# ---------------------------------------------------------------- Upload-Post (TikTok y otras)
def uploadpost_publicar(archivo, caption):
    datos = [("user", UP_USER), ("title", caption[:2200])]
    datos += [("platform[]", p) for p in UP_PLATAFORMAS]
    if "tiktok" in UP_PLATAFORMAS:
        primera_linea = caption.strip().splitlines()[0] if caption.strip() else ""
        datos += [
            ("tiktok_title", primera_linea[:90]),
            ("tiktok_description", caption[:4000]),
            ("privacy_level", "PUBLIC_TO_EVERYONE"),
            ("auto_add_music", "true" if TIKTOK_MUSICA else "false"),
        ]
    with open(archivo, "rb") as f:
        r = requests.post(
            API_UP,
            headers={"Authorization": f"Apikey {UP_KEY}"},
            data=datos,
            files=[("photos[]", (archivo.name, f, "image/jpeg"))],
            timeout=600,
        )
    try:
        resp = r.json()
    except Exception:
        resp = {"texto": r.text[:500]}
    log(f"Upload-Post respondió ({r.status_code}): {json.dumps(resp, ensure_ascii=False)[:1500]}")
    if r.status_code >= 300 or resp.get("success") is False:
        raise RuntimeError(f"Upload-Post falló ({r.status_code}): {resp}")
    return "OK"


# ---------------------------------------------------------------- Buffer (gratis: Instagram + TikTok)
CREAR_POST = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    __typename
    ... on PostActionSuccess { post { id status } }
    ... on MutationError { message }
  }
}"""


def buffer_gql(query, variables=None):
    r = requests.post(
        API_BUFFER,
        headers={
            "Authorization": f"Bearer {BUFFER_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (publicador-automatico)",
        },
        json={"query": query, "variables": variables or {}},
        timeout=60,
    )
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"errors": [{"message": r.text[:300]}]}


def buffer_canales():
    """Devuelve los canales de Buffer (Instagram/TikTok) donde hay que publicar."""
    codigo, datos = buffer_gql("query { account { organizations { id name } } }")
    orgs = (((datos or {}).get("data") or {}).get("account") or {}).get("organizations") or []
    if codigo != 200 or not orgs:
        raise RuntimeError(f"La clave de Buffer no funciona. Respuesta ({codigo}): {datos}")
    canales = []
    for org in orgs:
        codigo, datos = buffer_gql(
            "query($o: OrganizationId!) { channels(input: {organizationId: $o}) { id name service isQueuePaused } }",
            {"o": org["id"]},
        )
        if "errors" in datos:  # por si el tipo del parámetro cambia de nombre
            codigo, datos = buffer_gql(
                'query { channels(input: {organizationId: "%s"}) { id name service isQueuePaused } }' % org["id"]
            )
        for c in ((datos.get("data") or {}).get("channels") or []):
            servicio = (c.get("service") or "").lower()
            if servicio in BUFFER_REDES and not c.get("isQueuePaused"):
                canales.append(c)
    if not canales:
        raise RuntimeError(f"No encontré canales de {', '.join(BUFFER_REDES)} conectados en Buffer (o tienen la cola pausada).")
    log("Buffer conectado: " + ", ".join(f"{c['service']} ({c['name']})" for c in canales))
    return canales


def buffer_publicar(canales, url, caption):
    resultados, errores = [], []
    for canal in canales:
        servicio = canal["service"].lower()
        base = {"channelId": canal["id"], "text": caption, "schedulingType": "automatic",
                "assets": [{"image": {"url": url}}]}
        meta = {"instagram": {"type": "post", "shouldShareToFeed": True}} if servicio == "instagram" else None
        en_2_min = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Probamos primero "publicar ya"; si la API no acepta alguna opción, vamos con variantes más simples.
        variantes = []
        for modo in ({"mode": "shareNow"}, {"mode": "customScheduled", "dueAt": en_2_min}):
            if meta:
                variantes.append({**base, **modo, "metadata": meta})
            variantes.append({**base, **modo})
        ultimo = None
        for entrada in variantes:
            codigo, datos = buffer_gql(CREAR_POST, {"input": entrada})
            res = (datos.get("data") or {}).get("createPost") or {}
            if res.get("__typename") == "PostActionSuccess":
                resultados.append(f"{servicio} OK")
                log(f"Buffer {servicio}: OK ({entrada['mode']}) post {res['post']['id']}")
                break
            ultimo = res.get("message") or datos.get("errors") or datos
            log(f"Buffer {servicio}: intento sin éxito -> {ultimo}")
        else:
            resultados.append(f"{servicio} ERROR")
            errores.append(f"Buffer {servicio} falló: {ultimo}")
    return " | ".join(resultados), errores


# ---------------------------------------------------------------- flujo principal
def registrar(fila):
    nuevo = not REGISTRO.exists()
    with open(REGISTRO, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha_utc", "archivo", "instagram_directo", "buffer", "uploadpost"])
        w.writerow(fila)


def publicar_una(estado, ig_id, canales_buffer=None):
    pendientes = imagenes_pendientes()
    if not pendientes:
        return None
    original = pendientes[0]
    txt_propio = original.with_suffix(".txt")
    if not txt_propio.exists():
        txt_propio = next((p for p in PENDIENTES.glob(original.stem + ".*") if p.suffix.lower() == ".txt"), None)

    # ---- texto del post
    if txt_propio and txt_propio.exists():
        caption, origen_texto = txt_propio.read_text(encoding="utf-8").strip(), "propio"
    else:
        lista = textos_disponibles()
        if lista:
            caption = lista[estado.get("indice_texto", 0) % len(lista)]
            origen_texto = "rotacion"
        else:
            caption, origen_texto = "", "vacio"

    log(f"\n=== Publicando: {original.name} (quedan {len(pendientes) - 1} después de esta) ===")
    log(f"Texto ({origen_texto}): {caption[:120]!r}")

    # ---- preparar imágenes
    marca = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M")
    nombre_limpio = re.sub(r"[^A-Za-z0-9._-]+", "-", original.stem).strip("-") or "imagen"
    PUBLICADAS.mkdir(exist_ok=True)
    destino_ig = PUBLICADAS / f"{marca}_{nombre_limpio}.jpg"
    im = abrir_rgb(original)
    version_instagram(im, destino_ig)
    tmp_tiktok = pathlib.Path(tempfile.mkdtemp()) / f"{nombre_limpio}.jpg"
    version_tiktok(im, tmp_tiktok)

    # ---- sacar de la cola y subir la versión lista (Instagram necesita una URL pública)
    original.unlink()
    if txt_propio and txt_propio.exists():
        txt_propio.unlink()
    sha = guardar_en_repo(f"Publicando {original.name}")
    ruta = destino_ig.relative_to(RAIZ).as_posix()
    urls = [
        f"https://cdn.jsdelivr.net/gh/{REPO}@{sha}/{ruta}",
        f"https://raw.githubusercontent.com/{REPO}/{sha}/{ruta}",
    ]

    resultado_ig = resultado_bf = resultado_up = "-"
    errores = []
    if ig_id:
        try:
            resultado_ig = "PRUEBA" if MODO_PRUEBA else ig_publicar(ig_id, urls, caption)
            log(f"Instagram: {resultado_ig}")
        except Exception as e:
            resultado_ig = "ERROR"
            errores.append(str(e))
            error(str(e))
    if canales_buffer:
        if MODO_PRUEBA:
            resultado_bf = "PRUEBA"
        else:
            try:
                resultado_bf, errs = buffer_publicar(canales_buffer, urls[0], caption)
                errores += errs
                for e in errs:
                    error(e)
            except Exception as e:
                resultado_bf = "ERROR"
                errores.append(str(e))
                error(str(e))
    if USAR_UPLOADPOST:
        try:
            resultado_up = "PRUEBA" if MODO_PRUEBA else uploadpost_publicar(tmp_tiktok, caption)
            log(f"{', '.join(UP_PLATAFORMAS)}: {resultado_up}")
        except Exception as e:
            resultado_up = "ERROR"
            errores.append(str(e))
            error(str(e))

    algo_salio = any("OK" in r for r in (resultado_ig, resultado_bf, resultado_up)) or MODO_PRUEBA
    base = original.stem.removeprefix("000_reintento_")
    fallos = estado.setdefault("fallos", {})
    if algo_salio:
        if origen_texto == "rotacion":
            estado["indice_texto"] = estado.get("indice_texto", 0) + 1
        fallos.pop(base, None)
    else:
        # Nada se publicó: se reintenta una vez; si vuelve a fallar va a con_error/
        fallos[base] = fallos.get(base, 0) + 1
        if fallos[base] >= 2:
            CON_ERROR.mkdir(exist_ok=True)
            destino_ig.rename(CON_ERROR / f"{base}.jpg")
            fallos.pop(base, None)
            aviso(f"{original.name} falló 2 veces; quedó en con_error/")
        else:
            nuevo = PENDIENTES / f"000_reintento_{base}.jpg"
            destino_ig.rename(nuevo)
            if origen_texto == "propio":
                nuevo.with_suffix(".txt").write_text(caption, encoding="utf-8")
            aviso(f"{original.name} no se pudo publicar; se reintenta en la próxima ejecución")

    registrar([dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), original.name, resultado_ig, resultado_bf, resultado_up])
    escribir_estado(estado)
    guardar_en_repo(f"Publicada {original.name} (IG directo: {resultado_ig.split()[0]}, Buffer: {resultado_bf}, Upload-Post: {resultado_up})")
    return errores


def main():
    global USAR_UPLOADPOST
    if not IG_TOKEN and not USAR_BUFFER and not USAR_UPLOADPOST:
        error("No hay ningún destino configurado. Cargá el secret BUFFER_API_KEY (gratis), "
              "o IG_ACCESS_TOKEN, o UPLOADPOST_API_KEY + UPLOADPOST_USER. Ver README.")
        return 1

    # Verificamos las claves ANTES de tocar las imágenes, así una clave vencida no gasta fotos.
    canales_buffer = None
    if USAR_BUFFER:
        try:
            canales_buffer = ([{"id": "x", "name": "prueba", "service": s} for s in BUFFER_REDES]
                              if MODO_PRUEBA else buffer_canales())
            cubiertas = {c["service"].lower() for c in canales_buffer}
            for red in cubiertas & set(UP_PLATAFORMAS):
                UP_PLATAFORMAS.remove(red)  # ya sale por Buffer
            USAR_UPLOADPOST = bool(UP_KEY and UP_USER and UP_PLATAFORMAS)
        except Exception as e:
            error(str(e))
            if not IG_TOKEN and not USAR_UPLOADPOST:
                return 1

    ig_id = None
    if IG_TOKEN:
        try:
            ig_id = "PRUEBA" if MODO_PRUEBA else ig_verificar()
        except Exception as e:
            error(str(e))
            if not canales_buffer and not USAR_UPLOADPOST:
                return 1
            aviso("Sigo con los otros destinos.")

    estado = leer_estado()
    todos_errores = []
    publicadas = 0
    for _ in range(POR_EJECUCION):
        errores = publicar_una(estado, ig_id, canales_buffer)
        if errores is None:
            break
        publicadas += 1
        todos_errores += errores

    quedan = len(imagenes_pendientes())
    if publicadas == 0:
        error("La carpeta pendientes/ está vacía: subí más imágenes.")
        return 1
    if quedan <= AVISO_POCAS:
        aviso(f"Quedan solo {quedan} imágenes en pendientes/. ¡Subí más!")
    log(f"\nListo. Publicadas en esta ejecución: {publicadas}. Quedan: {quedan}.")
    return 1 if todos_errores else 0


if __name__ == "__main__":
    sys.exit(main())
