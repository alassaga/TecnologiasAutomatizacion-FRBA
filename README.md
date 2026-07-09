# TecnologiasAutomatizacion-FRBA

Repositorio para presentar el trabajo práctico final de Tecnologías para la automatización.
Autor: Andrea Fabiana Lassaga
Legajo: 68989/1

## Descripción

Esta aplicación es una simulación de un controlador PID para el control de contaminación con gluten en un alimento sin TACC, construida con Streamlit, NumPy, Pandas y Plotly.

## Requisitos previos

- Windows, macOS o Linux
- Python 3.9+ instalado
- Conexión a internet para instalar dependencias

## Instalación

1. Abre un terminal en la carpeta del proyecto:

```powershell
cd d:\TeoriaControl\TecnologiasAutomatizacion-FRBA
```

2. Crea un entorno virtual recomendado:

```powershell
py -m venv venv
```

3. Activa el entorno virtual:

- En Windows:

```powershell
venv\Scripts\Activate.ps1
```

- En macOS / Linux:

```bash
source venv/bin/activate
```

4. Instala las dependencias:

```powershell
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

## Ejecutar la aplicación

Desde la carpeta del proyecto con el entorno virtual activado, ejecuta:

```powershell
py -m streamlit run app.py
```

Luego abre la URL que muestra Streamlit en el navegador, normalmente:

- `http://localhost:8501`

## Uso en Streamlit

1. Ajusta los parámetros del controlador en la barra lateral:
   - `Kp`, `Ki`, `Kd` para el PID.
   - `Carga inicial`, `Referencia`, `Límite ANMAT`.
   - `Perturbación`, `Inicio` y `Duración`.
   - `Tiempo de escaneo`, `Ruido` y `Eficiencia de limpieza`.
2. Activa o desactiva `Mostrar simulación progresiva` para ver el avance en tiempo real.
3. Observa los gráficos generados:
   - Respuesta del sistema.
   - Error `e(t)`.
   - Componentes `P(t)`, `I(t)` y `D(t)`.
   - Señal de control `u(t)`.
4. Revisa los resultados finales en la sección de métricas y el análisis de estabilidad.

## Solución de problemas

- Si `streamlit` no está instalado, instala las dependencias con:

```powershell
py -m pip install -r requirements.txt
```

- Si el comando `py` no funciona, prueba con `python`:

```powershell
python -m streamlit run app.py
```

- Si se produce un error de sintaxis, ejecuta:

```powershell
py -m py_compile app.py
```

- Si la aplicación no se muestra en el navegador, revisa que no haya otro proceso usando el puerto `8501`.
- Si el terminal queda bloqueado, cierra el terminal y abre uno nuevo en la carpeta del proyecto.
- Si ves errores de importación, asegúrate de activar el entorno virtual antes de ejecutar Streamlit.

## Validar sintaxis

Antes de ejecutar, puedes verificar que no haya errores de sintaxis con:

```powershell
py -m py_compile app.py
```

## Archivos principales

- `app.py`: aplicación principal de Streamlit.
- `requirements.txt`: dependencias necesarias.
- `README.md`: instrucciones de uso.

## Publicar en GitHub

Si tu repositorio local ya está inicializado y tiene remoto configurado, usa:

```bash
git status
git add README.md app.py requirements.txt
git commit -m "Actualizar README e instrucciones de ejecución"
git push
```

Si necesitas configurar el remoto por primera vez, usa:

```bash
git branch -M main
git remote add origin https://github.com/alassaga/TecnologiasAutomatizacion-FRBA.git
git push -u origin main
```

## Notas

- Si Streamlit abre la aplicación en el navegador automáticamente, mantén el terminal abierto.
- Si recibes errores de módulo, revisa que el entorno virtual esté activo y que las dependencias estén instaladas.
- Para cualquier cambio posterior, repite `git add`, `git commit` y `git push`.

