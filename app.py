from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="TinySQL Lab | Text-to-SQL Case Study", page_icon="🧪", layout="wide", initial_sidebar_state="collapsed")

EXAMPLES = [
    {"id": 461, "database": "card_games", "difficulty": "Simple", "question": "Please list the names of the top 3 cards with the highest converted mana cost and a 2003 card frame style.", "sql": "SELECT name\nFROM cards\nWHERE frameVersion = '2003'\nORDER BY convertedManaCost DESC\nLIMIT 3;", "columns": ["name"], "rows": [["Draco"], ["Gleemax"], ["Gleemax"]]},
    {"id": 222, "database": "toxicology", "difficulty": "Moderate", "question": "What is the difference between the number of molecules that are carcinogenic and those that are not?", "sql": "SELECT SUM(CASE WHEN label = '+' THEN 1 ELSE 0 END)\n     - SUM(CASE WHEN label = '-' THEN 1 ELSE 0 END) AS difference\nFROM molecule;", "columns": ["difference"], "rows": [[-39]]},
    {"id": 787, "database": "superhero", "difficulty": "Simple", "question": "What are the race and alignment of Cameron Hicks?", "sql": "SELECT race.race, alignment.alignment\nFROM superhero\nJOIN race ON superhero.race_id = race.id\nJOIN alignment ON superhero.alignment_id = alignment.id\nWHERE superhero.superhero_name = 'Cameron Hicks';", "columns": ["race", "alignment"], "rows": [["Alpha", "Good"]]},
    {"id": 702, "database": "codebase_community", "difficulty": "Simple", "question": "How many posts have a score less than 20?", "sql": "SELECT COUNT(Id) AS post_count\nFROM posts\nWHERE Score < 20;", "columns": ["post_count"], "rows": [[90977]]},
    {"id": 1420, "database": "student_club", "difficulty": "Simple", "question": "State the name of the major that the Vice President has joined.", "sql": "SELECT major.major_name\nFROM member\nJOIN major ON member.link_to_major = major.major_id\nWHERE member.position = 'Vice President';", "columns": ["major_name"], "rows": [["Communication Studies"]]},
    {"id": 1089, "database": "european_football_2", "difficulty": "Simple", "question": "How many matches in the 2008/2009 season were held in Belgium?", "sql": "SELECT COUNT(match.id) AS match_count\nFROM Match AS match\nJOIN League ON match.league_id = League.id\nJOIN Country ON League.country_id = Country.id\nWHERE match.season = '2008/2009'\n  AND Country.name = 'Belgium';", "columns": ["match_count"], "rows": [[306]]},
]

