import time

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# ============================================================
# SIMULADOR PID EN LÍNEA PARA CONTROL DE GLUTEN
# ------------------------------------------------------------
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

El modelo permite modificar en pantalla el gluten inicial, la carga del proceso,
la perturbación, el tiempo de escaneo del sensor y los parámetros del controlador PID.
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
    saturado_final,
    estable,
    gluten_final,
    limite_anmat,
):
    """
    Evalúa la calidad del servicio del sistema.
    """
    # Si no recupera o termina por encima del límite -> FALLA
    if not recupera:
        return "FALLA"

    if gluten_final is None:
        return "FALLA"

    if gluten_final > limite_anmat:
        return "FALLA"

    # Si no hay tiempo de recuperación válido -> FALLA
    if tiempo_recuperacion is None:
        return "FALLA"

    # Si no es estable -> DEGRADADA
    if not estable:
        return "DEGRADADA"

    # Si tarda demasiado en recuperar -> DEGRADADA
    if tiempo_recuperacion > tiempo_maximo_recuperacion:
        return "DEGRADADA"

    # Si termina con saturación persistente -> DEGRADADA
    if saturado_final:
        return "DEGRADADA"

    # Si pasa todas las condiciones -> ADECUADA
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

    # Recuperación basada en la medición del scanner (f(t) / ym)
    recuperados = df_post[df_post["f(t)"] <= limite_anmat]

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

    # Evaluar la ventana final sobre la medición ym (f(t))
    ultimos = df.tail(ventana_estabilidad)

    if len(ultimos) < ventana_estabilidad:
        variacion_final = None
        estable = False
    else:
        variacion_final = ultimos["f(t)"].max() - ultimos["f(t)"].min()
        # Estable si la medición final y toda la ventana están por debajo del límite
        estable = (
            ultimos["f(t)"].max() <= limite_anmat
            and ultimos["f(t)"].iloc[-1] <= limite_anmat
        )

    if estable and tiempo_recuperacion <= tiempo_maximo_recuperacion:
        mensaje = "El sistema es estable: recupera condición segura y permanece controlado."
    elif tiempo_recuperacion > tiempo_maximo_recuperacion:
        mensaje = (
            f"El sistema recupera, pero el tiempo de recuperación ({tiempo_recuperacion:.1f} s) "
            f"supera el máximo esperado ({tiempo_maximo_recuperacion} s)."
        )
    else:
        mensaje = "El sistema recuperó pero no mantiene estabilidad final (valores fuera del límite en la ventana final)."

    return {
        "recupera": True,
        "tiempo_recuperacion": tiempo_recuperacion,
        "estable": estable,
        "variacion_final": variacion_final,
        "mensaje": mensaje,
    }


def simular_sistema(
    alimento,
    gluten_inicial,
    carga_proceso,
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
    factor_complejidad,
):
    """
    Simula el sistema PID completo.
    """

    y_real = gluten_inicial
    y_medido = y_real
    integral = 0.0
    error_anterior = 0.0
    ultimo_escaneo = -tiempo_scanner

    factor_carga = 1 + (carga_proceso / 100)
    eficiencia_limpieza = eficiencia_base / (factor_carga * factor_complejidad)

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

        # Forzar el último escaneo en el tiempo final de la simulación
        if t - ultimo_escaneo >= tiempo_scanner or t == tiempos[-1]:
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
        u_raw = p + i + d

        saturado = u_raw > accion_max
        u = np.clip(u_raw, 0.0, accion_max)

        reduccion = eficiencia_limpieza * u * dt
        aporte_perturbacion = d_t * dt
        y_real = y_real + aporte_perturbacion - reduccion
        if y_real < 0:
            y_real = 0.0

        # Clasificar el estado con la señal medida ym/f(t),
        # para que el estado final y la estabilidad se basen en la
        # misma información del scanner.
        estado = clasificar_estado(y_medido, limite_anmat)

        datos.append({
            "t": t,
            "alimento": alimento,
            "Oi(t)": referencia,
            "L(t)": carga_proceso,
            "Oo(t)": y_real,
            "f(t)": y_medido,
            "e(t)": error,
            "P(t)": p,
            "I(t)": i,
            "D(t)": d,
            "u(t)": u,
            "u_raw": u_raw,
            "d(t)": d_t,
            "factor_complejidad": factor_complejidad,
            "scanner": "MIDE" if escaneo_activo else "ESPERA",
            "estado": estado,
            "saturado": saturado,
            "eficiencia_limpieza": eficiencia_limpieza,
        })

        error_anterior = error

    return pd.DataFrame(datos)


