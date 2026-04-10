from __future__ import annotations

import base64
import html
import os
import sys
import time
from functools import lru_cache
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

# render replay traces in a separate streamlit ui driven by saved json events
# this module reads traces, steps replay engine state, and draws live panels

# add src to path when launched from repository root
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from visualization.replay_engine import ReplayEngine
from visualization.replay_loader import load_replay_trace
from visualization.replay_loader import load_replay_trace_from_text


TRIAGE_COLORS = {
    "red": "#c0392b",
    "yellow": "#f1c40f",
    "green": "#27ae60",
    "unknown": "#7f8c8d",
}
SPEED_OPTIONS = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
PATIENT_ASSET_PATH = Path(__file__).resolve().parents[2] / "assets" / "patient.png"
MAX_COMPLETED_TOKENS = 10
DEMO_PRESET_FILES = {
    "demo: 1 nurse": "demo_priority_1_nurse.json",
    "demo: 2 nurses": "demo_priority_2_nurses.json",
    "demo: 3 nurses": "demo_priority_3_nurses.json",
}
DEFAULT_DEMO_PRESET = "demo: 2 nurses"


def main() -> None:
    # streamlit reruns this function often, so persistent values live in session state
    st.set_page_config(page_title="hospital replay visualizer", layout="wide")
    st.title("hospital replay visualizer")

    _ensure_session_defaults()
    _render_board_styles()
    # local replay discovery keeps first-run usage simple without extra configuration
    traces_dir = Path(__file__).resolve().parents[2] / "data" / "replays"
    local_trace_files = sorted(traces_dir.glob("*.json"))

    # controls run before rendering so ui reflects any state mutations in same rerun
    _render_controls(local_trace_files)

    # engine instance in session state preserves replay position between reruns
    engine: ReplayEngine | None = st.session_state.get("engine")
    if engine is None:
        st.info("load a replay trace to begin")
        return

    # every panel reads from the same snapshot so one step updates all views consistently
    _render_overview(engine)
    _render_main_layout(engine)
    # autoplay runs last so current frame is shown before the next step is applied
    _run_autoplay(engine)


def _ensure_session_defaults() -> None:
    # initialize keys once so callback order does not cause missing-state errors
    st.session_state.setdefault("engine", None)
    st.session_state.setdefault("playing", False)
    st.session_state.setdefault("speed", 1.0)
    st.session_state.setdefault("selected_trace", "")
    st.session_state.setdefault("selected_demo_preset", DEFAULT_DEMO_PRESET)
    st.session_state.setdefault("auto_demo_loaded", False)
    st.session_state.setdefault("auto_requested_loaded", False)


