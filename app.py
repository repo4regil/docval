"""
app.py
------
Main Streamlit entry point for the Document Validator application.

Run with:
    streamlit run app.py

Session state keys used
~~~~~~~~~~~~~~~~~~~~~~~
``uploaded_file_name``  – original name of the currently loaded file
``tmp_path``            – path to the temporary copy on disk
``doc``                 – opened python-docx Document object
``logger``              – session logger instance
``doc_props``           – DocumentProperties from the last evaluation
``report``              – ValidationReport from the last evaluation
``evaluation_done``     – bool, True after a successful evaluation run
``progress_log``        – list of progress message strings shown in the log area
"""

import os
import time
import streamlit as st

from config import APP_TITLE, APP_VERSION, APP_ICON, ALLOWED_EXTENSIONS
from document_loader import load_document, clear_document
from validation_engine import ValidationEngine
from logger import setup_logger
from ui_components import (
    render_property_table,
    render_validation_report,
    render_progress_line,
)
from metadata_store import set_document_metadata

# ---------------------------------------------------------------------------
# Page configuration – must be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS overrides for a polished look
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Import a clean sans-serif font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: #0d1117;
    }
    section[data-testid="stSidebar"] * {
        color: #c9d1d9 !important;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #58a6ff !important;
    }

    /* Main area accent */
    .stButton > button {
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* Progress box */
    .progress-box {
        background: #f6f8fa;
        border: 1px solid #d0d7de;
        border-radius: 6px;
        padding: 12px 16px;
        max-height: 260px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 0.88rem;
        line-height: 1.7;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        border-radius: 8px;
    }

    /* Section divider */
    hr { border-color: #d0d7de; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helper: dummy logger used before the real one is initialised
# ---------------------------------------------------------------------------
def _dummy_logger():
    """Return a no-op logger for use before a real session logger exists."""
    import logging
    logger = logging.getLogger("dummy")
    logger.addHandler(logging.NullHandler())
    return logger


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
def _init_state() -> None:
    """Initialise all session state keys on first load."""
    defaults = {
        "uploaded_file_name": None,
        "tmp_path":           None,
        "doc":                None,
        "logger":             None,
        "doc_props":          None,
        "report":             None,
        "evaluation_done":    False,
        "progress_log":       [],
        "show_metadata_dialog": False,
        "run_evaluation_after_dialog": False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ---------------------------------------------------------------------------
# Dialog: collect additional document metadata before parsing/evaluation
# ---------------------------------------------------------------------------
@st.dialog("Document details")
def _document_metadata_dialog() -> None:
    """
    Popup dialog displayed when the user clicks **Evaluate** to collect
    additional document details before running validation.

    The captured values are stored globally via ``metadata_store.set_document_metadata``
    so they can be accessed from any module.
    """
    st.markdown(
        "Provide additional details for this uploaded document. "
        "All fields are optional and stored as strings."
    )

    # Use stable keys so values persist across reruns while the dialog is open
    title = st.text_input("Document title", key="metadata_title")
    version = st.text_input("Version", key="metadata_version")
    company = st.text_input("Company name", key="metadata_company")
    author = st.text_input("Author name", key="metadata_author")

    col_save, col_skip = st.columns(2)
    with col_save:
        if st.button("Save details", type="primary", use_container_width=True):
            # Persist globally for access from any module
            set_document_metadata(
                title=title,
                version=version,
                company=company,
                author=author,
            )
            st.session_state.show_metadata_dialog = False
            # After the user has provided details, trigger evaluation if requested
            if st.session_state.get("run_evaluation_after_dialog"):
                # Let the main script perform the actual evaluation on rerun
                st.session_state.run_evaluation_after_dialog = True
            st.success("Document details saved.")
            st.rerun()

    with col_skip:
        if st.button("Skip for now", use_container_width=True):
            st.session_state.show_metadata_dialog = False
            # Even if skipped, still proceed with evaluation if it was requested
            if st.session_state.get("run_evaluation_after_dialog"):
                st.session_state.run_evaluation_after_dialog = True
            st.rerun()


# ---------------------------------------------------------------------------
# Helper: run the validation engine (parsing + checks)
# ---------------------------------------------------------------------------
def _run_evaluation() -> None:
    """Execute the validation engine and render progress/results."""
    logger = st.session_state.logger
    if logger is None or st.session_state.doc is None:
        return

    logger.info("User clicked 'Evaluate'.")

    st.session_state.evaluation_done = False
    st.session_state.progress_log    = []
    st.session_state.doc_props       = None
    st.session_state.report          = None

    st.markdown("---")
    st.markdown("#### 🔄 Validation Progress")
    progress_placeholder = st.empty()
    log_lines: list = []

    engine = ValidationEngine(
        doc=st.session_state.doc,
        filename=st.session_state.uploaded_file_name,
        logger=logger,
        tmp_path=st.session_state.tmp_path,
    )

    for message in engine.run():
        log_lines.append(message)
        # Render all lines collected so far inside a styled box
        lines_html = "".join(f"<div>{line}</div>" for line in log_lines)
        progress_placeholder.markdown(
            f'<div class="progress-box">{lines_html}</div>',
            unsafe_allow_html=True,
        )
        time.sleep(0.05)  # small delay so the UI visibly refreshes per step

    # Store results in session state
    st.session_state.doc_props       = engine.doc_props
    st.session_state.report          = engine.report
    st.session_state.progress_log    = log_lines
    st.session_state.evaluation_done = True
    logger.info("Evaluation complete. Stored results in session state.")


_init_state()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"## {APP_ICON} {APP_TITLE}")
    st.markdown(f"**Version:** `{APP_VERSION}`")
    st.markdown("---")
    st.markdown(
        """
        ### How to use
        1. **Upload** a `.docm` file using the uploader below.  
        2. Click **Evaluate** to run all validation checks.  
        3. Review the **Validation Results** panel.  
        4. Click **Remove Document** to clear and start over.
        """,
    )
    st.markdown("---")
    st.markdown(
        """
        ### Validation Checks
        - 📋 Document properties  
        - 🔝 Header components (logo, title, version)  
        - 🔚 Footer components (label, page number, company)  
        - 📌 Document heading  
        - 📊 Tables under specific headings  
        - 🔗 Cross-table validation  
        """,
    )
    st.markdown("---")

    # Show log file path for the active session
    if st.session_state.logger:
        log_path = getattr(st.session_state.logger, "log_file_path", None)
        if log_path:
            st.markdown("### 📝 Active Log File")
            st.code(os.path.basename(log_path), language=None)


# ---------------------------------------------------------------------------
# Main page – header
# ---------------------------------------------------------------------------
st.markdown(f"# {APP_ICON} {APP_TITLE}")
st.markdown(
    "Upload a macro-enabled Word document (`.docm`) and click **Evaluate** "
    "to run all validation checks."
)
st.markdown("---")


# ---------------------------------------------------------------------------
# Row 1: Upload + action buttons
# ---------------------------------------------------------------------------
col_upload, col_actions = st.columns([3, 1], gap="large")

with col_upload:
    st.markdown("#### 📁 Upload Document")
    allowed_str = ", ".join(f"*{ext}" for ext in ALLOWED_EXTENSIONS)
    uploaded = st.file_uploader(
        label=f"Accepted formats: {allowed_str}",
        type=[ext.lstrip(".") for ext in ALLOWED_EXTENSIONS],
        accept_multiple_files=False,
        key="file_uploader_widget",
        help="Only macro-enabled Word (.docm) files are accepted.",
    )

with col_actions:
    st.markdown("#### ⚙️ Actions")
    evaluate_btn = st.button(
        "🔍 Evaluate",
        use_container_width=True,
        disabled=(uploaded is None),
        help="Run all validation checks on the uploaded document.",
    )
    remove_btn = st.button(
        "🗑️ Remove Document",
        use_container_width=True,
        disabled=(uploaded is None and st.session_state.doc is None),
        help="Clear the uploaded document and reset the session.",
    )


# ---------------------------------------------------------------------------
# Handle: Remove document
# ---------------------------------------------------------------------------
if remove_btn:
    if st.session_state.logger:
        st.session_state.logger.info("User clicked 'Remove Document'.")

    clear_document(st.session_state.tmp_path, st.session_state.logger or _dummy_logger())
    # Reset session state (except the logger so the log file is preserved)
    st.session_state.uploaded_file_name = None
    st.session_state.tmp_path           = None
    st.session_state.doc                = None
    st.session_state.doc_props          = None
    st.session_state.report             = None
    st.session_state.evaluation_done    = False
    st.session_state.progress_log       = []
    st.success("Document removed from memory. Upload a new file to continue.")
    st.rerun()


# ---------------------------------------------------------------------------
# Handle: New file uploaded → load it immediately
# ---------------------------------------------------------------------------
if uploaded is not None:
    # Only reload if a different file was uploaded
    if uploaded.name != st.session_state.uploaded_file_name:
        # Clear old state first
        clear_document(
            st.session_state.tmp_path,
            st.session_state.logger or _dummy_logger(),
        )
        st.session_state.doc           = None
        st.session_state.doc_props     = None
        st.session_state.report        = None
        st.session_state.evaluation_done = False
        st.session_state.progress_log  = []

        # Set up a fresh logger for this upload
        logger = setup_logger(uploaded.name)
        st.session_state.logger = logger
        logger.info("File uploaded by user: %s (%d bytes)", uploaded.name, uploaded.size)

        # Load document straight away (no popup yet)
        with st.spinner("Loading document…"):
            doc, tmp_path, error = load_document(
                file_bytes=uploaded.getvalue(),
                original_filename=uploaded.name,
                logger=logger,
            )

        if error:
            st.error(f"❌ Could not load document:\n\n{error}")
        else:
            st.session_state.doc               = doc
            st.session_state.tmp_path          = tmp_path
            st.session_state.uploaded_file_name = uploaded.name
            st.success(
                f"✅ '{uploaded.name}' loaded successfully. "
                "Click **Evaluate** to validate."
            )


# ---------------------------------------------------------------------------
# Handle: Evaluate – open metadata dialog first, then run validation
# ---------------------------------------------------------------------------
if evaluate_btn and st.session_state.doc is not None:
    # Trigger the metadata dialog; actual evaluation will run after it closes
    st.session_state.show_metadata_dialog = True
    st.session_state.run_evaluation_after_dialog = True


# ---------------------------------------------------------------------------
# Show metadata dialog when requested
# ---------------------------------------------------------------------------
if st.session_state.get("show_metadata_dialog"):
    _document_metadata_dialog()


# ---------------------------------------------------------------------------
# After the dialog, run evaluation if it was requested
# ---------------------------------------------------------------------------
if st.session_state.get("run_evaluation_after_dialog") and st.session_state.doc is not None:
    # Reset the trigger before running to avoid accidental double-runs
    st.session_state.run_evaluation_after_dialog = False
    _run_evaluation()


# ---------------------------------------------------------------------------
# Display: Document Properties + Validation Results
# (shown whenever evaluation_done is True, persists across reruns)
# ---------------------------------------------------------------------------
if st.session_state.evaluation_done:
    st.markdown("---")

    # Show the progress log (collapsed after first render)
    with st.expander("🔄 Validation Progress Log", expanded=False):
        lines_html = "".join(
            f"<div>{line}</div>" for line in st.session_state.progress_log
        )
        st.markdown(
            f'<div class="progress-box">{lines_html}</div>',
            unsafe_allow_html=True,
        )

    # Document Properties
    st.markdown("#### 📋 Document Properties")
    render_property_table(st.session_state.doc_props)

    # Validation Results
    st.markdown("#### 🧪 Validation Results")
    if st.session_state.report:
        render_validation_report(st.session_state.report)
    else:
        st.warning("No validation results available.")



