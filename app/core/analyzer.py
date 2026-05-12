
import plotly.express as px
import pandas as pd


def generate_charts(df: pd.DataFrame) -> dict:
    charts = {}

    if "HeartRate" in df.columns:
        fig = px.line(df, x="date", y="HeartRate", title="Heart Rate – Last 30 Days")
        charts["heart_rate"] = fig.to_json()

    if "Active Energy" in df.columns:
        fig = px.bar(df, x="date", y="Active Energy", title="Active Energy Burned")
        charts["active_energy"] = fig.to_json()

    if "sleep_stage" in df.columns:
        stage_map = {0: "Awake", 1: "Light", 2: "REM", 3: "Deep"}
        df["sleep_label"] = df["sleep_stage"].map(stage_map)
        fig = px.histogram(df, x="sleep_label", title="Sleep Stage Distribution")
        charts["sleep"] = fig.to_json()

    return charts