def _render_controls(local_trace_files: list[Path]) -> None:
    # controls mutate replay state directly because streamlit has no long-lived loop
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 3])

    traces_by_name = {path.name: path for path in local_trace_files}

    requested_trace_raw = os.environ.get("SIM_REPLAY_TRACE", "").strip()
    if (
        st.session_state.engine is None
        and requested_trace_raw
        and not st.session_state.auto_requested_loaded
    ):
        requested_trace_path = Path(requested_trace_raw)
        if requested_trace_path.exists() and requested_trace_path.is_file():
            requested_trace = load_replay_trace(requested_trace_path)
            _load_trace_into_session(
                requested_trace,
                source_name=requested_trace_path.name,
            )
            st.session_state.selected_demo_preset = "custom"
            st.session_state.auto_requested_loaded = True
            st.rerun()
        else:
            st.session_state.auto_requested_loaded = True
    available_demo_presets = {
        label: filename
        for label, filename in DEMO_PRESET_FILES.items()
        if filename in traces_by_name
    }

    if (
        st.session_state.engine is None
        and not st.session_state.auto_demo_loaded
        and DEFAULT_DEMO_PRESET in available_demo_presets
    ):
        default_filename = available_demo_presets[DEFAULT_DEMO_PRESET]
        default_trace = load_replay_trace(traces_by_name[default_filename])
        _load_trace_into_session(default_trace, source_name=default_filename)
        st.session_state.selected_demo_preset = DEFAULT_DEMO_PRESET
        st.session_state.auto_demo_loaded = True
        st.rerun()

    preset_col, preset_load_col, preset_hint_col = st.columns([2, 1, 3])
    preset_options = ["custom"] + list(available_demo_presets.keys())
    current_preset = st.session_state.selected_demo_preset
    if current_preset not in preset_options:
        current_preset = "custom"
    selected_preset = preset_col.selectbox(
        "demo presets",
        options=preset_options,
        index=preset_options.index(current_preset),
        help="load a ready-made replay for one-click demos",
    )
    st.session_state.selected_demo_preset = selected_preset

    if preset_load_col.button(
        "load preset",
        use_container_width=True,
        disabled=selected_preset == "custom",
    ):
        preset_file = available_demo_presets.get(selected_preset)
        if preset_file is not None:
            trace = load_replay_trace(traces_by_name[preset_file])
            _load_trace_into_session(trace, source_name=preset_file)
            st.rerun()
    preset_hint_col.caption(
        "tip: pick a preset and press load preset, or use local trace/upload below"
    )

    # play flag is consumed by autoplay to emulate continuous playback over reruns
    play_label = "pause" if st.session_state.playing else "play"
    if col1.button(play_label, use_container_width=True):
        if st.session_state.engine is not None:
            st.session_state.playing = not st.session_state.playing
            st.rerun()

    # forcing pause before step guarantees button press advances exactly one event
    if col2.button("next step", use_container_width=True):
        engine: ReplayEngine | None = st.session_state.engine
        if engine is not None:
            st.session_state.playing = False
            engine.apply_next_event()
            st.rerun()

    # reset is explicit so replay can always return to a deterministic baseline
    if col3.button("reset", use_container_width=True):
        engine: ReplayEngine | None = st.session_state.engine
        if engine is not None:
            st.session_state.playing = False
            engine.reset()
            st.rerun()

    # speed scales sleep delay, which controls how quickly reruns apply events
    speed_choice = col4.selectbox(
        "speed",
        options=SPEED_OPTIONS,
        index=SPEED_OPTIONS.index(float(st.session_state.speed)),
        format_func=lambda value: f"{value:g}x",
    )
    st.session_state.speed = speed_choice

    # remember previous selection so accidental reruns do not clear user context
    file_names = list(traces_by_name.keys())
    selected_name = col5.selectbox(
        "local trace",
        options=[""] + file_names,
        index=0 if st.session_state.selected_trace not in file_names else file_names.index(st.session_state.selected_trace) + 1,
        help="choose a json trace in data/replays",
    )

    # uploader path allows ad hoc traces without touching repository files
    with st.container():
        uploader = st.file_uploader("or upload replay json", type=["json"])
        load_cols = st.columns([1, 3])
        if load_cols[0].button("load trace", use_container_width=True):
            if uploader is not None:
                # decode uploaded bytes to text because loader accepts normalized json strings
                trace = load_replay_trace_from_text(
                    uploader.getvalue().decode("utf-8")
                )
                _load_trace_into_session(trace, source_name=uploader.name)
                st.rerun()
            elif selected_name:
                # resolve by filename from discovered list to avoid unsafe path input
                trace_path = next(
                    path for path in local_trace_files if path.name == selected_name
                )
                trace = load_replay_trace(trace_path)
                _load_trace_into_session(trace, source_name=selected_name)
                st.rerun()
            else:
                st.warning("select a local trace or upload a file")


def _load_trace_into_session(trace, source_name: str) -> None:
    # replace engine to avoid mixing old replay state with newly loaded traces
    # playback is paused so the first rendered frame is always event index zero
    st.session_state.engine = ReplayEngine(trace)
    st.session_state.playing = False
    st.session_state.selected_trace = source_name


def _render_overview(engine: ReplayEngine) -> None:
    # keep progress and clock visible so stepping behavior is easy to reason about
    state = engine.state
    metadata = engine.trace.metadata
    progress_text = f"{engine.current_event_index}/{engine.total_events}"

    meta_cols = st.columns(5)
    meta_cols[0].metric("clock", f"{state.clock:.2f}")
    meta_cols[1].metric("event", progress_text)
    meta_cols[2].metric("queue length", state.queue_length)
    meta_cols[3].metric("in service", len(state.active_servers))
    meta_cols[4].metric("completed", state.total_served)

    st.caption(
        f"scenario={metadata.scenario_name} | run={metadata.run_id} | model={metadata.model} | seed={metadata.seed} | nurses={metadata.num_nurses}"
    )


def _render_main_layout(engine: ReplayEngine) -> None:
    # left side focuses on system state while right side focuses on diagnostics
    left_col, right_col = st.columns([2, 1])
    with left_col:
        _render_queue(engine)
        _render_servers(engine)
        _render_completed(engine)
    with right_col:
        _render_metrics(engine)
        _render_recent_events(engine)
        _render_side_chart(engine)


def _render_queue(engine: ReplayEngine) -> None:
    # preserve queue order because ordering is part of replay correctness
    state = engine.state
    st.subheader("queue")
    if not state.waiting_queue:
        st.markdown(
            "<div class='board-empty'>no patients currently waiting</div>",
            unsafe_allow_html=True,
        )
        return

    tokens = []
    for patient_id in state.waiting_queue:
        triage = state.patients.get(patient_id).triage if patient_id in state.patients else "unknown"
        tokens.append(_patient_token_html(patient_id, triage))
    st.markdown(
        f"<div class='token-row'>{''.join(tokens)}</div>",
        unsafe_allow_html=True,
    )


