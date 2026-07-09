import time

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# ============================================================
# SIMULADOR PID EN LÍNEA PARA CONTROL DE GLUTEN
# ============================================================
# Sistema analizado:
# Control de contaminación con gluten en un alimento sin TACC
# mediante modelo PID, carga L(t), perturbación d(t),
# sensor con tiempo de escaneo y análisis de estabilidad.
# ============================================================


# ------------------------------------------------------------
# CONFIGURACIÓN GENERAL DE STREAMLIT
# ------------------------------------------------------------

st.set_page_config(
    page_title="Simulación PID - Control de Gluten",
    page_icon="🍞",
    layout="wide",
)

st.title("Simulación en línea de control PID para contaminación con gluten")

st.markdown(
    """
Este tablero permite simular un sistema de control en lazo cerrado aplicado
 a la detección y prevención de contaminación con gluten en un alimento sin TACC.

El modelo permite modificar en pantalla la carga inicial, la perturbación,
 el tiempo de escaneo del sensor y los parámetros del controlador PID.
"""
)


# ------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------


def calcular_perturbacion(t, inicio, duracion, amplitud):
    """
    Perturbación rectangular d(t).
    Se activa entre inicio e inicio + duración.

    La amplitud se interpreta como una tasa de contaminación
    expresada en ppm/s durante el intervalo activo.
    """
    if inicio <= t <= inicio + duracion:
        return amplitud
    return 0.0


def clasificar_estado(gluten_medido, limite_anmat):
    """
    Clasifica el estado operativo según el valor medido.
    """
    if gluten_medido <= 1:
        return "NORMAL"
    elif gluten_medido <= limite_anmat:
        return "CONTROLADO"
    elif gluten_medido <= 20:
        return "ALARMA"
    else:
        return "FALLA"


def calcular_calidad_servicio(
    recupera,
    tiempo_recuperacion,
    tiempo_maximo_recuperacion,
    hubo_saturacion,
    estable,
):
    """
    Evalúa la calidad del servicio del sistema.
    """
    if not recupera:
        return "FALLA"

    if hubo_saturacion and tiempo_recuperacion > tiempo_maximo_recuperacion:
        return "FALLA"

    if tiempo_recuperacion > tiempo_maximo_recuperacion:
        return "DEGRADADA"

    if not estable:
        return "DEGRADADA"

    return "ADECUADA"


def analizar_estabilidad(
    df,
    limite_anmat,
    fin_perturbacion,
    tiempo_maximo_recuperacion,
    ventana_estabilidad,
):
    """
    Analiza si el sistema recupera condición segura luego de la perturbación.
    """
    df_post = df[df["t"] >= fin_perturbacion].copy()

    if df_post.empty:
        return {
            "recupera": False,
            "tiempo_recuperacion": None,
            "estable": False,
            "variacion_final": None,
            "mensaje": "No hay datos posteriores a la perturbación.",
        }

    recuperados = df_post[df_post["ym(t)"] <= limite_anmat]

    if recuperados.empty:
        return {
            "recupera": False,
            "tiempo_recuperacion": None,
            "estable": False,
            "variacion_final": None,
            "mensaje": "El sistema no recuperó condición segura dentro del tiempo simulado.",
        }

    primer_tiempo_recuperado = recuperados["t"].iloc[0]
    tiempo_recuperacion = primer_tiempo_recuperado - fin_perturbacion

    ultimos = df.tail(ventana_estabilidad)

    if len(ultimos) < ventana_estabilidad:
        variacion_final = None
        estable = False
    else:
        variacion_final = ultimos["ym(t)"].max() - ultimos["ym(t)"].min()
        estable = (
            ultimos["ym(t)"].max() <= limite_anmat
            and variacion_final <= 1.0
        )

    if estable and tiempo_recuperacion <= tiempo_maximo_recuperacion:
        mensaje = "El sistema es estable: recupera condición segura y permanece controlado."
    elif tiempo_recuperacion > tiempo_maximo_recuperacion:
        mensaje = "El sistema recupera, pero con calidad de servicio degradada por recuperación lenta."
    else:
        mensaje = "El sistema no presenta estabilidad completa en la ventana final."

    return {
        "recupera": True,
        "tiempo_recuperacion": tiempo_recuperacion,
        "estable": estable,
        "variacion_final": variacion_final,
        "mensaje": mensaje,
    }


