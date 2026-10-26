# Liquidity Dashboard — despliegue Render

## Archivos faltantes
Este paquete integra los 24 archivos Python proporcionados en ambas entregas. No incluye los CSV ni el Excel, por lo que el arranque completo depende de contar con esos datos.

## Datos
Se requieren como minimo `Base_M.csv`, `df_final_tenencias.csv`, `IRS_volumen.csv` y un libro IIF compatible. No se incluyen datos. `data_files/` esta excluida del repositorio por `.gitignore`. En Render el sistema de archivos de un servicio gratuito es efimero y no tiene acceso directo a rutas SMB corporativas. Los datos deben obtenerse de una fuente aprobada y estar presentes ANTES de iniciar Gunicorn. No subas informacion corporativa a servicios externos sin autorizacion.

Variables admitidas:
- `DASHBOARD_DATA_DIR`: carpeta general de datos (por defecto `<raiz>/data_files`).
- `LIQUIDITY_BASE_PATH`: ruta completa de `Base_M.csv`.
- `HOLDINGS_BASE_PATH`: ruta completa de `df_final_tenencias.csv`.
- `IIF_DATA_DIR`: carpeta con libro Excel IIF.

Las paginas IRS e IIF ya utilizan rutas configurables. IIF admite tambien `IIF_WORKBOOK_PATH` para indicar un archivo Excel concreto.

## Despliegue
Build: `pip install -r requirements.txt`
Start: `gunicorn liquidity_app:server --bind 0.0.0.0:$PORT --workers 1 --timeout 180`

## Prueba local
`python -m pip install -r requirements.txt` y `python liquidity_app.py` (tras incorporar datos autorizados). Los modulos `data.py` y `holdings_utils.py` cargan los CSV al importar; actualizar el CSV requiere reiniciar o implementar recarga.
