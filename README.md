# 📲 Contenido en automático: Instagram + TikTok

Dejás imágenes en la carpeta **`pendientes/`** y el sistema publica **4 por día**, solo, en Instagram y TikTok.
Corre gratis en GitHub. No necesitás computadora ni tener el celular prendido.

## Cómo se publica (elegí uno)

| Camino | Instagram | TikTok | Costo | Configuración |
|---|---|---|---|---|
| **⭐ Buffer (recomendado)** | ✅ | ✅ | **Gratis** | 5 min desde el celu |
| API de Meta | ✅ | — | Gratis | Necesita computadora una vez |
| Upload-Post | ✅ | ✅ | USD 24/mes | 5 min desde el celu |

**Con Buffer gratis:** GitHub guarda tus imágenes y le pasa una a Buffer en cada horario con la orden "publicar ya".
Buffer las publica en tu Instagram y tu TikTok. El plan gratis de Buffer permite 3 redes y 10 posts en cola por red;
como el sistema le manda las fotos de a una y en el momento, ese límite no te afecta.

---

## Cómo funciona

1. En cada horario, GitHub agarra la **primera imagen** de `pendientes/` (en orden alfabético: `001`, `002`…).
2. La adapta sola: la pasa a JPG, la deja en el tamaño correcto y, si es muy vertical, le pone un fondo desenfocado
   para no recortarla.
3. La publica con el texto que le toque y la mueve a `publicadas/`. Todo queda anotado en `registro.csv`.
4. Si algo falla, **GitHub te manda un email**. La imagen se reintenta una vez; si vuelve a fallar, queda en `con_error/`.
5. Cuando quedan 8 o menos imágenes te avisa. Si la carpeta se vacía, te llega un email de error para que cargues más.

**Horarios (hora de Montevideo):** 09:07 · 13:07 · 18:07 · 21:07. GitHub a veces arranca entre 5 y 30 min tarde; es normal.

---

## ⭐ Configuración con Buffer (gratis, todo desde el celular)

### 1. Instagram profesional
En la app de Instagram: **Configuración → Tipo de cuenta y herramientas → Cambiar a cuenta profesional**
(Creador o Empresa). Es gratis y Buffer lo necesita para publicar solo.

### 2. Crear la cuenta de Buffer y conectar tus redes
1. Bajá la app **Buffer** (App Store / Play Store) o entrá a **buffer.com**, y creá una cuenta gratis.
2. Tocá **"Connect channel"** (conectar canal), elegí **Instagram** e iniciá sesión. Repetí lo mismo con **TikTok**.
3. Si Buffer te ofrece "notificaciones para publicar", elegí **publicación automática** (Automatic publishing).

### 3. Sacar la clave de API de Buffer
1. En el navegador del celu entrá a **publish.buffer.com/settings/api** con tu cuenta de Buffer.
   Si no se ve bien, usá **"Solicitar sitio de escritorio"**.
2. Tocá **"Generate API key"** (o "Create key"), ponele un nombre como `github` y **copiá la clave**.
   Ojo: se muestra una sola vez.

### 4. Guardar la clave en GitHub
En este repo: **Settings → Secrets and variables → Actions → New repository secret**
- Name: `BUFFER_API_KEY`
- Secret: pegá la clave → **Add secret**

### 5. Probar
1. Subí una imagen a `pendientes/` (cómo hacerlo está más abajo).
2. Andá a la pestaña **Actions → Publicar imagen → Run workflow**.
   - *Modo prueba = si*: hace todo menos publicar. Sirve para ver que no haya errores.
   - *Modo prueba = no*: publica de verdad.
3. Tocá la ejecución para ver qué pasó. ✅ verde = publicado. Revisá tu Instagram y tu TikTok.

¡Listo! Desde ahí funciona solo.

> Si en Buffer tenés conectada otra red (por ejemplo Facebook) y también querés publicar ahí, creá una variable
> `BUFFER_REDES` con el valor `instagram,tiktok,facebook` (ver "Ajustes" más abajo).

---

## Uso diario: cargar imágenes desde el celular