def simular_sistema(
    alimento,
    carga_inicial,
    referencia,
    limite_anmat,
    kp,
    ki,
    kd,
    amplitud_perturbacion,
    inicio_perturbacion,
    duracion_perturbacion,
    tiempo_scanner,
    tiempo_total,
    dt,
    eficiencia_base,
    ruido_sensor,
    accion_max,
    integral_max,
):
    """
    Simula el sistema PID completo.
    """

    y_real = carga_inicial
    y_medido = y_real
    integral = 0.0
    error_anterior = 0.0
    ultimo_escaneo = -tiempo_scanner

    factor_carga = 1 + (carga_inicial / 100)
    eficiencia_limpieza = eficiencia_base / factor_carga

    datos = []
    tiempos = np.arange(0, tiempo_total + dt, dt)

    for t in tiempos:
        d_t = calcular_perturbacion(
            t,
            inicio_perturbacion,
            duracion_perturbacion,
            amplitud_perturbacion,
        )

        escaneo_activo = False

        if t - ultimo_escaneo >= tiempo_scanner:
            ruido = np.random.normal(0, ruido_sensor)
            y_medido = max(0.0, y_real + ruido)
            ultimo_escaneo = t
            escaneo_activo = True

        error = y_medido - referencia
        integral += error * dt
        integral = np.clip(integral, -integral_max, integral_max)
        derivada = (error - error_anterior) / dt
        p = kp * error
        i = ki * integral
        d = kd * derivada
        u = p + i + d

        u_saturada = np.clip(u, 0.0, accion_max)
        saturado = u != u_saturada
        u = u_saturada

        reduccion = eficiencia_limpieza * u * dt
        aporte_perturbacion = d_t * dt
        y_real = y_real + aporte_perturbacion - reduccion
        if y_real < 0:
            y_real = 0.0

        estado = clasificar_estado(y_medido, limite_anmat)

        datos.append({
            "t": t,
            "alimento": alimento,
            "r(t)": referencia,
            "L(t)": carga_inicial,
            "y(t)": y_real,
            "ym(t)": y_medido,
            "e(t)": error,
            "P(t)": p,
            "I(t)": i,
            "D(t)": d,
            "u(t)": u,
            "d(t)": d_t,
            "scanner": "MIDE" if escaneo_activo else "ESPERA",
            "estado": estado,
            "saturado": saturado,
            "eficiencia_limpieza": eficiencia_limpieza,
        })

        error_anterior = error

    return pd.DataFrame(datos)


def graficar_respuesta(df, limite_anmat):
    """
    Gráfico de salida, medición, referencia y perturbación.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["y(t)"],
        name="y(t) - Gluten real",
        mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["ym(t)"],
        name="ym(t) - Gluten medido",
        mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["r(t)"],
        name="r(t) - Referencia",
        mode="lines",
        line=dict(dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["d(t)"],
        name="d(t) - Perturbación",
        mode="lines",
        line=dict(dash="dot"),
    ))

    fig.add_hline(
        y=limite_anmat,
        line_dash="dash",
        line_color="red",
        annotation_text="Límite ANMAT 10 ppm",
    )

    fig.update_layout(
        title="Respuesta del sistema ante carga y perturbación",
        xaxis_title="Tiempo [s]",
        yaxis_title="ppm",
        legend_title="Señales",
        height=430,
    )

    return fig


def graficar_pid(df):
    """
    Gráfico separado de P, I y D.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["P(t)"],
        name="P(t) - Proporcional",
        mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["I(t)"],
        name="I(t) - Integral",
        mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["D(t)"],
        name="D(t) - Derivativa",
        mode="lines",
    ))

    fig.update_layout(
        title="Componentes del controlador PID",
        xaxis_title="Tiempo [s]",
        yaxis_title="Valor de componente",
        legend_title="Componentes",
        height=430,
    )

    return fig