def graficar_respuesta(df, limite_anmat):
    """
    Gráfico de salida, medición, referencia, perturbación y carga.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["Oo(t)"],
        name="Oo(t) - Gluten real",
        mode="lines",
        yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["f(t)"],
        name="f(t) - Gluten medido",
        mode="lines",
        yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["Oi(t)"],
        name="Oi(t) - Referencia",
        mode="lines",
        line=dict(dash="dash"),
        yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["d(t)"],
        name="d(t) - Perturbación",
        mode="lines",
        line=dict(dash="dot"),
        yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=df["t"],
        y=df["L(t)"],
        name="L(t) - Carga proceso %",
        mode="lines",
        line=dict(dash="dashdot"),
        yaxis="y2",
    ))

    fig.add_hline(
        y=limite_anmat,
        line_dash="dash",
        line_color="red",
        annotation_text="Límite ANMAT 10 ppm",
        yref="y1",
    )

    fig.update_layout(
        title="Respuesta del sistema ante carga del proceso y perturbación",
        xaxis_title="Tiempo [s]",
        yaxis=dict(title="ppm", side="left"),
        yaxis2=dict(
            title="Carga L(t) [%]",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
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

input_defaults = {
    "alimento": "Panificado sin TACC",
    "referencia": 0.0,
    "limite_anmat": 10.0,
    "gluten_inicial": 0.0,
    "carga_proceso": 10.0,
    "kp": 0.80,
    "ki": 0.05,
    "kd": 0.20,
    "amplitud_perturbacion": 0.0,
    "inicio_perturbacion": 20,
    "duracion_perturbacion": 10,
    "tiempo_scanner": 5,
    "ruido_sensor": 0.00,
    "eficiencia_base": 0.08,
    "accion_max": 100.0,
    "integral_max": 300.0,
    "tiempo_total": 120,
    "dt": 1.0,
    "tiempo_maximo_recuperacion": 30,
    "ventana_estabilidad": 10,
    "modo_tiempo_real": False,
    "velocidad_reproduccion": 0.05,
    "stop_sim": False,
    "sim_started": False,
}

for key, value in input_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_inputs():
    for key, value in input_defaults.items():
        st.session_state[key] = value
    st.session_state["sim_started"] = False
    st.session_state["stop_sim"] = False
    st.session_state["progress_index"] = 0


def restart_simulation():
    reset_inputs()

alimento = st.sidebar.selectbox(
    "Alimento seleccionado",
    [
        "Panificado sin TACC",
        "Galletita sin TACC",
        "Pasta sin TACC",
        "Preparación hospitalaria sin TACC",
    ],
    key="alimento",
)

factores_complejidad = {
    "Panificado sin TACC": 1.0,
    "Galletita sin TACC": 1.2,
    "Pasta sin TACC": 1.3,
    "Preparación hospitalaria sin TACC": 1.5,
}

referencia = st.sidebar.number_input(
    "Referencia Oi(t) [ppm]",
    min_value=0.0,
    max_value=20.0,
    step=0.5,
    key="referencia",
)

limite_anmat = st.sidebar.number_input(
    "Límite operativo ANMAT [ppm]",
    min_value=1.0,
    max_value=50.0,
    step=1.0,
    key="limite_anmat",
)

gluten_inicial = st.sidebar.slider(
    "Gluten inicial y(0) [ppm]",
    min_value=0.0,
    max_value=10.0,
    step=0.1,
    key="gluten_inicial",
)

carga_proceso = st.sidebar.slider(
    "Carga del proceso L(t) [% complejidad]",
    min_value=0.0,
    max_value=100.0,
    step=1.0,
    key="carga_proceso",
)

st.sidebar.header("Parámetros PID")

kp = st.sidebar.slider(
    "Kp - Ganancia proporcional",
    min_value=0.0,
    max_value=5.0,
    step=0.05,
    key="kp",
)

ki = st.sidebar.slider(
    "Ki - Ganancia integral",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    key="ki",
)

kd = st.sidebar.slider(
    "Kd - Ganancia derivativa",
    min_value=0.0,
    max_value=2.0,
    step=0.05,
    key="kd",
)

st.sidebar.header("Perturbación d(t)")

amplitud_perturbacion = st.sidebar.slider(
    "Amplitud de perturbación d(t) [ppm/s]",
    min_value=0.0,
    max_value=50.0,
    step=1.0,
    key="amplitud_perturbacion",
)

inicio_perturbacion = st.sidebar.slider(
    "Inicio de perturbación [s]",
    min_value=0,
    max_value=300,
    step=1,
    key="inicio_perturbacion",
)

duracion_perturbacion = st.sidebar.slider(
    "Duración de perturbación [s]",
    min_value=0,
    max_value=300,
    step=1,
    key="duracion_perturbacion",
)

st.sidebar.header("Sensor / Scanner")

tiempo_scanner = st.sidebar.slider(
    "Tiempo de escaneo del sensor [s]",
    min_value=1,
    max_value=30,
    step=1,
    key="tiempo_scanner",
)

ruido_sensor = st.sidebar.slider(
    "Ruido del sensor [ppm]",
    min_value=0.0,
    max_value=3.0,
    step=0.05,
    key="ruido_sensor",
)

st.sidebar.header("Planta / actuador")

eficiencia_base = st.sidebar.slider(
    "Eficiencia base de limpieza",
    min_value=0.01,
    max_value=0.50,
    step=0.01,
    key="eficiencia_base",
)

accion_max = st.sidebar.slider(
    "Saturación máxima del actuador u(t)",
    min_value=10.0,
    max_value=200.0,
    step=5.0,
    key="accion_max",
)

integral_max = st.sidebar.slider(
    "Límite de acumulación integral",
    min_value=10.0,
    max_value=1000.0,
    step=10.0,
    key="integral_max",
)

st.sidebar.header("Tiempo de simulación")

tiempo_total = st.sidebar.slider(
    "Tiempo total [s]",
    min_value=30,
    max_value=600,
    step=10,
    key="tiempo_total",
)

dt = st.sidebar.selectbox(
    "Paso de simulación dt [s]",
    options=[0.5, 1.0, 2.0],
    key="dt",
)

tiempo_maximo_recuperacion = st.sidebar.slider(
    "Tiempo máximo de recuperación esperado [s]",
    min_value=5,
    max_value=180,
    step=5,
    key="tiempo_maximo_recuperacion",
)

ventana_estabilidad = st.sidebar.slider(
    "Ventana final para estabilidad [muestras]",
    min_value=5,
    max_value=30,
    step=1,
    key="ventana_estabilidad",
)

modo_tiempo_real = st.sidebar.checkbox(
    "Mostrar simulación progresiva",
    key="modo_tiempo_real",
)

if not modo_tiempo_real:
    st.sidebar.warning(
        "Activa 'Mostrar simulación progresiva' para usar Detener/Reanudar sobre la ejecución paso a paso."
    )

velocidad_reproduccion = st.sidebar.slider(
    "Velocidad de reproducción",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    key="velocidad_reproduccion",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Control de simulación")

# Control para iniciar/detener/reanudar/reiniciar simulación progresiva
if not st.session_state["sim_started"]:
    if st.sidebar.button("Iniciar simulación"):
        st.session_state["sim_started"] = True
        st.session_state["stop_sim"] = False
        st.session_state["progress_index"] = 0
    st.sidebar.info("Define parámetros y presiona Iniciar simulación.")
else:
    st.sidebar.success("Simulación iniciada")

if st.session_state["sim_started"]:
    if st.sidebar.button("Detener simulación"):
        st.session_state["stop_sim"] = True

    st.sidebar.markdown("---")

    if st.sidebar.button("Reanudar simulación"):
        st.session_state["stop_sim"] = False

if not modo_tiempo_real:
    st.sidebar.info("Activa 'Mostrar simulación progresiva' para usar Detener/Reanudar sobre la ejecución paso a paso.")

st.sidebar.markdown("---")

st.sidebar.button(
    "Reiniciar simulación",
    key="reiniciar",
    on_click=restart_simulation,
)

if not st.session_state["sim_started"]:
    st.write("Ajusta los parámetros y presiona 'Iniciar simulación' para ejecutar el modelo.")
    st.stop()

# ------------------------------------------------------------
# EJECUCIÓN DE LA SIMULACIÓN
# ------------------------------------------------------------

if st.session_state["sim_started"]:
    df = simular_sistema(
        alimento=alimento,
        gluten_inicial=gluten_inicial,
        carga_proceso=carga_proceso,
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
        factor_complejidad=factores_complejidad[alimento],
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
    saturado_final = bool(df["saturado"].iloc[-1])
    gluten_final = df["f(t)"].iloc[-1]
    # Determinar si la saturación fue relevante: ocurrió durante la recuperación
    # o persiste al final. Saturaciones previas al evento no se consideran críticas.
    if analisis["recupera"] and analisis["tiempo_recuperacion"] is not None:
        t_recuperacion_fin = fin_perturbacion + analisis["tiempo_recuperacion"]
        df_recuperacion = df[(df["t"] >= fin_perturbacion) & (df["t"] <= t_recuperacion_fin)]
        hubo_saturacion_relevante = bool(df_recuperacion["saturado"].any()) or saturado_final
    else:
        # Si no recupera, la calidad será FALLA de todas formas; consideramos saturación
        # relevante solo si persiste al final.
        hubo_saturacion_relevante = saturado_final

    u_raw_max = df["u_raw"].max()
    u_max = df["u(t)"].max()

    calidad_servicio = calcular_calidad_servicio(
        recupera=analisis["recupera"],
        tiempo_recuperacion=analisis["tiempo_recuperacion"]
        if analisis["tiempo_recuperacion"] is not None
        else 9999,
        tiempo_maximo_recuperacion=tiempo_maximo_recuperacion,
        hubo_saturacion=hubo_saturacion_relevante,
        saturado_final=saturado_final,
        estable=analisis["estable"],
        gluten_final=gluten_final,
        limite_anmat=limite_anmat,
    )


    # ------------------------------------------------------------
    # PANEL DE RESULTADOS
    # ------------------------------------------------------------

    st.subheader("Parámetros principales del ensayo")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Alimento", alimento)
        st.metric("Referencia Oi(t)", f"{referencia:.2f} ppm")

    with col2:
        st.metric("Gluten inicial y(0)", f"{gluten_inicial:.2f} ppm")
        st.metric("Carga de proceso L(t)", f"{carga_proceso:.2f} %")

    with col3:
        st.metric("Límite ANMAT", f"{limite_anmat:.2f} ppm")
        st.metric("Factor de complejidad", f"{factores_complejidad[alimento]:.2f}")

    with col4:
        st.metric("Kp", f"{kp:.2f}")
        st.metric("Ki", f"{ki:.2f}")
        st.metric("Kd", f"{kd:.2f}")
        st.metric("Scanner", f"{tiempo_scanner:.1f} s")


    st.subheader("Resultados finales")

    error_final = df["e(t)"].iloc[-1]
    accion_final = df["u(t)"].iloc[-1]
    estado_final = df["estado"].iloc[-1]

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric("Gluten medido final f(t)", f"{gluten_final:.2f} ppm")
        st.metric("u_raw máximo", f"{u_raw_max:.2f}")

    with col6:
        st.metric("Error final e(t)", f"{error_final:.2f} ppm")
        st.metric("u máximo", f"{u_max:.2f}")

    with col7:
        st.metric("Acción final u(t)", f"{accion_final:.2f}")
        st.metric("Saturación relevante", "SÍ" if hubo_saturacion_relevante else "NO")

    with col8:
        st.metric("Estado final", estado_final)
        st.metric("Saturación final", "SÍ" if saturado_final else "NO")


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
        st.metric("Saturación relevante", "SÍ" if hubo_saturacion_relevante else "NO")
        st.metric("Saturación final", "SÍ" if saturado_final else "NO")

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

        start_idx = st.session_state.get("progress_index", 0)
        if start_idx >= len(df):
            start_idx = len(df) - 1
            st.session_state["progress_index"] = start_idx

        for idx in range(start_idx, len(df)):
            df_animado = df.iloc[: idx + 1]
            fila = df_animado.iloc[-1]

            with placeholder_metricas.container():
                c1, c2, c3, c4, c5 = st.columns(5)

                with c1:
                    st.metric("t", f"{fila['t']:.1f} s")

                with c2:
                    st.metric("f(t)", f"{fila['f(t)']:.2f} ppm")

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

            if st.session_state.get("stop_sim", False):
                st.warning("Simulación detenida. Presione Reanudar para continuar.")
                st.session_state["progress_index"] = idx
                break

            st.session_state["progress_index"] = idx + 1
            time.sleep(velocidad_reproduccion)

        if len(df_animado) > 0:
            st.markdown("---")
            st.subheader("Resultados parciales")

            fila_parcial = df_animado.iloc[-1]
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric("Tiempo parcial", f"{fila_parcial['t']:.1f} s")
                st.metric("Muestras mostradas", f"{len(df_animado)} / {len(df)}")

            with c2:
                st.metric("Gluten medido parcial f(t)", f"{fila_parcial['f(t)']:.2f} ppm")
                st.metric("Gluten real parcial Oo(t)", f"{fila_parcial['Oo(t)']:.2f} ppm")

            with c3:
                st.metric("Error parcial e(t)", f"{fila_parcial['e(t)']:.2f} ppm")
                st.metric("Acción parcial u(t)", f"{fila_parcial['u(t)']:.2f}")

            with c4:
                st.metric("Estado parcial", fila_parcial["estado"])
                st.metric(
                    "Saturación parcial",
                    "SÍ" if bool(df_animado["saturado"].any()) else "NO",
                )
        
else:
    st.write("Ajusta los parámetros y presiona 'Iniciar simulación' para ejecutar el modelo.")


# ------------------------------------------------------------
# EXPLICACIÓN CONCEPTUAL
# ------------------------------------------------------------

st.subheader("Interpretación del modelo")

st.markdown(
    f"""
- La referencia del sistema es **Oi(t) = {referencia:.2f} ppm**.
- El límite operativo para considerar apto el alimento es **{limite_anmat:.2f} ppm**.
- La carga del proceso **L(t)** representa la complejidad o dificultad de limpieza del alimento.
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