st.markdown("""
<style>
:root{--ink:#08152f;--muted:#536179;--line:#dce2eb;--blue:#155eef;--green:#087f5b}
.stApp{background:#fff;color:var(--ink)}.block-container{max-width:1240px;padding-top:1.25rem;padding-bottom:4rem}header[data-testid="stHeader"]{display:none}#MainMenu,footer{visibility:hidden}
h1,h2,h3{color:var(--ink);letter-spacing:-.035em}h1{font-size:clamp(3.2rem,6vw,5.75rem)!important;line-height:.94!important;max-width:700px;margin-top:4.5rem!important}h2{font-size:clamp(2.15rem,4vw,3.45rem)!important;margin-top:5rem!important}p,li,label{color:var(--muted);font-size:1.05rem}
.brand{font-size:1.45rem;font-weight:850;letter-spacing:-.04em;color:var(--ink);padding:.5rem 0 1.4rem;border-bottom:1px solid var(--line)}.lede{font-size:1.3rem;line-height:1.65;max-width:660px;margin:1.7rem 0 2rem}.demo-note{color:var(--green);font-weight:700;margin:.75rem 0 0}
.metric-strip{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:4.5rem 0 1rem}.metric{padding:2rem 2.2rem 2.1rem 0}.metric+.metric{border-left:1px solid var(--line);padding-left:2.2rem}.metric strong{display:block;color:var(--blue);font-size:3.75rem;letter-spacing:-.06em;line-height:1}.metric span{color:var(--ink);font-weight:750}.metric small{display:block;color:var(--muted);margin-top:.65rem;line-height:1.4}
.progression{display:grid;grid-template-columns:repeat(4,1fr);border-top:2px solid var(--blue);margin:2rem 0}.step{padding:1.5rem 1.5rem 1rem 0}.step strong{display:block;color:var(--ink);font-size:2.4rem}.step b{color:var(--blue);font-family:monospace}.step small{display:block;color:var(--muted);margin-top:.45rem}.limitation{border-left:4px solid var(--green);background:#f2fbf7;padding:1rem 1.25rem;color:#145c47;margin-top:1rem}
.system-list{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-top:2rem}.system-list div{padding:1.2rem .8rem 1.2rem 0;color:var(--ink);font-weight:700}.cta{background:var(--ink);color:#fff;padding:2.2rem 2.5rem;margin-top:5rem;display:flex;align-items:center;justify-content:space-between;gap:2rem}.cta strong{font-size:1.8rem;letter-spacing:-.025em}.cta a{color:#fff!important;border:1px solid #7f8ba3;padding:.8rem 1rem;text-decoration:none;font-weight:700}
div[data-testid="stForm"]{border:1px solid var(--line);border-radius:8px;padding:1.4rem;box-shadow:0 18px 50px rgba(8,21,47,.07)}button[data-testid="stBaseButton-secondaryFormSubmit"]{background:var(--blue);color:#fff;border:0;border-radius:5px;font-weight:750;min-height:3rem}button[data-testid="stBaseButton-secondaryFormSubmit"] p{color:#fff;font-weight:750}button[data-testid="stBaseButton-secondaryFormSubmit"]:hover{background:#0b4cd4;color:#fff}a[data-testid="stBaseLinkButton-secondary"]{background:var(--ink);border-color:var(--ink);color:#fff;border-radius:5px}a[data-testid="stBaseLinkButton-secondary"] p{color:#fff;font-weight:750}div[data-baseweb="select"]>div,textarea{border-radius:5px!important}div[data-testid="stCode"]{border:1px solid var(--line);border-radius:5px}
@media(max-width:760px){.block-container{padding-left:1rem;padding-right:1rem}h1{margin-top:2rem!important}.metric-strip,.progression,.system-list{grid-template-columns:1fr}.metric+.metric{border-left:0;border-top:1px solid var(--line);padding-left:0}.cta{align-items:flex-start;flex-direction:column}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand">TinySQL Lab</div>', unsafe_allow_html=True)
intro, demo = st.columns([0.88, 1.12], gap="large", vertical_alignment="center")
with intro:
    st.title("Turn a question into SQL.")
    st.markdown('<p class="lede">A portfolio demo of a Qwen2.5-Coder model fine-tuned on BIRD, evaluated by running SQL against real SQLite databases.</p>', unsafe_allow_html=True)
    st.link_button("View source on GitHub", "https://github.com/Miraj-world/Tinysql-coder")
with demo:
    with st.form("demo"):
        selected_question = st.selectbox("Choose a frozen evaluation question", [item["question"] for item in EXAMPLES])
        run_demo = st.form_submit_button("Run evaluation example", use_container_width=True)
    selected = next(item for item in EXAMPLES if item["question"] == selected_question)
    if run_demo or st.session_state.get("demo_has_run"):
        st.session_state.demo_has_run = True
        st.caption(f"Database: {selected['database']} · {selected['difficulty']} · Question ID {selected['id']}")
        st.code(selected["sql"], language="sql")
        st.dataframe([dict(zip(selected["columns"], row)) for row in selected["rows"]], use_container_width=True, hide_index=True)
        st.markdown('<p class="demo-note">✓ Real model output from the frozen unseen evaluation set.</p>', unsafe_allow_html=True)
    else:
        st.info("Select a question and run the example to inspect the model output.")

st.markdown("""<div class="metric-strip" id="results">
<div class="metric"><strong>43/100</strong><span>unseen questions correct</span><small>Frozen before inference; excluded from training and development.</small></div>
<div class="metric"><strong>83/100</strong><span>SQL queries executable</span><small>The final guarded single-model pipeline on unseen questions.</small></div>
<div class="metric"><strong>58</strong><span>automated tests passing</span><small>Evaluation, repair, sampling, and training-path coverage.</small></div></div>""", unsafe_allow_html=True)

st.header("What changed the result")
st.markdown("""<div class="progression">
<div class="step"><strong>22/100</strong><b>Run 009 raw</b><small>Early full validation benchmark</small></div>
<div class="step"><strong>29/100</strong><b>Guarded repair</b><small>+7 correct without retraining</small></div>
<div class="step"><strong>35/100</strong><b>Run 013 + values</b><small>3B QLoRA practical pipeline</small></div>
<div class="step"><strong>46/100</strong><b>Semantic judge</b><small>Best development-set ensemble</small></div></div>""", unsafe_allow_html=True)

st.header("The honest final test")
score, detail = st.columns([0.7, 1.3], gap="large")
with score:
    st.markdown("## 43/100")
    st.write("100 frozen BIRD questions excluded from training and development.")
with detail:
    st.dataframe([{"Difficulty":"Simple","Correct":"39/69","Accuracy":"56.5%"},{"Difficulty":"Moderate","Correct":"2/20","Accuracy":"10.0%"},{"Difficulty":"Challenging","Correct":"2/11","Accuracy":"18.2%"}], use_container_width=True, hide_index=True)
    st.markdown('<div class="limitation"><strong>Important limitation:</strong> unseen questions on familiar schemas—not an unseen-schema benchmark.</div>', unsafe_allow_html=True)

st.header("Built as an engineering system")
st.markdown("""<div class="system-list"><div>4-bit QLoRA</div><div>Leakage-safe value retrieval</div><div>Guarded SQL repair</div><div>SQLite execution evaluation</div><div>Consensus + semantic judging</div><div>58 passing tests</div></div>
<div class="cta"><strong>Explore the code and evaluation trail.</strong><span><a href="https://github.com/Miraj-world/Tinysql-coder" target="_blank">View on GitHub ↗</a></span></div>""", unsafe_allow_html=True)
