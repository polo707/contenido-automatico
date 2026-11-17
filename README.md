# 📲 Contenido en automático: Instagram + TikTok

Dejás imágenes en la carpeta **`pendientes/`** y el sistema publica **4 por día**, solo, en Instagram y TikTok.
Todo corre gratis en GitHub (GitHub Actions). No necesitás computadora ni tener el celular prendido.

| Qué | Cómo | Costo |
|---|---|---|
| Instagram | API oficial de Meta, directo | **Gratis** (hasta 50–100 posts/día) |
| TikTok | Upload-Post (app ya aprobada por TikTok) | **USD 24/mes** (o 16/mes pagando el año) |
| Servidor | GitHub Actions | **Gratis** |

> **¿Por qué TikTok no es gratis?** TikTok obliga a que cualquier app nueva pase una auditoría; hasta entonces
> todo lo que publica queda **privado (solo vos lo ves)**. Upload-Post ya pasó esa auditoría, por eso sus posts salen públicos.
> Si no querés pagar, usá solo Instagram: TikTok es opcional.

---

## Cómo funciona

1. Cada horario, GitHub agarra la **primera imagen** de `pendientes/` (orden alfabético: `001`, `002`…).
2. La adapta sola: a JPG, tamaño correcto, y si es muy vertical le pone un fondo desenfocado (nada se recorta).
   Para TikTok arma una versión vertical 9:16.
3. La publica con el texto que le toque y la mueve a `publicadas/`. Todo queda anotado en `registro.csv`.
4. Si algo falla, **GitHub te manda un email**. La imagen se reintenta una vez; si vuelve a fallar queda en `con_error/`.
5. Cuando quedan 8 o menos imágenes te avisa; cuando la carpeta queda vacía, te llega un email de error para que cargues más.

**Horarios (hora de Montevideo):** 09:07 · 13:07 · 18:07 · 21:07
(GitHub a veces arranca 5–30 min tarde; es normal.)

---

## Configuración (una sola vez, ~20 min, todo desde el celular)

### Paso 1 — Instagram como cuenta profesional
En la app de Instagram: **Configuración → Tipo de cuenta y herramientas → Cambiar a cuenta profesional** (Creador o Empresa). Es gratis.

### Paso 2 — El repositorio
Este repo tiene que ser **público** (Instagram necesita poder descargar la imagen desde un link).
Las claves NO quedan públicas: van guardadas en *Secrets*, que nadie más puede ver.

### Paso 3 — Token de Instagram (gratis)
Desde el navegador del celu (si algo no aparece, activá **"Ver versión de escritorio"**):

1. Entrá a **developers.facebook.com** con tu cuenta de Facebook → **Mis apps → Crear app**.
2. Nombre: lo que quieras (ej. *Publicador*). Caso de uso: **"Administrar mensajes y contenido en Instagram"**.
   Si te pide portfolio comercial, elegí *"No quiero conectar un portfolio"*. Creá la app.
3. En el menú de la app: **Casos de uso → Personalizar → Configuración de la API con inicio de sesión de Instagram**.
4. En **"Generar tokens de acceso"** tocá **Agregar cuenta**, entrá con tu Instagram y aceptá los permisos.
   - Si te dice que primero aceptes una invitación de evaluador: en Instagram andá a
     **instagram.com/accounts/manage_access → Invitaciones de evaluador → Aceptar**, y volvé a intentar.
5. Tocá **Generar token** al lado de tu cuenta y **copialo entero** (es un texto largo que empieza con `IG…`).

La app se queda en "modo desarrollo": está bien así, porque solo la usás vos con tu propia cuenta.

### Paso 4 — Guardar el token en GitHub
En este repo: **Settings → Secrets and variables → Actions → New repository secret**
- Name: `IG_ACCESS_TOKEN`
- Secret: pegá el token → **Add secret**

### Paso 5 — Renovación automática del token
El token de Instagram vence a los 60 días. Para que se renueve solo cada semana:

1. Entrá a **github.com/settings/personal-access-tokens/new**
2. Nombre: `renovar-instagram` · Expiración: la más larga que te deje.
3. **Repository access → Only select repositories →** este repo.
4. **Permissions → Repository permissions → Secrets → Read and write.**
5. **Generate token**, copialo y guardalo como secret nuevo (igual que en el paso 4) con el nombre **`GH_PAT`**.

Si te saltás este paso, cada ~55 días vas a tener que repetir los pasos 3 y 4.

### Paso 6 — TikTok (opcional, pago)
1. Creá cuenta en **app.upload-post.com** y elegí el plan **Basic** (el gratis no incluye TikTok).
2. **Manage Users → crear un perfil** (ej. `pablo`) y conectale tu **TikTok**.
3. **API Keys →** creá una y copiala.
4. En GitHub, **Settings → Secrets and variables → Actions**:
   - Pestaña **Secrets** → New: `UPLOADPOST_API_KEY` = la key.
   - Pestaña **Variables** → New: `UPLOADPOST_USER` = el nombre del perfil (ej. `pablo`).

> ¿Preferís no lidiar con Meta? Podés mandar **también Instagram por Upload-Post**: conectá Instagram en el mismo
> perfil, no cargues `IG_ACCESS_TOKEN` y creá la variable `UPLOADPOST_PLATAFORMAS` = `tiktok,instagram`.

### Paso 7 — Probar
1. Subí 1 imagen a `pendientes/` (ver abajo).
2. Pestaña **Actions → Publicar imagen → Run workflow**.
   - Con *Modo prueba = si* hace todo menos publicar (sirve para ver que no haya errores).
   - Con *Modo prueba = no* publica de verdad.
3. Tocá la ejecución para ver qué pasó. ✅ verde = publicado.

---

## Uso diario: cargar imágenes desde el celular

1. Abrí el repo en el navegador → carpeta **`pendientes`**.
2. **Add file → Upload files** → elegí las fotos de la galería (hasta 100 por vez).
3. Abajo, **Commit changes**. Listo.

Se publican en **orden alfabético**. Si querés controlar el orden exacto, nombralas `001.jpg`, `002.jpg`…
(Las fotos del celu ya vienen como `IMG_1234`, así que salen en el orden en que las sacaste.)

Con 4 por día: **28 imágenes = 1 semana · 120 imágenes = 1 mes.**

### Textos de los posts
- Editá **`textos.txt`**: separá cada texto con una línea `---`. Se usan en ronda.
- ¿Texto especial para una foto? Subí un `.txt` con el **mismo nombre** (`foto7.jpg` + `foto7.txt`).
- En TikTok la primera línea va como título (máx. 90 letras) y el texto completo como descripción.

---

## Ajustes (Settings → Secrets and variables → Actions → Variables)

| Variable | Para qué | Por defecto |
|---|---|---|
| `IMAGENES_POR_EJECUCION` | Cuántas publica en cada horario | `1` |
| `TIKTOK_MUSICA` | TikTok le agrega música sola (`si`/`no`) | `si` |
| `UPLOADPOST_PLATAFORMAS` | Redes vía Upload-Post (`tiktok`, `instagram`, `facebook`…) | `tiktok` |
| `AVISAR_CUANDO_QUEDEN` | Aviso de "quedan pocas" | `8` |

**Cambiar horarios:** editá `.github/workflows/publicar.yml`, línea `cron: "7 0,12,16,21 * * *"`.
Son horas UTC (Montevideo + 3). Ejemplo para 10, 14, 19 y 22 h de Montevideo: `"7 1,13,17,22 * * *"`.

---

## Si algo falla

| Mensaje | Qué hacer |
|---|---|
| *El token de Instagram no funciona* | Repetí pasos 3 y 4. Revisá que el paso 5 esté hecho. |
| *La carpeta pendientes/ está vacía* | Subí más imágenes. |
| *Upload-Post falló* | Mirá en app.upload-post.com que TikTok siga conectado y el plan activo. |
| Imagen en `con_error/` | Falló 2 veces. Movela de nuevo a `pendientes/` cuando lo arregles. |

Límites a tener en cuenta: Instagram permite 50–100 posts por día por API y TikTok ~15 por día. Con 4 estás lejísimos.
