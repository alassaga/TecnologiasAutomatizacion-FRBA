# TecnologiasAutomatizacion-FRBA

Trabajo práctico final de Tecnologías para la automatización.
Autor: Andrea Fabiana Lassaga
Legajo: 68989/1

## ¿Qué hace esta app?

Simula un controlador PID para controlar la contaminación con gluten en un alimento sin TACC.

El modelo distingue dos variables clave:

- `gluten_inicial` o `y(0)` [ppm], que representa la cantidad real de gluten al inicio y está limitado entre 0 y 10 ppm.
- `carga_proceso` o `L(t)` [%], que representa la complejidad del proceso y la dificultad de limpieza.

El alimento seleccionado aplica un factor de complejidad adicional que reduce la eficiencia de limpieza. La perturbación `d(t)` representa contaminación cruzada y puede hacer que el gluten supere 10 ppm.

La aplicación usa Streamlit para mostrar gráficos de respuesta, error, componentes PID y señales de control.

## Requisitos

- Python 3.8 o superior
- Conexión a internet para instalar dependencias

## Pasos para ejecutar el programa

Si vas a trabajar desde el repositorio remoto, clónalo primero:

```powershell
git clone https://github.com/alassaga/TecnologiasAutomatizacion-FRBA.git
cd TecnologiasAutomatizacion-FRBA
```

Si ya tienes la carpeta local, abre una terminal directamente en ella.

1. Abre una terminal en la carpeta del proyecto:

```powershell
cd d:\TeoriaControl\TecnologiasAutomatizacion-FRBA
```

2. Crea un entorno virtual:

```powershell
py -3 -m venv .venv
```

3. Activa el entorno virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, ejecuta una vez:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

4. Instala las dependencias:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

5. Ejecuta la aplicación:

```powershell
py -m streamlit run app.py
```

6. Abre en el navegador la dirección que muestra Streamlit, normalmente:

- `http://localhost:8501`

## Instrucciones rápidas para cualquier usuario

Si solo quieres ejecutar el programa, sigue estos pasos:

- Clona el repositorio o usa la carpeta local.
- Abre una terminal dentro de `TecnologiasAutomatizacion-FRBA`.
- Crea y activa un entorno virtual.
- Instala dependencias con `pip install -r requirements.txt`.
- Ejecuta `py -m streamlit run app.py`.
- Abre `http://localhost:8501`.

## Modelo de simulación

- `gluten_inicial` (`y(0)`): gluten real en ppm al inicio.
- `carga_proceso` (`L(t)`): carga del proceso en porcentaje.
- `eficiencia_base`: eficiencia de limpieza base del actuador.
- `factor_complejidad`: depende del alimento y reduce la eficiencia de limpieza.
- `d(t)`: perturbación de contaminación cruzada que puede elevar el gluten.

## Qué ajustar en la app

En la barra lateral de Streamlit puedes modificar:

- `Kp`, `Ki`, `Kd`
- `Gluten inicial y(0)`
- `Carga del proceso L(t) [%]`
- `Referencia`
- `Límite ANMAT`
- `Perturbación`, `Inicio`, `Duración`
- `Tiempo de escaneo`
- `Ruido`
- `Eficiencia base de limpieza`
- `Saturación máxima del actuador`
- `Límite de acumulación integral`
- `Mostrar simulación progresiva`

## Qué muestran los resultados

- `r(t)`: referencia deseada de gluten en ppm.
- `y(t)`: gluten real en ppm.
- `ym(t)`: gluten medido por el sensor en ppm.
- `e(t)`: error de control (`ym(t) - r(t)`).
- `P(t)`, `I(t)`, `D(t)`: componentes del controlador PID.
- `u(t)`: acción de control aplicada.
- `d(t)`: perturbación de contaminación cruzada.
- `L(t)`: carga del proceso en %.
- `estado`: clasificación operacional según el límite ANMAT.
- `saturado`: indica si el actuador alcanzó su máximo.
- `calidad del servicio`: evaluación de recuperación y estabilidad.

## Solución de problemas

- Si el comando `py` no funciona, usa `python`:

```powershell
python -m streamlit run app.py
```

- Si `streamlit` no está instalado:

```powershell
pip install -r requirements.txt
```

- Si el puerto `8501` está ocupado, prueba otro puerto:

```powershell
py -m streamlit run app.py --server.port 8502
```

- Si hay error de sintaxis:

```powershell
py -m py_compile app.py
```

- Si no puedes activar el entorno en PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Archivos importantes

- `app.py`: aplicación principal de Streamlit.
- `requirements.txt`: lista de dependencias.
- `README.md`: instrucciones y guía de uso.

## Git básico (opcional)

Para guardar cambios si trabajas con Git:

```powershell
git status
git add README.md app.py requirements.txt
git commit -m "Actualizar README e instrucciones de ejecución"
git push
```

Si todavía no configuraste el remoto:

```powershell
git branch -M main
git remote add origin https://github.com/alassaga/TecnologiasAutomatizacion-FRBA.git
git push -u origin main
```
