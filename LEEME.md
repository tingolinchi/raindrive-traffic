# Preprocesador de incidencias de tráfico (DGT + Cataluña + País Vasco)

Qué hace: cada 10 minutos, un trabajo de GitHub Actions baja los feeds DATEX II del Punto de Acceso Nacional
(nap.dgt.es), los normaliza y los publica en GitHub Pages como JSON pequeño por celdas de 1°:

- `https://<usuario>.github.io/<repo>/meta.json` — hora de generación y estado de cada fuente.
- `https://<usuario>.github.io/<repo>/tiles/<lat>_<lon>.json` — incidencias de la celda (por ejemplo `38_-2.json`).
  Si una celda no existe (404) y `meta.json` está bien, significa "sin incidencias".

Fuentes (todas sin clave):
- DGT v3.7 (toda España salvo Cataluña y País Vasco): licencia CC BY, atribución a la DGT.
- Servei Català de Trànsit (Cataluña): el NAP dice "No licence – No contract / licencia no especificada". Comprueba con ellos
  las condiciones de reutilización antes de publicar la app abiertamente.
- Tráfico del Gobierno Vasco (DT-GV): CC BY, atribución.

Estado: probado solo con XML de ejemplo (`python3 -m unittest test_build_traffic`); NO probado contra los feeds reales
ni desde los servidores de GitHub (la DGT podría bloquear esas IP).

## Puesta en marcha (una vez)
1. Crea un repositorio PÚBLICO nuevo en GitHub (por ejemplo `raindrive-traffic`) y sube el contenido de esta carpeta
   (`traffic-feed/`) a su raíz (incluida la carpeta `.github`).
2. En el repositorio: Settings → Pages → Build and deployment → Source: **GitHub Actions**.
3. Pestaña Actions → "Incidencias de tráfico" → Run workflow. Mira el registro: debe mostrar cuántas incidencias salen de
   cada fuente y `skipped` (registros sin coordenadas, descartados).
4. Abre `https://<usuario>.github.io/<repo>/meta.json`. Debe mostrar `"ok":true` en las tres fuentes.
5. Pon esa dirección base en `local.properties` de la app: `traffic.baseUrl=https://<usuario>.github.io/<repo>`.

## Notas
- Si ninguna fuente responde, el trabajo falla y NO se publica (queda el último bueno; la app lo tratará como caducado a los 30 min).
- GitHub puede retrasar los trabajos programados; el repositorio hace un commit "latido" mensual para que no se desactive.
- Se descartan registros sin coordenadas (solo puntos kilométricos): se cuentan en `skipped`. Si ves muchos, dímelo.