1. Abrí el repo en el navegador y entrá a la carpeta **`pendientes`**.
2. Tocá **Add file → Upload files** y elegí las fotos de la galería (hasta 100 por vez).
   Si no ves "Add file", activá **"Solicitar sitio de escritorio"**.
3. Abajo, tocá **Commit changes**. Listo.

Se publican en **orden alfabético**. Para controlar el orden exacto, nombralas `001.jpg`, `002.jpg`…
Las fotos del celu ya vienen como `IMG_1234`, así que salen en el orden en que las sacaste.

Con 4 por día: **28 imágenes = 1 semana · 120 imágenes = 1 mes.**

### Textos de los posts
- Editá **`textos.txt`** y separá cada texto con una línea `---`. Se van usando en ronda.
- ¿Querés un texto especial para una foto? Subí un `.txt` con el **mismo nombre** (`foto7.jpg` + `foto7.txt`).

---

## Ajustes (Settings → Secrets and variables → Actions → pestaña Variables)

| Variable | Para qué sirve | Valor por defecto |
|---|---|---|
| `IMAGENES_POR_EJECUCION` | Cuántas imágenes publica en cada horario | `1` |
| `BUFFER_REDES` | En qué redes de Buffer publica | `instagram,tiktok` |
| `AVISAR_CUANDO_QUEDEN` | Cuándo te avisa que quedan pocas | `8` |

**Cambiar horarios:** editá `.github/workflows/publicar.yml`, en la línea `cron: "7 0,12,16,21 * * *"`.
Las horas van en UTC, que es Montevideo + 3. Por ejemplo, para las 10, 14, 19 y 22 h de Montevideo: `"7 1,13,17,22 * * *"`.

---

## Si algo falla

| Mensaje | Qué hacer |
|---|---|
| *La clave de Buffer no funciona* | Generá otra clave (paso 3) y reemplazá el secret `BUFFER_API_KEY`. |
| *No encontré canales… conectados en Buffer* | En Buffer, reconectá Instagram o TikTok y fijate que la cola no esté en pausa. |
| *Buffer instagram/tiktok falló* | Leé el mensaje en Actions. Suele ser que hay que reconectar la red en Buffer. |
| *La carpeta pendientes/ está vacía* | Subí más imágenes. |
| Imagen en `con_error/` | Falló 2 veces. Cuando lo arregles, movela de nuevo a `pendientes/`. |

Si Buffer acepta el post pero después no aparece en la red, Buffer te avisa por email o en su app. Casi siempre se
arregla reconectando la cuenta.

---

## Caminos alternativos (opcionales)

### API de Meta para Instagram (gratis, sin Buffer)
Hay que hacerlo **desde una computadora**, porque el panel de Meta no anda bien en el celular.

1. En **developers.facebook.com/apps** → **Crear app**, elegí el caso de uso
   "Administrar mensajes y contenido en Instagram" y "No conectar portfolio".
2. Andá a **Casos de uso → Personalizar → Configuración de la API con inicio de sesión de Instagram →
   Generar tokens de acceso → Agregar cuenta**, y después **Generar token**.
3. Guardá el token como secret **`IG_ACCESS_TOKEN`**.
4. Como el token vence a los 60 días, preparalo para que se renueve solo: en
   **github.com/settings/personal-access-tokens/new** creá un token con acceso solo a este repo y con el permiso
   **Secrets: Read and write**, y guardalo como secret **`GH_PAT`**.

Si cargás `IG_ACCESS_TOKEN`, Instagram sale por Meta y Buffer se usa solo para TikTok, así nada se publica dos veces.

### Upload-Post (pago)
En **app.upload-post.com** (plan Basic): creá un perfil, conectá TikTok y/o Instagram y generá una API key.
- Secret `UPLOADPOST_API_KEY` = la key
- Variable `UPLOADPOST_USER` = el nombre del perfil
- Variable `UPLOADPOST_PLATAFORMAS` = `tiktok` o `tiktok,instagram`

Las redes que ya salen por Buffer no se publican de nuevo por Upload-Post.

---

Límites de cada red: Instagram acepta 50–100 posts por día por API y TikTok unos 15 por día. Con 4 estás lejísimos.
