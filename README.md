# 📄 Document Validator

A **Streamlit** application for validating macro-enabled Word documents (`.docm`).
It checks document properties, header/footer content, heading structure, and validates tables — all with a live progress display and per-upload audit logs.

---

## 🗂️ Project Structure

```
DocumentValidator/
├── app.py                   # Main Streamlit entry point
├── config.py                # ⚙️  All tunable settings — start here
├── models.py                # Shared dataclasses (ValidationResult, Report, etc.)
├── logger.py                # Per-upload timestamped log setup
├── document_loader.py       # Load / clear uploaded .docm files
├── document_properties.py   # Extract core document metadata
├── header_validator.py      # Validate header components
├── footer_validator.py      # Validate footer components
├── heading_validator.py     # Validate document headings
├── table_extractor.py       # Extract tables under named headings
├── table_validator.py       # Validate table content + cross-reference checks
├── validation_engine.py     # Orchestrator — runs all validators in order
├── ui_components.py         # Reusable Streamlit UI widgets
├── requirements.txt         # Python dependencies
├── logs/                    # Auto-created — one .log file per upload
├── tmp/                     # Auto-created — temp files during processing
└── tests/
    └── test_validators.py   # Smoke tests
```

---

## ⚙️ Configuration (`config.py`)

Before running, open `config.py` and update:

| Setting | Description |
|---|---|
| `TABLE_HEADING_NAMES` | Heading names where tables are extracted (case-insensitive) |
| `COMPANY_NAME` | Company name expected in the footer |
| `EXPECTED_DOCUMENT_HEADING` | Expected Heading 1 text (leave `""` to skip) |
| `TABLE_CROSS_VALIDATION_RULES` | Pairs of tables + columns to cross-validate |
| `HEADER_CHECKS` / `FOOTER_CHECKS` | Toggle individual checks on/off |
| `VALIDATION_TOGGLES` | Toggle entire validator groups on/off |

---

## 🚀 Setup & Run

### 1. Create a virtual environment (recommended)
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run app.py
```

The app opens at **http://localhost:8501** in your browser.

---

## 📝 Audit Logs

Every time a document is uploaded, a new log file is created in `logs/`:

```
logs/20260313_191200_MyDocument.log
```

The log captures every check, pass/fail result, and any errors for full traceability.

---

## ➕ Adding New Validation Checks

### Add a new header check
1. Open `header_validator.py`
2. Write a `_check_<your_check>(header, logger)` function returning a `ValidationResult`
3. Add it to the `check_map` dict inside `validate_header()`
4. Add a toggle for it in `config.py → HEADER_CHECKS`

The same pattern applies for footer (`footer_validator.py`) and heading checks.

### Add a new table cross-validation rule
Open `config.py` and add a tuple to `TABLE_CROSS_VALIDATION_RULES`:
```python
TABLE_CROSS_VALIDATION_RULES = [
    ("Approvals", "Name", "Review Matrix", "Reviewer Name"),
]
```

---

## 🧪 Running Tests

```bash
pip install pytest
pytest tests/ -v
```