def graficar_control(df):
    """
    Gráfico de acción de control.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["u(t)"],
        name="u(t) - Acción de control",
        mode="lines",
    ))

    fig.update_layout(
        title="Señal de control u(t)",
        xaxis_title="Tiempo [s]",
        yaxis_title="Intensidad de actuación",
        height=350,
    )

    return fig


def graficar_error(df):
    """
    Gráfico de error.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["e(t)"],
        name="e(t) - Error",
        mode="lines",
    ))

    fig.update_layout(
        title="Señal de error e(t)",
        xaxis_title="Tiempo [s]",
        yaxis_title="ppm",
        height=350,
    )

    return fig


# ------------------------------------------------------------
# PANEL LATERAL - DATOS DE ENTRADA
# ------------------------------------------------------------

st.sidebar.header("Parámetros del sistema")

alimento = st.sidebar.selectbox(
    "Alimento seleccionado",
    [
        "Panificado sin TACC",
        "Galletita sin TACC",
        "Pasta sin TACC",
        "Preparación hospitalaria sin TACC",
    ],
)

referencia = st.sidebar.number_input(
    "Referencia r(t) [ppm]",
    min_value=0.0,
    max_value=20.0,
    value=0.0,
    step=0.5,
)

limite_anmat = st.sidebar.number_input(
    "Límite operativo ANMAT [ppm]",
    min_value=1.0,
    max_value=50.0,
    value=10.0,
    step=1.0,
)

carga_inicial = st.sidebar.slider(
    "Carga inicial L(t) [ppm]",
    min_value=0.0,
    max_value=100.0,
    value=25.0,
    step=1.0,
)

st.sidebar.header("Parámetros PID")

kp = st.sidebar.slider(
    "Kp - Ganancia proporcional",
    min_value=0.0,
    max_value=5.0,
    value=0.80,
    step=0.05,
)

ki = st.sidebar.slider(
    "Ki - Ganancia integral",
    min_value=0.0,
    max_value=1.0,
    value=0.05,
    step=0.01,
)

kd = st.sidebar.slider(
    "Kd - Ganancia derivativa",
    min_value=0.0,
    max_value=2.0,
    value=0.20,
    step=0.05,
)

st.sidebar.header("Perturbación d(t)")

amplitud_perturbacion = st.sidebar.slider(
    "Amplitud de perturbación d(t) [ppm/s]",
    min_value=0.0,
    max_value=50.0,
    value=12.0,
    step=1.0,
)

inicio_perturbacion = st.sidebar.slider(
    "Inicio de perturbación [s]",
    min_value=0,
    max_value=300,
    value=20,
    step=1,
)

duracion_perturbacion = st.sidebar.slider(
    "Duración de perturbación [s]",
    min_value=0,
    max_value=300,
    value=10,
    step=1,
)

st.sidebar.header("Sensor / Scanner")

tiempo_scanner = st.sidebar.slider(
    "Tiempo de escaneo del sensor [s]",
    min_value=1,
    max_value=30,
    value=5,
    step=1,
)

ruido_sensor = st.sidebar.slider(
    "Ruido del sensor [ppm]",
    min_value=0.0,
    max_value=3.0,
    value=0.20,
    step=0.05,
)

st.sidebar.header("Planta / actuador")

eficiencia_base = st.sidebar.slider(
    "Eficiencia base de limpieza",
    min_value=0.01,
    max_value=0.50,
    value=0.08,
    step=0.01,
)

accion_max = st.sidebar.slider(
    "Saturación máxima del actuador u(t)",
    min_value=10.0,
    max_value=200.0,
    value=100.0,
    step=5.0,
)

integral_max = st.sidebar.slider(
    "Límite de acumulación integral",
    min_value=10.0,
    max_value=1000.0,
    value=300.0,
    step=10.0,
)

st.sidebar.header("Tiempo de simulación")

tiempo_total = st.sidebar.slider(
    "Tiempo total [s]",
    min_value=30,
    max_value=600,
    value=120,
    step=10,
)

dt = st.sidebar.selectbox(
    "Paso de simulación dt [s]",
    options=[0.5, 1.0, 2.0],
    index=1,
)

