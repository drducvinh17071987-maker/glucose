import streamlit as st
import numpy as np
import datetime as dt

APP_VERSION = "Glucose ET v2.1 – mean E anchored"

# ---------- ET ENGINE ----------
def compute_T_E(g_values, g_min=3.0, g_max=25.0):
    """
    Map glucose (mmol/L) into T in [0,1] and E = 1 - T^2.
    This is the only transformation used for alerts.
    """
    g = np.array(g_values, float)
    T = (g - g_min) / (g_max - g_min)
    T = np.clip(T, 0.0, 1.0)
    E = 1.0 - T**2
    return E, T

def compute_dE_pct(E):
    """
    Relative change in E between consecutive points, in %.
    """
    deltas = [None]
    for i in range(1, len(E)):
        deltas.append((E[i] - E[i-1]) / E[i-1] * 100.0)
    return deltas

# ---------- CLASSIFICATION v2.1 (ONLY E AGGREGATION) ----------
def classify_with_reason(E):
    """
    v2.1 – ET-only classifier:
    - E_pre  : E at pre-meal.
    - E_mean : mean(E) over 5 points.
    - E_mean_rel: mean(E) relative to E_pre, in %.

    Higher E_mean_rel => less contraction => better state.
    Thresholds:
      GREEN  : E_mean_rel >= 90%
      YELLOW : 75% <= E_mean_rel < 90%
      RED    : E_mean_rel < 75%
    """

    E = np.array(E, float)
    E_pre = float(E[0])
    E_min = float(np.min(E))
    E_mean = float(np.mean(E))

    if E_pre == 0:
        E_mean_rel = 100.0
    else:
        E_mean_rel = (E_mean / E_pre) * 100.0  # %

    if E_mean_rel >= 90.0:
        status = "GREEN"
        reason = (
            "GREEN – mean Bio-Time level remains close to the pre-meal state; "
            "the contraction of biological time over this meal is mild."
        )
    elif E_mean_rel >= 75.0:
        status = "YELLOW"
        reason = (
            "YELLOW – mean Bio-Time level is moderately reduced; "
            "this meal consumes a noticeable fraction of regulatory time."
        )
    else:
        status = "RED"
        reason = (
            "RED – mean Bio-Time level is markedly reduced; "
            "this meal compresses biological time and limits recovery windows."
        )

    return status, reason, E_pre, E_min, E_mean, E_mean_rel

def detailed_guidance(status):
    if status == "GREEN":
        return (
            "**Scientific guidance**\n"
            "- The overall Bio-Time level stays near the pre-meal baseline.\n"
            "- Such meals are compatible with long-term metabolic resilience.\n"
            "- Maintain fibre and protein intake; avoid excessive liquid sugars.\n"
        )
    if status == "YELLOW":
        return (
            "**Scientific guidance**\n"
            "- The system accepts a moderate Bio-Time contraction to handle this meal.\n"
            "- Repeated YELLOW patterns may accumulate subtle 'time-debt' – fatigue or brain fog after meals.\n"
            "- Reducing fast sugars and adding fibre/protein can lower the Bio-Time cost.\n"
        )
    return (
        "**Scientific guidance**\n"
        "- The meal induces a strong average contraction of biological time.\n"
        "- Recurrent RED patterns are compatible with higher metabolic and vascular stress.\n"
        "- Consider reducing high-GI and liquid carbohydrates and seeking professional advice if common.\n"
    )

# ---------- UI SETUP ----------
st.set_page_config(page_title="Relative Bio-Time Shift • Glucose Mode", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] { font-size: 86%; }
.bigstatus { font-size: 185%; font-weight: 700; }
.arrows    { font-size: 120%; font-weight: 600; }
.smallnote { font-size: 82%; color: #333; }
</style>
""", unsafe_allow_html=True)

st.title("Relative Bio-Time Shift • Glucose Mode")
st.caption(APP_VERSION)
st.markdown(
    "<div style='color:#555;font-size:90%;'>"
    "Five post-prandial glucose points describe how one meal contracts or preserves biological time."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='smallnote'>Alerts in v2.1 are derived by aggregating E from the E–T mapping only, "
    "without additional composite scores or glucose thresholds.</div>",
    unsafe_allow_html=True,
)

# ---------- INPUT LAYOUT (LEFT) ----------
left, right = st.columns([1.05, 0.95])

with left:
    st.subheader("Inputs")

    labels = ["Pre", "+30m", "+60m", "+90m", "+120m"]
    t_default = [
        dt.time(18, 0),
        dt.time(18, 30),
        dt.time(19, 0),
        dt.time(19, 30),
        dt.time(20, 0),
    ]
    g_default = [4.0, 6.0, 7.0, 6.5, 5.5]  # can be changed when demo

    glucose = []
    cols = st.columns(5)
    for i in range(5):
        with cols[i]:
            st.caption(labels[i])
            st.time_input("", value=t_default[i], key=f"time{i}")
            glucose.append(
                st.number_input(
                    "",
                    min_value=0.0,
                    max_value=40.0,
                    value=float(g_default[i]),
                    step=0.1,
                    format="%.1f",
                    key=f"glu{i}",
                )
            )

    analyze = st.button("Analyze Meal")

# ---------- OUTPUT LAYOUT (RIGHT) ----------
with right:
    if not analyze:
        st.info("Enter glucose inputs and press **Analyze Meal**.")
    else:
        E, T = compute_T_E(glucose)
        dE = compute_dE_pct(E)
        steps = dE[1:]
        net = sum([x for x in steps if x is not None])

        status, reason, E_pre, E_min, E_mean, E_mean_rel = classify_with_reason(E)

        icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}[status]
        st.markdown(
            f"<div class='bigstatus'>{icon} {status}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("**Relative Bio-Time Shift (% between points):**")
        shift_text = " → ".join([f"{x:+.1f}%" for x in steps])
        st.markdown(
            f"<div class='arrows'>{shift_text}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("**Net Bio-Time Shift for this meal:**")
        st.write(f"**{net:+.1f}% contraction** (sum of ΔE/E between points)")

        st.markdown(
            f"<div class='smallnote'>{reason}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("**E–T Summary (v2.1 mean-E anchoring):**")
        st.markdown(
            f"- E at pre-meal: **{E_pre:.3f}**  \n"
            f"- Minimum E during the meal: **{E_min:.3f}**  \n"
            f"- Mean E over all points: **{E_mean:.3f}**  \n"
            f"- Mean E relative to pre-meal: **{E_mean_rel:.1f}%**"
        )

        st.markdown("---")
        st.markdown(detailed_guidance(status))
