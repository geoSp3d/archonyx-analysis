# Archonyx, De un bot autenticado a RCE

Análisis técnico y reproducción de **Archonyx**, un reto Web Medium de Cyber Apocalypse CTF 2026: The Salt Crown.

La resolución no dependía de una vulnerabilidad aislada, sino de encadenar cuatro capacidades:

1. utilizar mediante CSRF la sesión de un bot autenticado;
2. convertir una extracción TAR en sobrescritura arbitraria de archivos;
3. transformar esa escritura en acceso privilegiado como `ledgermaster`;
4. cargar JavaScript local mediante el sistema de plugins de LESS.

![Cadena de explotación de Archonyx](assets/archonyx-chain.png)

## Cadena resumida

```text
/report
→ bot autenticado
→ CSRF contra /api/fetch
→ TAR extraído antes de validarse
→ hardlink absoluto
→ inode compartido y truncado
→ sobrescritura de db.json
→ acceso ledgermaster
→ sobrescritura de transitions.js
→ LESS @plugin
→ RCE como ctf
→ /readflag SUID
→ flag
```

## Documentación

### Análisis técnico

[Archonyx: de un bot autenticado a RCE mediante cuatro primitivas encadenadas](article/archonyx-analysis.md)

El artículo se centra en:

- el razonamiento utilizado para aislar cada primitiva;
- las fronteras de confianza atravesadas;
- el funcionamiento del hardlink y el inode compartido;
- las pruebas locales utilizadas;
- las hipótesis descartadas;
- las causas raíz y mitigaciones.

### Walkthrough reproducible

[Walkthrough operativo completo](walkthrough/archonyx-reproducible.md)

Incluye:

- construcción de los payloads TAR;
- preparación de los documentos HTML;
- entrega mediante el bot;
- acceso como `ledgermaster`;
- validación inocua de la ejecución LESS;
- Stage 2 y recuperación de la flag;
- troubleshooting y limpieza.

## Artefactos

```text
.
├── README.md
├── LICENSE
├── article/
│   └── archonyx-analysis.md
├── walkthrough/
│   └── archonyx-reproducible.md
├── scripts/
│   ├── build_stage1_tar.py
│   ├── build_stage2_tar.py
│   └── marker-plugin.js
├── payloads/
│   ├── stage1.example.html
│   └── stage2.example.html
└── assets/
    ├── archonyx-chain.png
    ├── 01-bot-fetch-requests.png
    ├── 02-ledgermaster-access.png
    ├── 03-less-plugin-marker.png
    ├── 04-final-rce-and-flag.png
    ├── 05-decompress-tar-linkname.png
    └── 06-decompress-hardlink-write.png
```

## Generación de payloads

Stage 1:

```bash
python3 scripts/build_stage1_tar.py \
  --output stage1.tar
```

Stage 2:

```bash
python3 scripts/build_stage2_tar.py \
  --output stage2.tar
```

Comprobar las entradas:

```bash
tar -tvf stage1.tar
tar -tvf stage2.tar
```

Los archivos TAR generados no se incluyen en el repositorio.

## Primitiva principal

Archonyx utilizaba:

```text
decompress 4.2.1
decompress-tar 4.1.1
```

El extractor validaba que el destino permaneciera dentro del directorio de salida, pero utilizaba directamente el `linkname` de las entradas hardlink como origen del enlace.

La segunda entrada con el mismo nombre era escrita mediante `writeFile`, que truncaba y reescribía el inode existente en lugar de crear uno nuevo.

Esto permitía transformar:

```text
hardlink absoluto
+
entrada duplicada
+
truncado sobre el inode compartido
```

en:

```text
sobrescritura arbitraria de un archivo externo
```

La explicación completa y el código verificado están en el [análisis técnico](article/archonyx-analysis.md).

## Alcance

Este repositorio documenta un reto retirado de un CTF y una reproducción realizada en un entorno autorizado y aislado.

El contenido se publica con fines educativos y de investigación defensiva. No incluye:

- credenciales temporales;
- cookies o JWT reales;
- direcciones de instancias activas;
- dominios temporales utilizados durante el evento;
- el código fuente completo del reto;
- los archivos originales distribuidos por la organización.

## Resultado

Cyber Apocalypse CTF 2026: The Salt Crown

**249.º de 6.743 equipos — Cerberus Red Team**

## Licencia

Los scripts y el contenido original de este repositorio se publican bajo la [licencia MIT](LICENSE).

Los nombres, marcas y materiales originales del reto pertenecen a sus respectivos propietarios.
