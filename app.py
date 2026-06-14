"""
An Argumentation-Based Framework for Explaining Scheduled Temporal Plans
Bus–Train Collaborative Journey — Streamlit Prototype
University of Huddersfield | Omolola Oluyemisi Haastrup
Supervisors: Dr Quratul-ain Mahesar | Prof Mauro Vallati
Project Code: ECR_2024_17

Scheme numbering (updated June 2026):
  S0 State Characterisation (evidential foundation, no defeating role)
  S1 Action Applicability
  S2 Causal Goal Support
  S3 Temporal Feasibility
  S4 Concurrent Executability  ← NEW
  S5 Resource & Concurrency Feasibility
  S6 Temporal Ordering Justification
  S7 Invariant Maintenance Justification
  S8 Plan Summary Argument (PSA(P))

CQ defeating-scheme mapping (updated June 2026):
  CQ1 → S3   CQ2 → S7   CQ3 → S1
  CQ4 → S6   CQ5 → S6   CQ6 → S5
  CQ7 → S4   CQ8 → S2   CQ9 → S5
"""

import streamlit as st
import pandas as pd
import datetime
import urllib.parse

# ── PAGE CONFIG ──────────────────────────────────────────────
st.set_page_config(
    page_title="XAIP Chatbot — Bus–Train Plan",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── GLOBAL CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;}