def _render_servers(engine: ReplayEngine) -> None:
    # fixed nurse row order makes server assignment changes easy to spot between steps
    state = engine.state
    st.subheader("nurses")

    station_cards = []
    for server_id in range(engine.trace.metadata.num_nurses):
        patient_id = state.active_servers.get(server_id)
        if patient_id is None:
            station_cards.append(
                (
                    "<div class='station-card'>"
                    f"<div class='station-title'>nurse {server_id}</div>"
                    "<div class='station-empty'>idle</div>"
                    "</div>"
                )
            )
        else:
            patient = state.patients.get(patient_id)
            triage = patient.triage if patient is not None else "unknown"
            station_cards.append(
                (
                    "<div class='station-card'>"
                    f"<div class='station-title'>nurse {server_id}</div>"
                    "<div class='station-body'>"
                    f"{_patient_token_html(patient_id, triage)}"
                    "</div>"
                    "</div>"
                )
            )
    st.markdown(
        f"<div class='station-grid'>{''.join(station_cards)}</div>",
        unsafe_allow_html=True,
    )


def _render_completed(engine: ReplayEngine) -> None:
    # limit to recent completions to keep panel readable on long traces
    state = engine.state
    st.subheader("completed")
    if not state.completed_patients:
        st.markdown(
            "<div class='board-empty'>no completed patients yet</div>",
            unsafe_allow_html=True,
        )
        return

    tokens = []
    for patient_id in state.completed_patients[-MAX_COMPLETED_TOKENS:]:
        triage = state.patients.get(patient_id).triage if patient_id in state.patients else "unknown"
        tokens.append(_patient_token_html(patient_id, triage, compact=True, faded=True))
    st.markdown(
        f"<div class='token-row completed-row'>{''.join(tokens)}</div>",
        unsafe_allow_html=True,
    )


def _render_metrics(engine: ReplayEngine) -> None:
    # show incremental metrics so users can validate state transitions while stepping
    state = engine.state
    st.subheader("live metrics")

    max_queue_length = 0
    if state.history:
        max_queue_length = int(max(point["queue_length"] for point in state.history))

    metric_rows = [
        {"metric": "total arrived", "value": state.total_arrived},
        {"metric": "total served", "value": state.total_served},
        {"metric": "number in system", "value": state.num_in_system},
        {"metric": "max queue length", "value": max_queue_length},
        {"metric": "running average wait", "value": round(state.running_average_wait, 3)},
        {"metric": "busy time", "value": round(state.busy_time, 3)},
    ]
    st.table(metric_rows)


def _render_recent_events(engine: ReplayEngine) -> None:
    # newest-first ordering matches user focus during play and single-step actions
    st.subheader("recent events")
    rows = []
    for event in reversed(engine.state.recent_events):
        rows.append(
            {
                "t": round(event.t, 3),
                "type": event.type,
                "patient_id": event.patient_id or "",
                "triage": event.triage or "",
                "server_id": "" if event.server_id is None else str(event.server_id),
            }
        )
    if rows:
        st.table(rows)
    else:
        st.write("none yet")


def _render_side_chart(engine: ReplayEngine) -> None:
    # chart uses per-step history snapshots so plotted trends match event progression
    # queue and completed lines provide quick sanity checks during playback
    st.subheader("queue and completion over time")
    history = engine.state.history
    if len(history) < 2:
        st.write("chart updates as events are applied")
        return

    times = [point["t"] for point in history]
    queue_lengths = [point["queue_length"] for point in history]
    completed = [point["completed"] for point in history]

    # redraw from full history each rerun so paused and stepped states are identical
    fig, axis = plt.subplots(figsize=(5.0, 3.0))
    axis.plot(times, queue_lengths, label="queue length", linewidth=2)
    axis.plot(times, completed, label="completed", linewidth=2)
    axis.set_xlabel("simulation time")
    axis.set_ylabel("count")
    axis.grid(alpha=0.2)
    axis.legend(loc="best")
    st.pyplot(fig)
    plt.close(fig)


def _patient_token_html(
    patient_id: str,
    triage: str,
    compact: bool = False,
    faded: bool = False,
) -> str:
    # render one patient token with avatar, id, and triage marker
    # queue order and station assignment come from caller ordering
    color = TRIAGE_COLORS.get(triage, TRIAGE_COLORS["unknown"])
    safe_id = html.escape(str(patient_id))
    safe_triage = html.escape(str(triage))
    size_class = "token-compact" if compact else "token-normal"
    fade_class = "token-faded" if faded else ""
    avatar = _patient_avatar_markup()
    return (
        f"<div class='patient-token {size_class} {fade_class}' style='--triage-color: {color};'>"
        f"<div class='token-avatar'>{avatar}</div>"
        f"<div class='token-info'>"
        f"<div class='token-id'>patient {safe_id}</div>"
        f"<div class='token-triage'>{safe_triage}</div>"
        "</div>"
        "<div class='token-dot'></div>"
        "</div>"
    )


