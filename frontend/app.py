"""
Self-Care AI — Streamlit Frontend
===================================
A clean UI for submitting daily check-ins and viewing personalized recommendations.
"""

import streamlit as st
import httpx
import os
from datetime import datetime

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Self-Care AI",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main { padding-top: 2rem; }
    .stSlider > div > div { padding-top: 0.5rem; }
    .rec-card {
        background: #f0f9f4;
        border-left: 4px solid #2e7d52;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }
    .rec-card h4 { margin: 0 0 0.4rem 0; color: #1a5c38; }
    .rec-card p  { margin: 0; color: #2d2d2d; font-size: 0.95rem; }
    .tip-card {
        background: #fff8e7;
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-top: 1rem;
    }
    .mood-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .badge-low      { background:#fee2e2; color:#991b1b; }
    .badge-medium   { background:#fef3c7; color:#92400e; }
    .badge-high     { background:#d1fae5; color:#065f46; }
    .history-row    { border-bottom: 1px solid #e5e7eb; padding: 0.5rem 0; font-size:0.88rem; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("🌿 Self-Care AI")
st.caption("Daily wellness check-in → personalized self-care plan")
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["📝 Daily Check-In", "📋 My Latest Plan", "📈 My History"])


# ── Tab 1: Check-In Form ──────────────────────────────────────────────────────

with tab1:
    st.subheader("How are you doing today?")

    with st.form("checkin_form"):
        user_id = st.text_input(
            "Your name / ID",
            value="user_demo",
            help="Used to track your history and personalize recommendations.",
        )

        col1, col2 = st.columns(2)

        with col1:
            mood = st.slider(
                "😊 Mood",
                min_value=1, max_value=10, value=5,
                help="1 = very low, 10 = excellent",
            )
            stress_level = st.slider(
                "😰 Stress Level",
                min_value=1, max_value=10, value=5,
                help="1 = no stress, 10 = extreme stress",
            )

        with col2:
            sleep_hours = st.slider(
                "😴 Sleep Last Night (hours)",
                min_value=0.0, max_value=12.0, value=7.0, step=0.5,
            )
            activity_level = st.slider(
                "🏃 Activity Level",
                min_value=1, max_value=10, value=5,
                help="1 = sedentary, 10 = very active",
            )

        note = st.text_area(
            "📝 Anything specific on your mind? (optional)",
            placeholder="e.g. Big presentation today, feeling anxious about it…",
            height=80,
        )

        submitted = st.form_submit_button(
            "✨ Get My Self-Care Plan",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if not user_id.strip():
            st.error("Please enter a user ID.")
        else:
            with st.spinner("Analyzing your check-in and generating your plan…"):
                try:
                    resp = httpx.post(
                        f"{BACKEND_URL}/api/v1/checkin",
                        json={
                            "user_id": user_id.strip(),
                            "mood": mood,
                            "sleep_hours": sleep_hours,
                            "stress_level": stress_level,
                            "activity_level": activity_level,
                            "note": note.strip() or None,
                        },
                        timeout=30,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    st.success("Your personalized plan is ready!")
                    st.session_state["last_rec"] = data
                    st.session_state["user_id"] = user_id.strip()

                    # Show inline
                    label = data["mood_label"]
                    badge_cls = f"badge-{label}"
                    st.markdown(
                        f'<span class="mood-badge {badge_cls}">Wellness state: {label.upper()}</span>',
                        unsafe_allow_html=True,
                    )

                    recs = data["recommendations"]
                    for slot, emoji in [("morning","🌅"), ("afternoon","☀️"), ("evening","🌙")]:
                        st.markdown(
                            f'<div class="rec-card"><h4>{emoji} {slot.capitalize()}</h4>'
                            f'<p>{recs[slot]}</p></div>',
                            unsafe_allow_html=True,
                        )

                    if recs.get("focus_tip"):
                        st.markdown(
                            f'<div class="tip-card"><strong>💡 Insight</strong><br>{recs["focus_tip"]}</div>',
                            unsafe_allow_html=True,
                        )

                except httpx.ConnectError:
                    st.error(
                        "Cannot reach the backend. "
                        "Make sure the FastAPI server is running on http://localhost:8000"
                    )
                except httpx.HTTPStatusError as e:
                    st.error(f"API error {e.response.status_code}: {e.response.text}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")


# ── Tab 2: Latest Plan ────────────────────────────────────────────────────────

with tab2:
    st.subheader("Your Latest Self-Care Plan")

    uid = st.text_input("Enter your user ID to fetch plan", key="rec_uid",
                        value=st.session_state.get("user_id", "user_demo"))

    if st.button("Fetch Plan", key="fetch_rec"):
        try:
            resp = httpx.get(f"{BACKEND_URL}/api/v1/recommendation/{uid.strip()}", timeout=15)
            if resp.status_code == 404:
                st.info("No recommendations yet. Submit a check-in first!")
            else:
                resp.raise_for_status()
                data = resp.json()
                st.session_state["last_rec"] = data

                label = data["mood_label"]
                badge_cls = f"badge-{label}"
                ts = data.get("generated_at", "")[:16].replace("T", " ") if data.get("generated_at") else ""

                st.markdown(
                    f'<span class="mood-badge {badge_cls}">Wellness: {label.upper()}</span>'
                    + (f" &nbsp; <small style='color:#6b7280'>Generated {ts}</small>" if ts else ""),
                    unsafe_allow_html=True,
                )

                recs = data["recommendations"]
                for slot, emoji in [("morning","🌅"), ("afternoon","☀️"), ("evening","🌙")]:
                    st.markdown(
                        f'<div class="rec-card"><h4>{emoji} {slot.capitalize()}</h4>'
                        f'<p>{recs[slot]}</p></div>',
                        unsafe_allow_html=True,
                    )

                if recs.get("focus_tip"):
                    st.markdown(
                        f'<div class="tip-card"><strong>💡 Insight</strong><br>{recs["focus_tip"]}</div>',
                        unsafe_allow_html=True,
                    )

        except httpx.ConnectError:
            st.error("Cannot reach the backend.")
        except Exception as e:
            st.error(f"Error: {e}")


# ── Tab 3: History ────────────────────────────────────────────────────────────

with tab3:
    st.subheader("Check-In History")

    uid_h = st.text_input("Enter your user ID", key="hist_uid",
                          value=st.session_state.get("user_id", "user_demo"))
    limit = st.number_input("Number of entries", min_value=1, max_value=30, value=7)

    if st.button("Load History", key="fetch_hist"):
        try:
            resp = httpx.get(
                f"{BACKEND_URL}/api/v1/history/{uid_h.strip()}",
                params={"limit": limit},
                timeout=15,
            )
            if resp.status_code == 404:
                st.info("No history yet. Submit your first check-in!")
            else:
                resp.raise_for_status()
                history = resp.json()

                # Summary metrics
                moods = [h["mood"] for h in history]
                sleeps = [h["sleep_hours"] for h in history]
                stresses = [h["stress_level"] for h in history]

                c1, c2, c3 = st.columns(3)
                c1.metric("Avg Mood", f"{sum(moods)/len(moods):.1f}/10")
                c2.metric("Avg Sleep", f"{sum(sleeps)/len(sleeps):.1f}h")
                c3.metric("Avg Stress", f"{sum(stresses)/len(stresses):.1f}/10")

                st.divider()

                # Table
                for h in history:
                    ts = str(h.get("created_at", ""))[:16].replace("T", " ")
                    label = h.get("mood_label", "—")
                    badge_cls = f"badge-{label}" if label in ("low","medium","high") else ""
                    st.markdown(
                        f'<div class="history-row">'
                        f'<b>{ts}</b> &nbsp; '
                        f'<span class="mood-badge {badge_cls}" style="padding:0.1rem 0.5rem;font-size:0.75rem">{label}</span> &nbsp; '
                        f'Mood <b>{h["mood"]}</b> · Sleep <b>{h["sleep_hours"]}h</b> · '
                        f'Stress <b>{h["stress_level"]}</b> · Activity <b>{h["activity_level"]}</b>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        except httpx.ConnectError:
            st.error("Cannot reach the backend.")
        except Exception as e:
            st.error(f"Error: {e}")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Self-Care AI · MVP · Backend: FastAPI + scikit-learn + ChromaDB + OpenAI")