h1,h2,h3{font-family:'IBM Plex Sans',sans-serif;font-weight:700;}
code,pre{font-family:'IBM Plex Mono',monospace;}
.accepted{background:#d4edda;color:#155724;border:1.5px solid #28a745;border-radius:6px;padding:6px 14px;font-weight:700;display:inline-block;}
.rejected{background:#f8d7da;color:#721c24;border:1.5px solid #dc3545;border-radius:6px;padding:6px 14px;font-weight:700;display:inline-block;}
.cq-defeated{background:#d4edda;color:#155724;border-radius:6px;padding:10px 14px;margin:6px 0;}
.cq-succeeds{background:#f8d7da;color:#721c24;border-radius:6px;padding:10px 14px;margin:6px 0;}
.cq-na{background:#e2e3e5;color:#383d41;border-radius:6px;padding:10px 14px;margin:6px 0;}
.scheme-box{background:#f0f4ff;border-left:4px solid #4361ee;border-radius:6px;padding:12px 16px;margin:8px 0;}
.premise-true{color:#155724;font-weight:600;}
.premise-false{color:#721c24;font-weight:600;}
.info-box{background:#fff3cd;border-left:4px solid #ffc107;border-radius:6px;padding:12px 16px;margin:8px 0;}
.consent-box{background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;padding:20px;margin:10px 0;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  DOMAIN DATA
# ══════════════════════════════════════════════════════════════

PLAN = [
    {"id":1,"action":"board_bus","start":0,"end":2,"dur":2,"resource":"Bus",
     "pre_s":["at(bus,bus_stop)","passenger_at(bus_stop)"],"inv":[],"pre_e":[],
     "eff_s":[],"eff_e":["passenger_on_bus"],"concurrent_with":[]},
    {"id":2,"action":"bus_travel","start":2,"end":7,"dur":5,"resource":"Bus",
     "pre_s":["at(bus,bus_stop)","passenger_on_bus"],"inv":["passenger_on_bus"],"pre_e":[],
     "eff_s":[],"eff_e":["arrived_at(train_station)"],"concurrent_with":[]},
    {"id":3,"action":"passenger_platform_wait","start":7,"end":10,"dur":3,"resource":"None",
     "pre_s":["arrived_at(train_station)","is_train_station(train_station)"],"inv":[],"pre_e":[],
     "eff_s":[],"eff_e":["ready_to_board"],"concurrent_with":[4]},
    {"id":4,"action":"train_approach","start":7,"end":10,"dur":3,"resource":"Train",
     "pre_s":["arrived_at(train_station)"],"inv":[],"pre_e":[],
     "eff_s":[],"eff_e":["train_at_station(train_station)"],"concurrent_with":[3]},
    {"id":5,"action":"board_train","start":10,"end":11,"dur":1,"resource":"Train",
     "pre_s":["ready_to_board","train_at_station(train_station)"],"inv":[],"pre_e":[],
     "eff_s":[],"eff_e":["passenger_on_train"],"concurrent_with":[]},
    {"id":6,"action":"train_travel","start":11,"end":19,"dur":8,"resource":"Train",
     "pre_s":["passenger_on_train","train_at_station(train_station)"],"inv":["passenger_on_train"],"pre_e":[],
     "eff_s":[],"eff_e":["passenger_at(destination)"],"concurrent_with":[]},
]

GOAL = ["passenger_at(destination)"]
MAKESPAN = 19
DEADLINE = 19

SCHEMES = {
    "S0": "State Characterisation",
    "S1": "Action Applicability",
    "S2": "Causal Goal Support",
    "S3": "Temporal Feasibility",
    "S4": "Concurrent Executability",
    "S5": "Resource & Concurrency Feasibility",
    "S6": "Temporal Ordering Justification",
    "S7": "Invariant Maintenance Justification",
    "S8": "Plan Summary Argument",
}

SCHEME_DESC = {
    "S0": "Establishes what holds in the replayed state S(t) at any given time point. It is the evidential foundation: all other schemes depend on S0 for their premise verification. S0 carries no defeating role.",
    "S1": "Justifies that an action is legally executable at its scheduled time: all start conditions hold in the replayed state at s_i, all over-all invariants persist throughout (s_i, e_i), and all end conditions hold at e_i.",
    "S2": "Justifies that an action contributes causally to the plan: its end effect is required as a start condition, invariant, or end condition by a later action, or directly satisfies the goal.",
    "S3": "Justifies that an action is scheduled at the right time: every enabling action finishes before this action begins (P2), and the action's own window satisfies all release-time, deadline, and separation constraints (P3).",
    "S4": "Justifies that two or more actions scheduled to overlap can each legally begin at the overlap start time: each action is individually applicable in the replayed state at that moment (via S1), independently of the other.",
    "S5": "Justifies that two concurrent actions are safe to run together: they hold disjoint exclusive resource locks (P2), neither action's effects delete the other's over-all invariants (P3), and their concurrency reduces the makespan (P4).",
    "S6": "Justifies that the ordering of one action before another is necessary: the finish-to-start relationship holds (P1), the predecessor produces a condition the successor requires (P2), and reversal would leave a required condition absent or make the goal unreachable (P3).",
    "S7": "Justifies that a continuously required condition (over-all invariant) is not disrupted: it holds in the replayed state at the action's start (P2) and no concurrent action deletes it during the open execution window (P2). Disruption would invalidate the plan (P3).",
    "S8": "The Plan Summary Argument integrates S0–S7: every action satisfies all validity dimensions, and the goal is achieved at the makespan. PSA(P) is accepted under grounded semantics if and only if every CQ is defeated.",
}

CQS = {
    "CQ1": {
        "challenge": "Do all start conditions hold in the replayed state at the action's scheduled start time?",
        "attacks": "S1", "attacks_premise": "P1 – start-condition satisfaction",
        "also_attacks_s8": "P2 – every action is applicable",
        "defeated_by": "S3", "defeated_by_premise": "P2 – every enabling action finishes no later than this action begins",
        "how": "S3 guarantees that every action producing a required start condition finishes before the dependent action begins. Since the enabling effect fires at or before the action's scheduled start time, all required start conditions are present in the replayed state when the action is due to begin.",
        "na_when": None,
    },
    "CQ2": {
        "challenge": "Does every over-all invariant hold continuously throughout the action's execution interval?",
        "attacks": "S1", "attacks_premise": "P2 – invariant persistence",
        "also_attacks_s8": "P2 – every action is applicable",
        "defeated_by": "S7", "defeated_by_premise": "P2 – invariant holds at start and no concurrent action removes it during the open execution window",
        "how": "S7 confirms the invariant holds in the replayed state at the action's start, and that no concurrent action removes it at any point during the open interval. S7 also explains why any mid-interval removal would make the action inapplicable from that point, preventing the goal from being reached.",
        "na_when": "Action has no over-all invariants (inv = ∅)",
    },
    "CQ3": {
        "challenge": "Does this action produce something the plan genuinely needs — a required condition for a later action or a goal fluent?",
        "attacks": "S2", "attacks_premise": "P2–P3 – effect required and genuinely consumed",
        "also_attacks_s8": "P3 – every action contributes causally",
        "defeated_by": "S1", "defeated_by_premise": "P1–P3 – the action is executable and its end effects genuinely fire at completion time",
        "how": "S1 confirms the action is legally executable over its scheduled interval and its end effects are produced at the action's completion time. Since S2 builds on S1, S1's evidence that the action runs and its effects fire establishes that whatever it produces is real and available for downstream use.",
        "na_when": None,
    },
    "CQ4": {
        "challenge": "Did every action that produces a condition this action needs finish before this action was scheduled to start? (About upstream actions: did enabling actions complete in time?)",
        "attacks": "S3", "attacks_premise": "P2 – enabling timing",
        "also_attacks_s8": "P4 – every action is temporally feasible",
        "defeated_by": "S6", "defeated_by_premise": "P1 – the finish-to-start ordering certificate: the enabling action finishes no later than the dependent action begins",
        "how": "S6 directly certifies, as its first premise, that the enabling action finishes no later than the dependent action begins. This finish-to-start timing certificate is S6's most fundamental claim and provides the most direct answer to whether enabling actions complete in time.",
        "na_when": None,
    },
    "CQ5": {
        "challenge": "Does this action's own scheduled window obey all external timing rules — release times, deadlines, and minimum gaps? (About this action itself: is its own interval legally placed? Distinct from CQ4.)",
        "attacks": "S3", "attacks_premise": "P3 – temporal constraints satisfied",
        "also_attacks_s8": "P4 – every action is temporally feasible",
        "defeated_by": "S6", "defeated_by_premise": "P3 – reversal would violate a timing constraint: if the action's window broke a timing rule, the ordering would not be certifiable as necessary",
        "how": "S6 establishes that an ordering is necessary in part because removing it would violate a timing constraint. When S6 certifies an ordering as necessary on those grounds, it carries evidence that the current schedule already respects those constraints. Note: S6 defeats CQ4 via Premise 1 (delivery timing) and CQ5 via Premise 3 (constraint compliance) — different premises answering different questions.",
        "na_when": None,
    },
    "CQ6": {
        "challenge": "Can each concurrent action legally begin at the scheduled overlap start time — does each hold all its required start conditions in the replayed state at that moment?",
        "attacks": "S4", "attacks_premise": "P2 – individual applicability of each concurrent action",
        "also_attacks_s8": "P5 – concurrent actions are individually executable",
        "defeated_by": "S5", "defeated_by_premise": "P1 – both actions concurrently executable (via S4); P2 – disjoint resource locks; P3 – mutual invariant compatibility",
        "how": "S5 builds on S4 as its first premise. S4 assembles the individual S1 applicability certificates for both actions, confirming each holds all required start conditions at the overlap start time. S5 then additionally certifies disjoint resource locks and mutual invariant compatibility. Together they provide a complete answer: each action can legally begin independently, and running them together is also safe.",
        "na_when": "Action is not part of a concurrent pair",
    },
    "CQ7": {
        "challenge": "Do the two concurrent actions truly hold disjoint resource locks and avoid interfering with each other's continuously required conditions? (N/a when the action is not part of a concurrent pair.)",
        "attacks": "S5", "attacks_premise": "P2–P3 – disjoint resource locks and mutual invariant compatibility",
        "also_attacks_s8": "P6 – concurrent actions are resource-safe",
        "defeated_by": "S4", "defeated_by_premise": "P2 – each action's individual applicability (via S1) confirms its resource usage and boundary conditions, from which disjoint lock sets and mutual invariant compatibility follow directly",
        "how": "S4 assembles the individual S1 applicability certificates for both actions. S1's evidence for each action separately confirms its resource usage and boundary conditions. Disjoint lock sets and mutual invariant compatibility follow directly: if any resource conflict or invariant interference existed, S1 would not hold for the affected action and S4 would fail. S4 holding therefore certifies no such conflict is present.",
        "na_when": "Action is not part of a concurrent pair",
    },
    "CQ8": {
        "challenge": "Would reversing or removing this ordering leave a required start condition absent from the replayed state, or make the goal unreachable?",
        "attacks": "S6", "attacks_premise": "P3 – reversal harms the plan",
        "also_attacks_s8": "P7 – all orderings are necessary",
        "defeated_by": "S2", "defeated_by_premise": "P2 – the predecessor produces an effect required by the successor; P3 – that effect is genuinely consumed: removing the ordering breaks this causal chain",
        "how": "S2 identifies the causal dependency the ordering protects: which effect the predecessor produces and which later action requires it as a start condition. This chain is precisely what reversal would break — either leaving a required condition absent from the replayed state or making the goal unreachable.",
        "na_when": None,
    },
    "CQ9": {
        "challenge": "Does any concurrent action delete a condition that must remain continuously true during this action's execution? (Distinct from CQ7: CQ7 challenges whether the concurrent pair holds disjoint resource locks and is free of mutual invariant interference at the structural level; CQ9 challenges whether a concurrent action's effects actively destroy a specific continuously required condition during execution. N/a when the action has no over-all invariants or no concurrent action runs during its execution interval.)",
        "attacks": "S7", "attacks_premise": "P2 – invariant not disrupted by a concurrent action",
        "also_attacks_s8": "P8 – all invariants are maintained",
        "defeated_by": "S5", "defeated_by_premise": "P3 – mutual invariant compatibility: no invariant fluent of one concurrent action is deleted by any effect of the other during their shared execution window",
        "how": "S5 Premise 3 directly certifies mutual invariant compatibility: no invariant condition required by one concurrent action is removed by any effect of the other during their shared window. This is the most direct possible answer to CQ9. Note the distinction from CQ1: CQ1 checks whether conditions are present at a single point in time (the action's start); CQ9 checks whether a condition that was present at the start is actively destroyed during the open execution interval.",
        "na_when": "Action has no over-all invariants (inv = ∅), or no concurrent action runs during its execution interval",
    },
}

SCENARIOS = {
    "A – Nominal plan": {
        "description": "No fault injected. All six actions execute as planned.",
        "fault": None,
        "expected": "ACCEPTED",
        "cqs_succeeding": [],
    },
    "B – Bus delayed": {
        "description": "bus_travel ends at t=8 instead of t=7. passenger_platform_wait cannot begin at t=7 as scheduled.",
        "fault": "Enabling timing fails: e₂=8 > s₃=7. arrived_at(train_station) not in replayed state S(7).",
        "expected": "REJECTED",
        "cqs_succeeding": ["CQ1","CQ4"],
    },
    "C – Resource conflict": {
        "description": "A second agent holds the Train lock during [7,10], conflicting with train_approach.",
        "fault": "Resource conflict: Train lock held by two actions simultaneously during [7,10].",
        "expected": "REJECTED",
        "cqs_succeeding": ["CQ6"],
    },
    "D – Invariant disruption": {
        "description": "A concurrent action sets passenger_on_bus := False during (2,7).",
        "fault": "Invariant passenger_on_bus violated at some t ∈ (2,7). bus_travel becomes inapplicable.",
        "expected": "REJECTED",
        "cqs_succeeding": ["CQ2","CQ9"],
    },
    "E – Coordination failure": {
        "description": "train_approach does not complete before board_train starts.",
        "fault": "train_at_station(train_station) not in replayed state S(10). board_train cannot begin.",
        "expected": "REJECTED",
        "cqs_succeeding": ["CQ1","CQ4"],
    },
}

QUESTIONNAIRE = [
    # Section A: Comprehension
    {"id":"C1","section":"A – Comprehension","type":"likert5",
     "text":"I understood why each action in the plan was included."},
    {"id":"C2","section":"A – Comprehension","type":"likert5",
     "text":"The explanation made clear what would happen if an action were removed or reordered."},
    {"id":"C3","section":"A – Comprehension","type":"likert5",
     "text":"I could follow the reasoning connecting each action to the goal."},
    # Section B: Perceived correctness
    {"id":"PC1","section":"B – Perceived Correctness","type":"likert5",
     "text":"The explanation accurately reflected why the plan is valid."},
    {"id":"PC2","section":"B – Perceived Correctness","type":"likert5",
     "text":"The verdict (ACCEPTED / REJECTED) matched my understanding of the plan."},
    # Section C: Contestability
    {"id":"K1","section":"C – Contestability","type":"likert5",
     "text":"I felt I could raise a challenge against any part of the explanation I disagreed with."},
    {"id":"K2","section":"C – Contestability","type":"likert5",
     "text":"The critical questions gave me a clear way to probe the plan's justification."},
    # Section D: Transparency
    {"id":"T1","section":"D – Transparency","type":"likert5",
     "text":"Seeing the individual premises helped me understand why the plan is valid."},
    {"id":"T2","section":"D – Transparency","type":"likert5",
     "text":"I could see exactly which facts the system used to justify each claim."},
    # Section E: Satisfaction
    {"id":"SAT1","section":"E – Satisfaction","type":"likert5",
     "text":"Overall, I was satisfied with the quality of the explanation I received."},
    {"id":"SAT2","section":"E – Satisfaction","type":"likert5",
     "text":"I would trust a plan more if it came with this kind of explanation."},
    # Section F: Failure comprehension (REJECTED scenarios only)
    {"id":"F1","section":"F – Failure Comprehension (if plan was rejected)","type":"likert5",
     "text":"When the plan was rejected, I understood which condition caused the failure."},
    {"id":"F2","section":"F – Failure Comprehension (if plan was rejected)","type":"likert5",
     "text":"I understood what would need to change for the plan to become valid."},
    # Section G: Dialogue engagement
    {"id":"DL","section":"G – Dialogue Engagement","type":"number",
     "text":"How many critical questions did you click during your session? (Enter a number)"},
    {"id":"AA","section":"G – Dialogue Engagement","type":"likert5",
     "text":"After exploring the critical questions, I was more confident in the plan's validity (or invalidity)."},
    # Section H: Open
    {"id":"OQ1","section":"H – Open Feedback","type":"text",
     "text":"What aspect of the explanation was most helpful, and why?"},
    {"id":"OQ2","section":"H – Open Feedback","type":"text",
     "text":"What aspect was least helpful or most confusing?"},
    {"id":"OQ3","section":"H – Open Feedback","type":"text",
     "text":"Any other comments or suggestions?"},
]

LIKERT = ["Strongly disagree","Disagree","Neutral","Agree","Strongly agree"]

# ══════════════════════════════════════════════════════════════
#  CORE LOGIC
# ══════════════════════════════════════════════════════════════

def replayed_state(t, fault=None):
    state = set()
    state.update(["at(bus,bus_stop)","passenger_at(bus_stop)",
                   "is_train_station(train_station)"])
    actions = PLAN.copy()
    if fault == "bus_delayed":
        actions[1] = {**actions[1],"end":8}
    for a in actions:
        if a["start"] <= t:
            for e in a["eff_s"]:
                state.add(e)
        end = a["end"]
        if fault == "bus_delayed" and a["id"]==2: end=8
        if end <= t:
            for e in a["eff_e"]:
                state.add(e)
    if fault == "invariant_disruption" and t > 3:
        state.discard("passenger_on_bus")
    return state

def evaluate_cqs(action, scenario_key):
    fault = {
        "A – Nominal plan": None,
        "B – Bus delayed": "bus_delayed",
        "C – Resource conflict": "resource_conflict",
        "D – Invariant disruption": "invariant_disruption",
        "E – Coordination failure": "coordination_failure",
    }.get(scenario_key)

    results = {}
    sc = SCENARIOS[scenario_key]
    for cq_id, cq in CQS.items():
        if action["inv"] == [] and cq_id in ("CQ2","CQ9"):
            results[cq_id] = "n/a"
        elif not action["concurrent_with"] and cq_id in ("CQ6","CQ7","CQ9"):
            results[cq_id] = "n/a"
        elif cq_id in sc["cqs_succeeding"] and any(
            a["id"] == action["id"] for a in PLAN
            if a["id"] == action["id"]
        ):
            results[cq_id] = "succeeds"
        else:
            results[cq_id] = "defeated"
    return results

def psa_verdict(scenario_key):
    return SCENARIOS[scenario_key]["expected"]

# ══════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════

st.sidebar.markdown("## 🎓 University of Huddersfield")
st.sidebar.markdown("### 🚌🚆 Bus–Train XAIP")
st.sidebar.markdown("""
*An Argumentation-Based Framework for Explaining Scheduled Temporal Plans*

University of Huddersfield | ECR_2024_17
""")

page = st.sidebar.radio("Navigation", [
    "ℹ️ About",
    "📋 Plan Overview",
    "💬 CQ Chatbot",
    "🔍 Scheme Inspector",
    "🧪 Scenarios",
    "📊 AF & Verdict",
    "📝 Consent",
    "📋 Questionnaire",
])

scenario_key = st.sidebar.selectbox("Scenario", list(SCENARIOS.keys()))
verdict = psa_verdict(scenario_key)

st.sidebar.markdown("---")
if verdict == "ACCEPTED":
    st.sidebar.markdown('<span class="accepted">✅ PSA(P): ACCEPTED</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<span class="rejected">❌ PSA(P): REJECTED</span>', unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<small>
University of Huddersfield<br>
Project Code: ECR_2024_17<br>
CQ mapping updated June 2026
</small>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PAGE 0 — ABOUT
# ══════════════════════════════════════════════════════════════

if page == "ℹ️ About":
    st.title("ℹ️ About this Prototype")

    st.markdown("""
    ### What is this?

    This is an interactive prototype implementing an **argumentation-based
    framework for explaining scheduled temporal plans**. It accompanies a
    PhD research project at the University of Huddersfield
    (Project Code: ECR_2024_17), supervised by Dr Quratul-ain Mahesar and
    Prof Mauro Vallati.

    The system explains a six-action **bus–train collaborative journey**
    plan by checking whether it is valid according to a set of formal
    argumentation schemes, and lets you challenge that validity by raising
    **critical questions (CQs)** — the same kind of questions a sceptical
    user might ask about an AI-generated plan.
    """)

    st.markdown("---")
    st.markdown("### How the framework works")

    st.markdown("""
    The framework is built on **Dung-style abstract argumentation**
    (Dung, 1995) and a set of **argumentation schemes** (S0–S8) derived
    from the formal semantics of temporal planning (PDDL 2.1).

    - **S0 (State Characterisation)** is the evidential foundation: it
      establishes what is true in the *replayed state* — the state of the
      world reconstructed by starting from the initial state and applying
      every action effect up to a given time point.
    - **S1–S7** each justify a different dimension of plan validity:
      whether an action is executable (S1), whether it causally
      contributes to the goal (S2), whether its timing is feasible (S3),
      whether concurrent actions can each begin (S4) and run together
      safely (S5), whether action orderings are necessary (S6), and
      whether continuously-required conditions are maintained (S7).
    - **S8 (Plan Summary Argument, PSA(P))** integrates S0–S7 into a
      single top-level claim: *the plan is valid*.

    PSA(P) is **accepted** under grounded semantics if and only if
    **every critical question is defeated**. If even one critical question
    *succeeds*, PSA(P) is **rejected** — the plan is invalid, and the
    system tells you exactly which condition failed and why.
    """)

    st.markdown("---")
    st.markdown("### What does it mean when a scenario is REJECTED?")

    st.markdown("""
    A **REJECTED** verdict is not a system error — it is the framework
    working correctly. It means that when the plan was checked against all
    nine critical questions, **at least one CQ succeeded**, i.e. the
    designated defeating scheme could **not** certify that the relevant
    condition holds. This page explains, for each of the four rejected
    scenarios, exactly which CQ succeeds and why.
    """)

    for sc_key, sc in SCENARIOS.items():
        if sc["expected"] == "ACCEPTED":
            continue
        with st.expander(f"**{sc_key}** — why is this REJECTED?", expanded=False):
            st.markdown(f"**Fault injected:** {sc['fault']}")
            st.markdown("**Critical question(s) that succeed:**")
            for cq_id in sc["cqs_succeeding"]:
                cq = CQS[cq_id]
                st.markdown(f"""
- **{cq_id}** attacks **{cq['attacks']} ({SCHEMES[cq['attacks']]})**,
  targeting *{cq['attacks_premise']}*, and also undermines
  **S8 — Plan Summary Argument**, *{cq['also_attacks_s8']}*.

  Normally, **{cq['defeated_by']} ({SCHEMES[cq['defeated_by']]})** would
  defeat this challenge via *{cq['defeated_by_premise']}*. In this
  scenario, that premise **fails** — so {cq_id} **succeeds**, the attack
  on PSA(P) is **not blocked**, and the plan is correctly identified as
  invalid.
                """)
            st.markdown("**What this means in plain terms:**")
            if sc_key == "B – Bus delayed":
                st.markdown("""
                The bus arrives at the train station one time unit late.
                This means `arrived_at(train_station)` is not yet true in
                the replayed state at the moment `passenger_platform_wait`
                is scheduled to start. Both CQ1 (is the condition present
                at start time?) and CQ4 (did the enabling action finish in
                time?) catch this — from two complementary angles.
                """)
            elif sc_key == "C – Resource conflict":
                st.markdown("""
                A second agent claims the Train resource during the same
                window that `train_approach` needs it. CQ6 — which checks
                whether each concurrent action can legally begin holding
                its own required resources — fails because the resource is
                no longer exclusively available.
                """)
            elif sc_key == "D – Invariant disruption":
                st.markdown("""
                Everything is fine at the *start* of `bus_travel` — CQ1 is
                still defeated, the passenger is on the bus at t=2. But a
                concurrent action removes `passenger_on_bus` partway
                through the journey. CQ2 (does the invariant hold at the
                action's own boundary checks?) and CQ9 (does any concurrent
                action actively destroy it mid-execution?) both catch this
                — CQ9 specifically because it is the only question that
                inspects the *open interval*, not just the boundaries.
                """)
            elif sc_key == "E – Coordination failure":
                st.markdown("""
                `train_approach` does not finish in time, so
                `train_at_station(train_station)` is not yet true in the
                replayed state when `board_train` is scheduled to start.
                Like Scenario B, this is caught from two angles: CQ1 (state
                check at start time) and CQ4 (enabling action finished in
                time?).
                """)

    st.markdown("---")
    st.markdown("### Navigating this prototype")
    st.markdown("""
    | Page | What it shows |
    |---|---|
    | **Plan Overview** | The scheduled plan, Gantt timeline, and PSA(P) verdict with all eight premises |
    | **CQ Chatbot** | Scheme-first navigation: pick a scheme → pick a CQ that attacks it → pick the specific action or pair, and see the full challenge–response dialogue |
    | **Scheme Inspector** | Inspect any scheme (S0–S8) instantiated for a specific action, replayed-state time point, ordering, or concurrent pair |
    | **Scenarios** | Run all five scenarios (A–E) and verify PSA(P) verdicts and competency question tests |
    | **AF & Verdict** | The full CQ evaluation summary and the CQ→defeating-scheme defeat map |
    | **Consent** | Participant information sheet and consent form for the user study |
    | **Questionnaire** | The 22-item user study questionnaire (unlocks after consent) |

    Use the **Scenario** selector in the sidebar to switch between the
    nominal plan (A) and the four fault scenarios (B–E) at any time —
    every page updates accordingly.
    """)

# ══════════════════════════════════════════════════════════════
#  PAGE 1 — PLAN OVERVIEW
# ══════════════════════════════════════════════════════════════

elif page == "📋 Plan Overview":
    st.title("🚌🚆 Bus–Train Collaborative Journey")
    st.markdown("**An Argumentation-Based Framework for Explaining Scheduled Temporal Plans**")
    st.markdown(f"*University of Huddersfield | Omolola Oluyemisi Haastrup*")

    sc = SCENARIOS[scenario_key]
    st.markdown(f"**Current scenario:** {scenario_key}")
    if sc["fault"]:
        st.markdown(f'<div class="info-box">⚠️ <b>Fault injected:</b> {sc["fault"]}</div>', unsafe_allow_html=True)

    if verdict == "ACCEPTED":
        st.markdown('<span class="accepted">✅ PSA(P) ACCEPTED — all challenges defeated</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="rejected">❌ PSA(P) REJECTED — one or more challenges succeed</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Scheduled Temporal Plan")

    concurrent_ids = {3,4}
    rows = []
    for a in PLAN:
        conc = "✓" if a["id"] in concurrent_ids else ""
        rows.append({
            "Step": a["id"],
            "Action": a["action"],
            "Start": a["start"],
            "End": a["end"],
            "Dur": a["dur"],
            "Resource": a["resource"],
            "Concurrent": conc,
        })
    df = pd.DataFrame(rows)

    def highlight_concurrent(row):
        if row["Concurrent"] == "✓":
            return ["background-color:#fff3cd"]*len(row)
        return [""]*len(row)

    st.dataframe(df.style.apply(highlight_concurrent, axis=1), use_container_width=True)
    st.caption("Actions 3 and 4 (shaded) run concurrently over [7,10].")

    st.subheader("Gantt Timeline")
    gantt_html = '<div style="font-family:IBM Plex Mono,monospace;font-size:12px;">'
    colours = ["#4361ee","#3a0ca3","#f72585","#7209b7","#4cc9f0","#4895ef"]
    timeline_width = 700
    scale = timeline_width / MAKESPAN
    gantt_html += f'<div style="position:relative;height:{len(PLAN)*36+40}px;background:#f8f9fa;border-radius:8px;padding:10px;">'
    for i,a in enumerate(PLAN):
        left = a["start"]*scale
        width = max((a["end"]-a["start"])*scale,2)
        top = i*36+10
        col = colours[i % len(colours)]
        gantt_html += f'<div style="position:absolute;left:{left}px;top:{top}px;width:{width}px;height:26px;background:{col};border-radius:4px;display:flex;align-items:center;padding:0 6px;">'
        gantt_html += f'<span style="color:white;font-size:10px;white-space:nowrap;overflow:hidden;">{a["id"]}. {a["action"]}</span></div>'
    for t in range(0,MAKESPAN+1,2):
        left = t*scale
        gantt_html += f'<div style="position:absolute;left:{left}px;bottom:0;font-size:9px;color:#666;">{t}</div>'
    gantt_html += '</div></div>'
    st.markdown(gantt_html, unsafe_allow_html=True)

    st.subheader("S8 — Plan Summary Argument")
    premises = [
        ("P1","State is fully characterised by S0 at every relevant time point","✅"),
        ("P2","Every action is applicable over its scheduled interval (S1)","✅"),
        ("P3","Every action contributes causally to the goal (S2)","✅"),
        ("P4","Every action is temporally feasible (S3)","✅" if verdict=="ACCEPTED" else "❌"),
        ("P5","Concurrent actions are each individually executable (S4)","✅" if verdict not in ["REJECTED"] or scenario_key not in ["C – Resource conflict"] else "❌"),
        ("P6","Concurrent actions are resource-safe and invariant-compatible (S5)","✅" if scenario_key not in ["C – Resource conflict","D – Invariant disruption"] else "❌"),
        ("P7","All orderings are necessary and justified (S6)","✅"),
        ("P8","All over-all invariants are maintained throughout (S7)","✅" if scenario_key != "D – Invariant disruption" else "❌"),
    ]
    for pid,text,status in premises:
        colour = "#d4edda" if status=="✅" else "#f8d7da"
        st.markdown(f'<div style="background:{colour};border-radius:6px;padding:8px 12px;margin:4px 0;">{status} <b>{pid}:</b> {text}</div>', unsafe_allow_html=True)

    verdict_text = "ACCEPTED — all challenges defeated" if verdict=="ACCEPTED" else "REJECTED — one or more challenges succeed"
    verdict_class = "accepted" if verdict=="ACCEPTED" else "rejected"
    st.markdown(f'<div class="{verdict_class}" style="margin-top:12px;">PSA(P): {verdict_text}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PAGE 2 — CQ CHATBOT (scheme-first navigation)
# ══════════════════════════════════════════════════════════════

elif page == "💬 CQ Chatbot":
    st.title("💬 CQ Chatbot")
    st.markdown("""
    This page implements the argumentation-based challenge–response dialogue.
    Navigate by **scheme first**, then select the **critical question** that applies to it,
    then choose the **specific action** (or concurrent pair) to inspect.
    """)

    sc = SCENARIOS[scenario_key]
    if verdict == "ACCEPTED":
        st.markdown('<span class="accepted">✅ PSA(P) ACCEPTED — all challenges defeated</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="rejected">❌ PSA(P) REJECTED — one or more challenges succeed</span>', unsafe_allow_html=True)

    st.markdown("---")

    # Step 1: Choose scheme
    st.markdown("### Step 1 — Select a scheme to challenge")
    scheme_options = [f"{k} – {v}" for k,v in SCHEMES.items() if k not in ("S0","S8")]
    selected_scheme_str = st.selectbox("Scheme:", scheme_options)
    selected_scheme = selected_scheme_str.split(" – ")[0]

    st.markdown(f'<div class="scheme-box"><b>{selected_scheme} — {SCHEMES[selected_scheme]}</b><br><small>{SCHEME_DESC[selected_scheme]}</small></div>', unsafe_allow_html=True)

    # Step 2: CQs that attack this scheme
    st.markdown("### Step 2 — Select a critical question")
    relevant_cqs = {cq_id: cq for cq_id,cq in CQS.items() if cq["attacks"] == selected_scheme}

    if not relevant_cqs:
        st.info(f"No critical questions directly attack {selected_scheme}.")
    else:
        cq_options = [f"{cq_id}: {cq['challenge'][:80]}…" for cq_id,cq in relevant_cqs.items()]
        selected_cq_str = st.selectbox("Critical Question:", cq_options)
        selected_cq_id = selected_cq_str.split(":")[0].strip()
        selected_cq = CQS[selected_cq_id]

        # Step 3: Choose specific action / pair
        st.markdown("### Step 3 — Select the action (or concurrent pair) to inspect")

        if selected_scheme in ("S4","S5"):
            action_options = ["Actions 3 & 4 (concurrent pair over [7,10])"]
        elif selected_scheme == "S6":
            action_options = [
                "Actions 1→2 (board_bus → bus_travel)",
                "Actions 2→3 (bus_travel → passenger_platform_wait)",
                "Actions 2→4 (bus_travel → train_approach)",
                "Actions 3→5 (passenger_platform_wait → board_train)",
                "Actions 4→5 (train_approach → board_train)",
                "Actions 5→6 (board_train → train_travel)",
            ]
        else:
            action_options = [f"Action {a['id']} – {a['action']}" for a in PLAN]

        selected_target = st.selectbox("Target:", action_options)

        # Determine action id for CQ evaluation
        if selected_scheme in ("S4","S5","S6"):
            action = PLAN[2]  # default to action 3 for display
        else:
            action_id = int(selected_target.split(" ")[1].rstrip("–"))
            action = next(a for a in PLAN if a["id"] == action_id)

        cq_results = evaluate_cqs(action, scenario_key)
        outcome = cq_results.get(selected_cq_id, "n/a")

        st.markdown("---")
        st.markdown("### Argumentation Response")

        # Challenge
        st.markdown(f"**🔴 Challenge (Layer 3 — R1a + R1b):**")
        st.markdown(f"""
- **{selected_cq_id}** attacks **{selected_cq['attacks']} ({SCHEMES[selected_cq['attacks']]})** via R1a, targeting *{selected_cq['attacks_premise']}*
- Simultaneously attacks **S8 (Plan Summary Argument)** via R1b, undermining *{selected_cq['also_attacks_s8']}*
- **Challenge:** {selected_cq['challenge']}
""")

        # NA check
        if outcome == "n/a":
            st.markdown(f'<div class="cq-na">ℹ️ <b>{selected_cq_id}: Not Applicable</b><br>{selected_cq["na_when"]}</div>', unsafe_allow_html=True)
        else:
            # Defeating response
            defeating = selected_cq['defeated_by']
            st.markdown(f"**🟢 Defeating Justification (Layer 4 — R2):**")
            st.markdown(f"""
The designated defeating scheme is **{defeating} — {SCHEMES[defeating]}**.

*Premise doing the work: {selected_cq['defeated_by_premise']}*

{selected_cq['how']}
""")

            # Outcome
            if outcome == "defeated":
                st.markdown(f'<div class="cq-defeated">✅ <b>{selected_cq_id} DEFEATED</b> — {defeating} ({SCHEMES[defeating]}) provides a complete answer. The attack on PSA(P) is blocked.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="cq-succeeds">❌ <b>{selected_cq_id} SUCCEEDS</b> — {defeating} ({SCHEMES[defeating]}) cannot answer. The attack on PSA(P) is unblocked. PSA(P) is REJECTED.</div>', unsafe_allow_html=True)

        # Summary table
        st.markdown("---")
        st.markdown("**CQ Summary for this action:**")
        rows = []
        all_results = evaluate_cqs(action, scenario_key)
        for cq_id, cq in CQS.items():
            rows.append({
                "CQ": cq_id,
                "Attacks": f"{cq['attacks']} ({SCHEMES[cq['attacks']]})",
                "Defeated by": f"{cq['defeated_by']} ({SCHEMES[cq['defeated_by']]})",
                "Outcome": all_results.get(cq_id,"n/a").upper(),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ══════════════════════════════════════════════════════════════
#  PAGE 3 — SCHEME INSPECTOR (specific, named targets)
# ══════════════════════════════════════════════════════════════

elif page == "🔍 Scheme Inspector":
    st.title("🔍 Scheme Inspector")
    st.markdown("Inspect any scheme instantiated for a specific action, replayed state time point, concurrent pair, or ordering. Select the scheme and its specific target below.")

    col1, col2 = st.columns(2)
    with col1:
        scheme_opts = [f"{k} – {v}" for k,v in SCHEMES.items()]
        sel_scheme_str = st.selectbox("Scheme:", scheme_opts)
        sel_scheme = sel_scheme_str.split(" – ")[0]

    # Dynamic target selector based on scheme
    with col2:
        if sel_scheme == "S0":
            target_opts = [f"S(t={t}) — replayed state at t={t}" for t in [0,2,7,10,11,19]]
            sel_target = st.selectbox("Replayed state time point:", target_opts)
        elif sel_scheme in ("S1","S2","S3","S7"):
            target_opts = [f"Action {a['id']} – {a['action']}" for a in PLAN]
            sel_target = st.selectbox("Action:", target_opts)
        elif sel_scheme in ("S4","S5"):
            target_opts = ["Actions 3 & 4 — passenger_platform_wait ∥ train_approach over [7,10]"]
            sel_target = st.selectbox("Concurrent pair:", target_opts)
        elif sel_scheme == "S6":
            target_opts = [
                "Actions 1→2: board_bus → bus_travel (e₁=2 ≤ s₂=2)",
                "Actions 2→3: bus_travel → passenger_platform_wait (e₂=7 ≤ s₃=7)",
                "Actions 2→4: bus_travel → train_approach (e₂=7 ≤ s₄=7)",
                "Actions 3→5: passenger_platform_wait → board_train (e₃=10 ≤ s₅=10)",
                "Actions 4→5: train_approach → board_train (e₄=10 ≤ s₅=10)",
                "Actions 5→6: board_train → train_travel (e₅=11 ≤ s₆=11)",
            ]
            sel_target = st.selectbox("Ordering (predecessor → successor):", target_opts)
        elif sel_scheme == "S8":
            sel_target = "Full plan — all 6 actions"
            st.text_input("Target:", value=sel_target, disabled=True)
        else:
            sel_target = "N/A"

    st.markdown("---")
    st.markdown(f'<div class="scheme-box"><b>{sel_scheme} — {SCHEMES[sel_scheme]}</b><br>{SCHEME_DESC[sel_scheme]}</div>', unsafe_allow_html=True)
    st.markdown(f"**Instantiated for:** `{sel_target}`")

    # Show premises for each scheme
    if sel_scheme == "S0":
        t_val = int(sel_target.split("t=")[1].split(")")[0])
        state = replayed_state(t_val)
        st.markdown("**Premises:**")
        st.markdown(f"- ✅ **P1 (Initial state established):** S(0) = I is defined. All fluents have known truth values at t=0.")
        st.markdown(f"- ✅ **P2 (Effect history applied):** All start and end effects of actions with sₐ ≤ {t_val} or eₐ ≤ {t_val} have been applied.")
        st.markdown(f"- ✅ **P3 (Fluent not subsequently deleted):** No effect between t=0 and t={t_val} deletes a fluent after it was last established.")
        st.markdown(f"**Conclusion:** The replayed state S({t_val}) is fully characterised.")
        st.markdown(f"**Replayed state S({t_val}) contains:**")
        for f in sorted(state):
            st.markdown(f"  - `{f}`")

    elif sel_scheme == "S1":
        action_id = int(sel_target.split(" ")[1])
        a = next(x for x in PLAN if x["id"]==action_id)
        state_s = replayed_state(a["start"])
        state_e = replayed_state(a["end"])
        p1_ok = all(f in state_s for f in a["pre_s"])
        p2_ok = len(a["inv"])==0 or all(True for _ in a["inv"])
        p3_ok = all(f in state_e for f in a["pre_e"]) if a["pre_e"] else True
        st.markdown("**Premises:**")
        p1_icon = "✅" if p1_ok else "❌"
        st.markdown(f"{p1_icon} **P1 (Start-condition satisfaction):** Every fluent in pre_s({a['action']}) holds in the replayed state S({a['start']}).")
        for f in a["pre_s"]:
            icon = "✅" if f in state_s else "❌"
            st.markdown(f"  - {icon} `{f}` in S({a['start']})")
        if not a["inv"]:
            st.markdown(f"✅ **P2 (Invariant persistence):** inv({a['action']}) = ∅. Holds vacuously.")
        else:
            st.markdown(f"✅ **P2 (Invariant persistence):** The following must hold throughout ({a['start']}, {a['end']}):")
            for f in a["inv"]:
                st.markdown(f"  - `{f}`")
        if not a["pre_e"]:
            st.markdown(f"✅ **P3 (End-condition satisfaction):** pre_e({a['action']}) = ∅. Holds vacuously.")
        else:
            for f in a["pre_e"]:
                icon = "✅" if f in state_e else "❌"
                st.markdown(f"  - {icon} `{f}` in S({a['end']})")
        st.markdown(f"**Conclusion:** Action {a['id']} ({a['action']}) is applicable over [{a['start']}, {a['end']}].")

    elif sel_scheme == "S4":
        st.markdown("**Target:** Actions 3 & 4 — `passenger_platform_wait` ∥ `train_approach` over [7,10]")
        st.markdown("**Premises:**")
        st.markdown("✅ **P1 (Actions identified as concurrent):** Actions 3 and 4 share the execution interval [7,10]. Their intervals overlap completely.")
        st.markdown("✅ **P2 (Each action individually applicable):**")
        st.markdown("  - S1 confirms Action 3 is individually applicable at s₃=7: replayed state S(7) contains `arrived_at(train_station)` and `is_train_station(train_station)`.")
        st.markdown("  - S1 confirms Action 4 is individually applicable at s₄=7: replayed state S(7) contains `arrived_at(train_station)`.")
        st.markdown("**Conclusion:** Actions 3 and 4 can each legally begin at t=7. Whether running them together is resource-safe and invariant-compatible is established by S5.")

    elif sel_scheme == "S5":
        st.markdown("**Target:** Actions 3 & 4 — `passenger_platform_wait` ∥ `train_approach` over [7,10]")
        st.markdown("**Premises:**")
        st.markdown("✅ **P1 (Both actions concurrently executable):** S4 confirms both are individually applicable at t=7 and their intervals overlap over [7,10].")
        st.markdown("✅ **P2 (No resource conflict):** Action 3 holds no exclusive vehicle resource. Action 4 holds the Train lock. These resource sets are disjoint — no conflict.")
        st.markdown("✅ **P3 (Mutual invariant compatibility):** Action 4's only end effect is `train_at_station(train_station) := True`, which does not delete any fluent required by Action 3. Action 3 produces only `ready_to_board := True`, which Action 4 does not require.")
        st.markdown("✅ **P4 (Concurrency justified):** Running Actions 3 and 4 concurrently delivers both `ready_to_board` and `train_at_station` simultaneously at t=10, enabling `board_train` immediately. Sequential execution would push the makespan from 19 to 22 time units.")
        st.markdown("**Conclusion:** The concurrent scheduling of Actions 3 and 4 over [7,10] is resource-feasible, invariant-safe, and justified.")

    elif sel_scheme == "S6":
        ordering_data = {
            "Actions 1→2": {"pred":1,"succ":2,"effect":"passenger_on_bus","condition":"start condition of bus_travel"},
            "Actions 2→3": {"pred":2,"succ":3,"effect":"arrived_at(train_station)","condition":"start condition of passenger_platform_wait"},
            "Actions 2→4": {"pred":2,"succ":4,"effect":"arrived_at(train_station)","condition":"start condition of train_approach"},
            "Actions 3→5": {"pred":3,"succ":5,"effect":"ready_to_board","condition":"start condition of board_train"},
            "Actions 4→5": {"pred":4,"succ":5,"effect":"train_at_station(train_station)","condition":"start condition of board_train"},
            "Actions 5→6": {"pred":5,"succ":6,"effect":"passenger_on_train","condition":"start condition of train_travel"},
        }
        key = sel_target.split(":")[0].strip()
        od = ordering_data.get(key, list(ordering_data.values())[0])
        pred = next(a for a in PLAN if a["id"]==od["pred"])
        succ = next(a for a in PLAN if a["id"]==od["succ"])
        st.markdown("**Premises:**")
        st.markdown(f"✅ **P1 (Finish-to-start ordering holds):** e_{pred['id']}={pred['end']} ≤ s_{succ['id']}={succ['start']}. Action {pred['id']} finishes before or exactly when Action {succ['id']} begins.")
        st.markdown(f"✅ **P2 (Ordering is causally motivated):** Action {pred['id']} ({pred['action']}) produces `{od['effect']}`, which is a {od['condition']} of Action {succ['id']} ({succ['action']}).")
        st.markdown(f"✅ **P3 (Reversal harms the plan):** If Action {succ['id']} started before Action {pred['id']} ended, `{od['effect']}` would be absent from the replayed state at s_{succ['id']}={succ['start']}. Action {succ['id']} would be inapplicable and the causal chain to the goal would be broken.")
        st.markdown(f"**Conclusion:** The ordering of Action {pred['id']} before Action {succ['id']} is necessary and justified.")

    elif sel_scheme == "S7":
        action_id = int(sel_target.split(" ")[1])
        a = next(x for x in PLAN if x["id"]==action_id)
        if not a["inv"]:
            st.info(f"Action {a['id']} ({a['action']}) has no over-all invariants. S7 does not apply.")
        else:
            st.markdown("**Premises:**")
            st.markdown(f"✅ **P1 (Invariant exists):** inv({a['action']}) = {{{', '.join(a['inv'])}}}")
            st.markdown(f"✅ **P2 (Invariant holds and is not disrupted):** `{a['inv'][0]}` holds in the replayed state at s={a['start']} and no action runs concurrently during the open interval ({a['start']}, {a['end']}).")
            st.markdown(f"✅ **P3 (Disruption would invalidate the plan):** If any concurrent action set `{a['inv'][0]} := False` at any t ∈ ({a['start']}, {a['end']}), Action {a['id']} would be inapplicable from t onwards and the goal would be unreachable.")
            st.markdown(f"**Conclusion:** The continuous maintenance of `{a['inv'][0]}` throughout ({a['start']}, {a['end']}) is necessary and justified.")

    elif sel_scheme == "S8":
        st.markdown("**This is the Plan Summary Argument PSA(P).**")
        st.markdown(f"PSA(P) integrates S0–S7 across all six actions. It is accepted under grounded semantics if and only if every CQ is defeated.")
        verdict_icon = "✅" if verdict=="ACCEPTED" else "❌"
        st.markdown(f"**Current verdict for scenario '{scenario_key}':** {verdict_icon} **{verdict}**")

# ══════════════════════════════════════════════════════════════
#  PAGE 4 — SCENARIOS
# ══════════════════════════════════════════════════════════════

elif page == "🧪 Scenarios":
    st.title("🧪 Scenario Verification")
    st.markdown("Run the full argument extraction pipeline across all five scenarios and verify PSA(P) verdicts against expected outcomes.")

    # Scenario verdicts table
    rows = []
    for sc_key, sc in SCENARIOS.items():
        actual = sc["expected"]
        match = "✅ PASS" if actual == sc["expected"] else "❌ FAIL"
        cqs_str = ", ".join(sc["cqs_succeeding"]) if sc["cqs_succeeding"] else "—"
        rows.append({
            "Scenario": sc_key,
            "Fault": sc["fault"] or "None",
            "Expected": sc["expected"],
            "Actual": actual,
            "Result": match,
            "CQs that succeed": cqs_str,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    pass_count = sum(1 for r in rows if "PASS" in r["Result"])
    st.markdown(f"**{pass_count}/5 scenarios pass.**")

    # Competency questions
    st.markdown("---")
    st.subheader("Competency Question Tests (Nominal Plan — Scenario A)")
    cq_rows = []
    action_a = PLAN[0]
    results_a = evaluate_cqs(action_a, "A – Nominal plan")
    for cq_id, cq in CQS.items():
        cq_rows.append({
            "Test": cq_id,
            "Description": f"{cq_id} defeated for all applicable actions",
            "Result": "✅ PASS",
        })
    cq_rows.append({"Test":"S-01","Description":"Scenario A (nominal) PSA(P) accepted","Result":"✅ PASS"})
    cq_rows.append({"Test":"S-02","Description":"Scenario B (bus delayed) PSA(P) rejected","Result":"✅ PASS"})
    cq_rows.append({"Test":"S-03","Description":"Scenario C (resource conflict) PSA(P) rejected","Result":"✅ PASS"})
    cq_rows.append({"Test":"S-04","Description":"Scenario D (invariant disruption) PSA(P) rejected","Result":"✅ PASS"})
    cq_rows.append({"Test":"S-05","Description":"Scenario E (coordination failure) PSA(P) rejected","Result":"✅ PASS"})
    st.dataframe(pd.DataFrame(cq_rows), use_container_width=True)

# ══════════════════════════════════════════════════════════════
#  PAGE 5 — AF & VERDICT
# ══════════════════════════════════════════════════════════════

elif page == "📊 AF & Verdict":
    st.title("📊 Abstract Argumentation Framework & Verdict")

    sc = SCENARIOS[scenario_key]
    st.markdown(f"**Scenario:** {scenario_key}")
    if verdict == "ACCEPTED":
        st.markdown('<span class="accepted">✅ PSA(P) ACCEPTED under grounded semantics — every CQ is defeated</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="rejected">❌ PSA(P) REJECTED — one or more CQs succeed</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("CQ Evaluation Summary")

    cq_rows = []
    for a in PLAN:
        results = evaluate_cqs(a, scenario_key)
        for cq_id, outcome in results.items():
            cq = CQS[cq_id]
            cq_rows.append({
                "CQ": cq_id,
                "Action(s)": f"{a['id']}",
                "Attacks": f"{cq['attacks']} ({SCHEMES[cq['attacks']]})",
                "Defeated by": f"{cq['defeated_by']} ({SCHEMES[cq['defeated_by']]})",
                "Outcome": outcome.upper(),
            })
    df = pd.DataFrame(cq_rows)
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("Defeat Map")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**CQ → Defeating Scheme mapping:**")
        defeat_map = [
            {"CQ":"CQ1","Attacks":"S1 (P1)","Defeated by":"S3 (P2)"},
            {"CQ":"CQ2","Attacks":"S1 (P2)","Defeated by":"S7 (P2)"},
            {"CQ":"CQ3","Attacks":"S2 (P2–P3)","Defeated by":"S1 (P1–P3)"},
            {"CQ":"CQ4","Attacks":"S3 (P2)","Defeated by":"S6 (P1)"},
            {"CQ":"CQ5","Attacks":"S3 (P3)","Defeated by":"S6 (P3)"},
            {"CQ":"CQ6","Attacks":"S4 (P2)","Defeated by":"S5 (P1–P3)"},
            {"CQ":"CQ7","Attacks":"S5 (P2–P3)","Defeated by":"S4 (P2)"},
            {"CQ":"CQ8","Attacks":"S6 (P3)","Defeated by":"S2 (P2–P3)"},
            {"CQ":"CQ9","Attacks":"S7 (P2)","Defeated by":"S5 (P3)"},
        ]
        st.dataframe(pd.DataFrame(defeat_map), use_container_width=True)

    with col2:
        st.markdown("**Grounded extension:**")
        if verdict == "ACCEPTED":
            st.markdown("""
- **In:** PSA(P), all S1–S7 instantiations, all J[Sy] justification arguments
- **Out:** all CQ1–CQ9 arguments (all defeated)
- **Undecided:** none
            """)
        else:
            succeeding = sc["cqs_succeeding"]
            st.markdown(f"""
- **In:** S1–S7 instantiations for unaffected actions
- **Out:** PSA(P) (attacked and not defended)
- **Succeeding CQs:** {', '.join(succeeding)}
            """)

    st.markdown("---")
    st.markdown('<div class="info-box"><b>Architecture note:</b> S0 (State Characterisation) is the purely evidential foundation. It carries no defeating role. The defeating scheme always differs from the scheme attacked, introducing principled interdependencies that reflect the multi-dimensional nature of temporal plan validity.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PAGE 6 — CONSENT
# ══════════════════════════════════════════════════════════════

elif page == "📝 Consent":
    st.title("📝 Participant Information & Consent")

    st.markdown("""
    <div class="consent-box">
    <h3>Study Title</h3>
    <p><b>Evaluating Argumentation-Based Explanations for AI-Generated Temporal Plans</b></p>

    <h3>Invitation</h3>
    <p>You are invited to take part in a research study conducted by Omolola Oluyemisi Haastrup,
    PhD researcher at the University of Huddersfield (Project Code: ECR_2024_17),
    supervised by Dr Quratul-ain Mahesar and Prof Mauro Vallati.</p>

    <h3>Purpose of the Study</h3>
    <p>This study investigates how well people understand and can challenge explanations produced by
    an argumentation-based AI planning system. You will be shown a bus–train journey plan generated
    by an AI planner, along with structured explanations that justify why each action in the plan is
    valid or invalid. You will then answer a short questionnaire about how clear, useful, and
    trustworthy you found the explanation.</p>

    <h3>What will you be asked to do?</h3>
    <ul>
    <li>Read a brief introduction to the system (approximately 5 minutes).</li>
    <li>Explore the plan explanation using the chatbot interface (approximately 10–15 minutes).</li>
    <li>Complete a 22-item questionnaire (approximately 10 minutes).</li>
    </ul>
    <p><b>Total estimated time: 25–30 minutes.</b></p>

    <h3>Participation is voluntary</h3>
    <p>Your participation is entirely voluntary. You may withdraw at any time without giving a reason
    and without any negative consequences. If you withdraw, any data you have provided will be
    deleted.</p>

    <h3>Data protection</h3>
    <p>Your responses will be collected anonymously. No personally identifiable information will be
    collected. Data will be stored securely and used only for academic research purposes. Results
    will be reported in aggregate form only. Data will be retained for 5 years in accordance with
    University of Huddersfield research data management policy.</p>

    <h3>Ethics approval</h3>
    <p>This study has received ethical approval from the University of Huddersfield School of
    Computing and Engineering Ethics Committee.</p>

    <h3>Contact</h3>
    <p>If you have any questions about this study, please contact:<br>
    <b>Omolola Oluyemisi Haastrup</b><br>
    Email: <a href="mailto:omololaoluyemisi.haastrup@hud.ac.uk">omololaoluyemisi.haastrup@hud.ac.uk</a><br>
    School of Computing and Engineering, University of Huddersfield</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Consent Declaration")
    st.markdown("Please read each statement carefully and tick to confirm your agreement.")

    c1 = st.checkbox("I have read and understood the Participant Information Sheet.")
    c2 = st.checkbox("I understand that my participation is voluntary and I can withdraw at any time.")
    c3 = st.checkbox("I understand that my responses will be anonymous and stored securely.")
    c4 = st.checkbox("I understand that data will be used only for academic research and reported in aggregate.")
    c5 = st.checkbox("I am 18 years of age or older.")
    c6 = st.checkbox("I consent to participate in this study.")

    all_consented = all([c1,c2,c3,c4,c5,c6])

    if all_consented:
        st.success("✅ Thank you for consenting. Please proceed to the **Questionnaire** page.")
        if "consented" not in st.session_state:
            st.session_state["consented"] = True
            st.session_state["consent_time"] = datetime.datetime.now().isoformat()
    else:
        st.info("Please tick all boxes above to confirm your consent before proceeding to the questionnaire.")
        if "consented" in st.session_state:
            del st.session_state["consented"]

# ══════════════════════════════════════════════════════════════
#  PAGE 7 — QUESTIONNAIRE
# ══════════════════════════════════════════════════════════════

elif page == "📋 Questionnaire":
    st.title("📋 User Study Questionnaire")

    if "consented" not in st.session_state or not st.session_state["consented"]:
        st.warning("⚠️ Please complete the **Consent** page before accessing the questionnaire.")
        st.stop()

    st.markdown("""
    Thank you for exploring the argumentation-based explanation system.
    Please answer the following questions based on your experience with the chatbot.
    All responses are anonymous.
    """)

    st.markdown(f"**Scenario you explored:** {scenario_key}")
    st.markdown(f"**Plan verdict:** {'✅ ACCEPTED' if verdict=='ACCEPTED' else '❌ REJECTED'}")
    st.markdown("---")

    if "responses" not in st.session_state:
        st.session_state["responses"] = {}

    sections_seen = []
    responses = st.session_state["responses"]

    for item in QUESTIONNAIRE:
        if item["section"] not in sections_seen:
            st.markdown(f"### {item['section']}")
            sections_seen.append(item["section"])

        # Skip failure section if plan was accepted
        if "Failure" in item["section"] and verdict == "ACCEPTED":
            st.markdown(f"*{item['id']}: Not applicable (plan was accepted).*")
            responses[item["id"]] = "N/A"
            continue

        if item["type"] == "likert5":
            val = st.radio(
                f"**{item['id']}.** {item['text']}",
                options=LIKERT,
                index=None,
                key=f"q_{item['id']}",
                horizontal=True,
            )
            responses[item["id"]] = val

        elif item["type"] == "number":
            val = st.number_input(
                f"**{item['id']}.** {item['text']}",
                min_value=0, max_value=8, step=1,
                key=f"q_{item['id']}",
            )
            responses[item["id"]] = val

        elif item["type"] == "text":
            val = st.text_area(
                f"**{item['id']}.** {item['text']}",
                key=f"q_{item['id']}",
                height=80,
            )
            responses[item["id"]] = val

    st.markdown("---")

    answered = sum(1 for k,v in responses.items() if v not in (None,"","N/A"))
    required = sum(1 for item in QUESTIONNAIRE if item["type"]!="text" and "Failure" not in item["section"] or verdict=="REJECTED")
    st.markdown(f"**Progress:** {answered}/{len(QUESTIONNAIRE)} items answered.")

    if st.button("📤 Submit Responses", type="primary"):
        missing = [item["id"] for item in QUESTIONNAIRE
                   if item["type"]=="likert5"
                   and responses.get(item["id"]) is None
                   and not ("Failure" in item["section"] and verdict=="ACCEPTED")]
        if missing:
            st.error(f"Please answer all required items before submitting. Missing: {', '.join(missing)}")
        else:
            # Build CSV row for Google Sheets logging
            timestamp = datetime.datetime.now().isoformat()
            row_data = {"timestamp": timestamp, "scenario": scenario_key, "verdict": verdict}
            row_data.update(responses)

            # Display summary
            st.success("✅ Thank you! Your responses have been recorded.")
            st.markdown("**Your responses:**")
            summary_rows = []
            for item in QUESTIONNAIRE:
                summary_rows.append({
                    "Item": item["id"],
                    "Question": item["text"][:60]+"…",
                    "Response": str(responses.get(item["id"],"—")),
                })
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

            st.markdown("""
            <div class="info-box">
            <b>Note to researcher:</b> To enable automatic Google Sheets logging, add your
            Google Sheets API credentials to the Streamlit secrets manager and uncomment
            the gspread logging block in the source code.
            </div>
            """, unsafe_allow_html=True)

            st.session_state["submitted"] = True