tiempo_maximo_recuperacion = st.sidebar.slider(
    "Tiempo máximo de recuperación esperado [s]",
    min_value=5,
    max_value=180,
    value=30,
    step=5,
)

ventana_estabilidad = st.sidebar.slider(
    "Ventana final para estabilidad [muestras]",
    min_value=5,
    max_value=30,
    value=10,
    step=1,
)

modo_tiempo_real = st.sidebar.checkbox(
    "Mostrar simulación progresiva",
    value=False,
)

velocidad_reproduccion = st.sidebar.slider(
    "Velocidad de reproducción",
    min_value=0.0,
    max_value=1.0,
    value=0.05,
    step=0.01,
)


# ------------------------------------------------------------
# EJECUCIÓN DE LA SIMULACIÓN
# ------------------------------------------------------------

df = simular_sistema(
    alimento=alimento,
    carga_inicial=carga_inicial,
    referencia=referencia,
    limite_anmat=limite_anmat,
    kp=kp,
    ki=ki,
    kd=kd,
    amplitud_perturbacion=amplitud_perturbacion,
    inicio_perturbacion=inicio_perturbacion,
    duracion_perturbacion=duracion_perturbacion,
    tiempo_scanner=tiempo_scanner,
    tiempo_total=tiempo_total,
    dt=dt,
    eficiencia_base=eficiencia_base,
    ruido_sensor=ruido_sensor,
    accion_max=accion_max,
    integral_max=integral_max,
)

fin_perturbacion = inicio_perturbacion + duracion_perturbacion

analisis = analizar_estabilidad(
    df=df,
    limite_anmat=limite_anmat,
    fin_perturbacion=fin_perturbacion,
    tiempo_maximo_recuperacion=tiempo_maximo_recuperacion,
    ventana_estabilidad=ventana_estabilidad,
)

hubo_saturacion = bool(df["saturado"].any())

calidad_servicio = calcular_calidad_servicio(
    recupera=analisis["recupera"],
    tiempo_recuperacion=analisis["tiempo_recuperacion"]
    if analisis["tiempo_recuperacion"] is not None
    else 9999,
    tiempo_maximo_recuperacion=tiempo_maximo_recuperacion,
    hubo_saturacion=hubo_saturacion,
    estable=analisis["estable"],
)


# ------------------------------------------------------------
# PANEL DE RESULTADOS
# ------------------------------------------------------------

st.subheader("Parámetros principales del ensayo")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Alimento", alimento)
    st.metric("Referencia r(t)", f"{referencia:.2f} ppm")

with col2:
    st.metric("Carga L(t)", f"{carga_inicial:.2f} ppm")
    st.metric("Límite ANMAT", f"{limite_anmat:.2f} ppm")

with col3:
    st.metric("Kp", f"{kp:.2f}")
    st.metric("Ki", f"{ki:.2f}")

with col4:
    st.metric("Kd", f"{kd:.2f}")
    st.metric("Scanner", f"{tiempo_scanner:.1f} s")


st.subheader("Resultados finales")

gluten_final = df["ym(t)"].iloc[-1]
error_final = df["e(t)"].iloc[-1]
accion_final = df["u(t)"].iloc[-1]
estado_final = df["estado"].iloc[-1]

col5, col6, col7, col8 = st.columns(4)

with col5:
    st.metric("Gluten medido final ym(t)", f"{gluten_final:.2f} ppm")

with col6:
    st.metric("Error final e(t)", f"{error_final:.2f} ppm")

with col7:
    st.metric("Acción final u(t)", f"{accion_final:.2f}")

with col8:
    st.metric("Estado final", estado_final)


st.subheader("Ensayo de estabilidad y calidad del servicio")

col9, col10, col11, col12 = st.columns(4)

with col9:
    if analisis["tiempo_recuperacion"] is None:
        st.metric("Tiempo de recuperación", "No recupera")
    else:
        st.metric(
            "Tiempo de recuperación",
            f"{analisis['tiempo_recuperacion']:.1f} s",
        )

with col10:
    st.metric("Estabilidad", "ESTABLE" if analisis["estable"] else "NO ESTABLE")

