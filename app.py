"""QEC operational dashboard (Streamlit).

Run with:
    streamlit run app.py

The dashboard reads bundled artifacts from ``data/sample_runs/`` by default, or
any directory supplied in the sidebar. It surfaces the metrics an error-correction
operations team would watch: physical vs logical error rates, syndrome statistics,
decoder performance, and code-distance effects.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from qecdash.data_loader import DEFAULT_DATA_DIR, load_all

st.set_page_config(page_title="QEC Dashboard", layout="wide", page_icon="*")


@st.cache_data(show_spinner=False)
def _load(data_dir: str) -> dict:
    return load_all(data_dir)


def _log_axes(fig: go.Figure) -> go.Figure:
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    return fig


def render_overview(bundle: dict) -> None:
    st.subheader("Physical vs logical error rates")
    threshold = bundle.get("threshold")
    if threshold is None or threshold.empty:
        st.info("No threshold artifact found.")
        return

    estimate = bundle.get("threshold_estimate")
    columns = st.columns(4)
    columns[0].metric("Code distances", ", ".join(map(str, sorted(threshold["distance"].unique()))))
    columns[1].metric("Physical rates", f"{threshold['p'].min():.3g} - {threshold['p'].max():.3g}")
    columns[2].metric("Threshold estimate", f"{estimate:.4f}" if estimate else "n/a")
    columns[3].metric("Total shots", f"{int(threshold['num_shots'].sum()):,}")

    fig = px.line(
        threshold.sort_values("p"),
        x="p",
        y="logical_error_rate",
        color="distance",
        markers=True,
        labels={"p": "Physical error rate", "logical_error_rate": "Logical error rate"},
        title="Logical vs physical error rate by code distance",
    )
    if estimate:
        fig.add_vline(x=estimate, line_dash="dash", annotation_text=f"p_th ~ {estimate:.4f}")
    st.plotly_chart(_log_axes(fig), use_container_width=True)


def render_distance_effects(bundle: dict) -> None:
    st.subheader("Code distance effects")
    threshold = bundle.get("threshold")
    if threshold is None or threshold.empty:
        st.info("No threshold artifact found.")
        return

    available = sorted(threshold["p"].unique())
    chosen = st.select_slider("Physical error rate", options=available, value=available[0])
    subset = threshold[threshold["p"] == chosen].sort_values("distance")
    fig = px.line(
        subset,
        x="distance",
        y="logical_error_rate",
        markers=True,
        labels={"distance": "Code distance", "logical_error_rate": "Logical error rate"},
        title=f"Logical error rate vs distance at p = {chosen:.4f}",
    )
    fig.update_yaxes(type="log")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Below threshold this curve falls with distance (error suppression); "
        "above threshold it rises."
    )


def render_syndrome(bundle: dict) -> None:
    st.subheader("Syndrome statistics")
    syndrome = bundle.get("syndrome")
    if syndrome is None or syndrome.empty:
        st.info("No syndrome artifact found.")
        return

    distances = sorted(syndrome["distance"].unique())
    rates = sorted(syndrome["p"].unique())
    col_a, col_b = st.columns(2)
    distance = col_a.selectbox("Distance", distances)
    rate = col_b.selectbox("Physical error rate", rates)

    subset = syndrome[(syndrome["distance"] == distance) & (syndrome["p"] == rate)]
    if subset.empty:
        st.info("No data for that combination.")
        return

    st.metric("Mean detector firing probability", f"{subset['firing_probability'].mean():.4f}")
    fig = px.bar(
        subset,
        x="detector",
        y="firing_probability",
        labels={"detector": "Detector index", "firing_probability": "Firing probability"},
        title=f"Detector firing frequency (d={distance}, p={rate})",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_decoders(bundle: dict) -> None:
    st.subheader("Decoder performance")
    benchmark = bundle.get("benchmark")
    if benchmark is None or benchmark.empty:
        st.info("No benchmark artifact found.")
        return

    leaderboard = (
        benchmark.groupby("decoder")
        .agg(
            mean_logical_error_rate=("logical_error_rate", "mean"),
            mean_us_per_shot=("microseconds_per_shot", "mean"),
            mean_peak_kib=("peak_kib", "mean"),
            points=("logical_error_rate", "count"),
        )
        .reset_index()
        .sort_values("mean_logical_error_rate")
    )
    st.dataframe(leaderboard, use_container_width=True, hide_index=True)

    fig = px.scatter(
        leaderboard,
        x="mean_us_per_shot",
        y="mean_logical_error_rate",
        text="decoder",
        size="mean_peak_kib",
        labels={
            "mean_us_per_shot": "Mean runtime (us / shot)",
            "mean_logical_error_rate": "Mean logical error rate",
        },
        title="Accuracy vs runtime (lower-left is better)",
    )
    fig.update_traces(textposition="top center")
    st.plotly_chart(_log_axes(fig), use_container_width=True)


def render_explorer(bundle: dict) -> None:
    st.subheader("Run explorer")
    benchmark = bundle.get("benchmark")
    if benchmark is None or benchmark.empty:
        st.info("No benchmark artifact found.")
        return

    decoders = sorted(benchmark["decoder"].unique())
    chosen = st.multiselect("Decoders", decoders, default=decoders)
    filtered = benchmark[benchmark["decoder"].isin(chosen)]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="qec_runs.csv",
        mime="text/csv",
    )


def main() -> None:
    st.title("Quantum Error Correction Dashboard")
    st.caption(
        "Operational metrics for surface-code simulations: error rates, syndrome statistics, "
        "decoder performance and code-distance effects."
    )

    data_dir = st.sidebar.text_input("Data directory", value=str(DEFAULT_DATA_DIR))
    if not Path(data_dir).exists():
        st.error(f"Data directory not found: {data_dir}")
        st.stop()
    bundle = _load(data_dir)

    tabs = st.tabs(
        ["Overview", "Distance effects", "Syndrome stats", "Decoders", "Run explorer"]
    )
    with tabs[0]:
        render_overview(bundle)
    with tabs[1]:
        render_distance_effects(bundle)
    with tabs[2]:
        render_syndrome(bundle)
    with tabs[3]:
        render_decoders(bundle)
    with tabs[4]:
        render_explorer(bundle)


if __name__ == "__main__":
    main()