def _patient_avatar_markup() -> str:
    # use local avatar image when available and fallback to emoji otherwise
    data_uri = _load_asset_data_uri(PATIENT_ASSET_PATH)
    if data_uri is not None:
        return f"<img src='{data_uri}' alt='patient avatar'/>"
    return "<span class='token-emoji'>&#x1F9D1;</span>"


@lru_cache(maxsize=8)
def _load_asset_data_uri(asset_path: Path) -> str | None:
    # inline local asset as base64 so token rendering does not depend on static hosting
    if not asset_path.exists():
        return None
    raw_bytes = asset_path.read_bytes()
    encoded = base64.b64encode(raw_bytes).decode("utf-8")
    suffix = asset_path.suffix.lower()
    mime_type = "image/png"
    if suffix in {".jpg", ".jpeg"}:
        mime_type = "image/jpeg"
    elif suffix == ".webp":
        mime_type = "image/webp"
    return f"data:{mime_type};base64,{encoded}"


def _render_board_styles() -> None:
    # inject lightweight css once per rerun for queue, station, and completion board layout
    st.markdown(
        """
        <style>
        .token-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            align-items: center;
            margin-bottom: 0.35rem;
        }
        .completed-row .patient-token {
            transform: scale(0.92);
            transform-origin: left center;
        }
        .board-empty {
            padding: 0.55rem 0.75rem;
            border: 1px dashed rgba(127, 127, 127, 0.65);
            border-radius: 0.55rem;
            color: inherit;
            font-size: 0.92rem;
            background: rgba(127, 127, 127, 0.12);
            width: fit-content;
        }
        .patient-token {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            border: 2px solid var(--triage-color);
            border-radius: 0.6rem;
            background: rgba(127, 127, 127, 0.14);
            padding: 0.3rem 0.45rem;
            color: inherit;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
            min-width: 7.3rem;
            position: relative;
        }
        .token-normal {
            font-size: 0.82rem;
        }
        .token-compact {
            font-size: 0.74rem;
            min-width: 6.5rem;
            padding: 0.24rem 0.38rem;
        }
        .token-faded {
            opacity: 0.6;
            filter: grayscale(0.12);
        }
        .token-avatar {
            width: 1.5rem;
            height: 1.5rem;
            border-radius: 50%;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(127, 127, 127, 0.16);
            border: 1px solid rgba(127, 127, 127, 0.4);
            flex-shrink: 0;
        }
        .token-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .token-emoji {
            font-size: 1.1rem;
            line-height: 1;
        }
        .token-info {
            display: flex;
            flex-direction: column;
            line-height: 1.15;
            min-width: 0;
            padding-right: 0.35rem;
        }
        .token-id {
            font-weight: 600;
            color: inherit;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .token-triage {
            color: inherit;
            opacity: 0.85;
            text-transform: lowercase;
        }
        .token-dot {
            width: 0.5rem;
            height: 0.5rem;
            border-radius: 50%;
            background: var(--triage-color);
            flex-shrink: 0;
        }
        .station-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 0.65rem;
            margin-bottom: 0.4rem;
        }
        .station-card {
            border: 1px solid rgba(127, 127, 127, 0.45);
            border-radius: 0.65rem;
            background: rgba(127, 127, 127, 0.1);
            min-height: 6.6rem;
            padding: 0.45rem;
            display: flex;
            flex-direction: column;
            gap: 0.45rem;
        }
        .station-title {
            font-weight: 600;
            color: inherit;
            font-size: 0.9rem;
            text-transform: lowercase;
        }
        .station-body {
            display: flex;
            align-items: center;
        }
        .station-empty {
            color: inherit;
            opacity: 0.85;
            font-size: 0.86rem;
            border: 1px dashed rgba(127, 127, 127, 0.55);
            border-radius: 0.45rem;
            padding: 0.4rem 0.45rem;
            width: fit-content;
            background: rgba(127, 127, 127, 0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _run_autoplay(engine: ReplayEngine) -> None:
    # autoplay advances one event per cycle to keep progression deterministic
    # sleep plus rerun simulates a timer loop in streamlit's rerun-based model
    if not st.session_state.playing:
        return
    if not engine.has_next_event():
        # end-of-trace auto-stop prevents repeated reruns with no state change
        st.session_state.playing = False
        return

    engine.apply_next_event()
    delay_seconds = max(0.05, 0.6 / float(st.session_state.speed))
    time.sleep(delay_seconds)
    st.rerun()


if __name__ == "__main__":
    main()