with col11:
    st.metric("Saturación del actuador", "SÍ" if hubo_saturacion else "NO")

with col12:
    st.metric("Calidad del servicio", calidad_servicio)

st.info(analisis["mensaje"])


# ------------------------------------------------------------
# GRÁFICOS
# ------------------------------------------------------------

if not modo_tiempo_real:
    st.subheader("Gráficos de señales del sistema")

    st.plotly_chart(
        graficar_respuesta(df, limite_anmat),
        use_container_width=True,
    )

    st.plotly_chart(
        graficar_error(df),
        use_container_width=True,
    )

    st.plotly_chart(
        graficar_pid(df),
        use_container_width=True,
    )

    st.plotly_chart(
        graficar_control(df),
        use_container_width=True,
    )

    st.subheader("Últimos valores de señales")
    st.dataframe(df.tail(15), use_container_width=True)
else:
    st.subheader("Simulación progresiva")

    placeholder_metricas = st.empty()
    placeholder_grafico1 = st.empty()
    placeholder_grafico2 = st.empty()
    placeholder_grafico3 = st.empty()
    placeholder_tabla = st.empty()

    df_animado = pd.DataFrame()

    for idx in range(len(df)):
        df_animado = df.iloc[: idx + 1]
        fila = df_animado.iloc[-1]

        with placeholder_metricas.container():
            c1, c2, c3, c4, c5 = st.columns(5)

            with c1:
                st.metric("t", f"{fila['t']:.1f} s")

            with c2:
                st.metric("ym(t)", f"{fila['ym(t)']:.2f} ppm")

            with c3:
                st.metric("e(t)", f"{fila['e(t)']:.2f} ppm")

            with c4:
                st.metric("u(t)", f"{fila['u(t)']:.2f}")

            with c5:
                st.metric("Estado", fila["estado"])

        placeholder_grafico1.plotly_chart(
            graficar_respuesta(df_animado, limite_anmat),
            use_container_width=True,
        )

        placeholder_grafico2.plotly_chart(
            graficar_pid(df_animado),
            use_container_width=True,
        )

        placeholder_grafico3.plotly_chart(
            graficar_control(df_animado),
            use_container_width=True,
        )

        placeholder_tabla.dataframe(
            df_animado.tail(10),
            use_container_width=True,
        )

        time.sleep(velocidad_reproduccion)


# ------------------------------------------------------------
# EXPLICACIÓN CONCEPTUAL
# ------------------------------------------------------------

st.subheader("Interpretación del modelo")

st.markdown(
    f"""
- La referencia del sistema es **r(t) = {referencia:.2f} ppm**.
- El límite operativo para considerar apto el alimento es **{limite_anmat:.2f} ppm**.
- La carga del proceso **L(t)** representa la condición inicial del alimento, superficie o lote.
- La perturbación **d(t)** representa contaminación cruzada durante un intervalo de tiempo.
- El scanner mide cada **{tiempo_scanner} segundos**.
- Si la perturbación dura más que el tiempo de escaneo, el sistema debería detectarla.
- El controlador PID calcula la acción de control a partir de:

`u(t) = P(t) + I(t) + D(t)`

 donde:

- `P(t) = Kp · e(t)`
- `I(t) = Ki · ∫e(t)dt`
- `D(t) = Kd · de(t)/dt`

La señal `u(t)` representa la intensidad de actuación del sistema,
por ejemplo limpieza, bloqueo, alarma, remuestreo o rechazo.
"""
)

st.subheader("Relación entre carga y calidad del servicio")

st.markdown(
    """
La carga `L(t)` afecta directamente la calidad del servicio del sistema.
Una carga elevada reduce la eficiencia relativa de la acción correctiva,
aumenta el tiempo de recuperación y puede llevar a saturación del actuador.

La calidad del servicio se clasifica como:

- **ADECUADA**: recupera condición segura dentro del tiempo esperado.
- **DEGRADADA**: recupera, pero tarda más de lo esperable o presenta inestabilidad.
- **FALLA**: no recupera condición segura o permanece por encima del límite.
"""
)

