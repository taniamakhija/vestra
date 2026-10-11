# Keep navigation visible above the dashboard and live demo.

from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="VESTRA",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Style a fixed navigation bar.
STYLE = """
<style>
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stHeader"],
[data-testid="stImage"] {
    display: none !important;
}

.st-key-top_navigation {
    position: fixed !important;
    top: 0;
    left: 0;
    right: 0;
    width: 100%;
    z-index: 99999;
    background: #E5EBDD !important;
    border-bottom: 1px solid #8FA98B;
    padding: 12px 24px;
}

.st-key-top_navigation p,
.st-key-top_navigation a,
.st-key-top_navigation span {
    font-family: Georgia, "Times New Roman", serif !important;
    font-size: 21px !important;
    color: #234638 !important;
}

[data-testid="stMainBlockContainer"] {
    max-width: 1500px !important;
    padding-top: 6rem !important;
}

.stApp p,
.stApp label {
    font-size: 20px;
    color: #234638;
}
/* Keep ALL form buttons light with dark text. */
[data-testid="stFormSubmitButton"] button,
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stFormSubmitButton"] button:focus,
[data-testid="stFormSubmitButton"] button:active,
[data-testid="stFormSubmitButton"] button:disabled {
    background: #E5EBDD !important;
    color: #234638 !important;
    border: 1px solid #8FA98B !important;
    box-shadow: none !important;
}

[data-testid="stFormSubmitButton"] button * {
    color: #234638 !important;
    font-family: Georgia, "Times New Roman", serif !important;
}

/* Keep the dropdown and its arrow light. */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div {
    background: #FBF9F3 !important;
    color: #234638 !important;
    border-color: #8FA98B !important;
}

[data-baseweb="select"] svg {
    color: #234638 !important;
    fill: #234638 !important;
}

/* Dropdown menus sit outside the main page container. */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="menu"],
[role="listbox"],
[role="option"] {
    background: #FBF9F3 !important;
    color: #234638 !important;
    font-family: Georgia, "Times New Roman", serif !important;
}

[role="option"] *,
[data-baseweb="menu"] li * {
    color: #234638 !important;
    font-family: Georgia, "Times New Roman", serif !important;
}

[role="option"]:hover,
[role="option"][aria-selected="true"],
[data-baseweb="menu"] li:hover {
    background: #E5EBDD !important;
    color: #234638 !important;
}

/* Keep text boxes readable and remove red focus borders. */
textarea,
input {
    background: #FBF9F3 !important;
    color: #234638 !important;
    -webkit-text-fill-color: #234638 !important;
}

[data-baseweb="textarea"],
[data-baseweb="input"] {
    background: #FBF9F3 !important;
    border-color: #8FA98B !important;
}
</style>
"""

st.markdown(STYLE, unsafe_allow_html=True)

# Register both pages without sidebar navigation.
dashboard_page = st.Page(
    str(ROOT / "dashboard.py"),
    title="Dashboard",
    default=True,
)

demo_page = st.Page(
    str(ROOT / "live_demo.py"),
    title="Live demo",
)

navigation = st.navigation(
    [dashboard_page, demo_page],
    position="hidden",
)

# Keep both links visible while scrolling.
with st.container(key="top_navigation"):
    left, right = st.columns(2)

    with left:
        st.page_link(dashboard_page, label="Dashboard")

    with right:
        st.page_link(demo_page, label="Live demo — enter your situation")

# Display the selected page.
navigation.run()

# Keep these styles after the page's own styling.
st.markdown(STYLE, unsafe_allow_html=True)