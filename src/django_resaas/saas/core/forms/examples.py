"""Example form definitions (documentation and tests - nothing registers
them): a clinic's triage (workflow), a hotel check-in (wizard, repeater,
calculated total) and a school enrolment (hybrid over a model, conditions).
docs/architecture/form-engine.md shows them; tests/test_examples.py proves
they are valid and that the server enforces their rules."""

CLINIC_TRIAGE = {
    "schema_version": "1.0",
    "key": "saude.triage",
    "title": "Triage",
    "mode": "workflow",
    "layout": "sections",
    "submit": {"endpoint": "saude/agendas/{id}/triage/", "method": "post"},
    "sections": [
        {"key": "vitals", "label": "Vital signs", "fields": [
            {"name": "temperature", "type": "decimal", "label": "Temperature (°C)", "cols": 4, "required": True,
             "validators": [{"rule": "min", "value": 30}, {"rule": "max", "value": 45}]},
            {"name": "systolic", "type": "integer", "label": "Systolic", "cols": 4},
            {"name": "diastolic", "type": "integer", "label": "Diastolic", "cols": 4,
             "required_if": {"field": "systolic", "op": "not_empty"}},
            {"name": "pain", "type": "integer", "label": "Pain (0-10)", "cols": 4,
             "validators": [{"rule": "min", "value": 0}, {"rule": "max", "value": 10}]},
        ]},
        {"key": "risk", "label": "Risk", "fields": [
            {"name": "priority", "type": "select", "label": "Priority", "required": True, "options": [
                {"value": "normal", "label": "Normal"}, {"value": "urgent", "label": "Urgent"},
                {"value": "emergency", "label": "Emergency"}]},
            {"name": "reason", "type": "textarea", "label": "Why urgent",
             "required_if": {"field": "priority", "op": "in", "value": ["urgent", "emergency"]},
             "visible_if": {"field": "priority", "op": "ne", "value": "normal"}},
        ]},
    ],
}

HOTEL_CHECK_IN = {
    "schema_version": "1.0",
    "key": "hotel.check_in",
    "title": "Check-in",
    "mode": "workflow",
    "layout": "wizard",
    "autosave": True,
    "submit": {"endpoint": "hotel/stays/{id}/check_in/", "method": "post"},
    "sections": [
        {"key": "guest", "label": "Guest", "fields": [
            {"name": "full_name", "type": "text", "label": "Full name", "required": True, "locked": True},
            {"name": "foreigner", "type": "boolean", "label": "Foreign guest"},
            {"name": "passport", "type": "text", "label": "Passport number",
             "visible_if": {"field": "foreigner", "op": "eq", "value": True},
             "required_if": {"field": "foreigner", "op": "eq", "value": True},
             "validators": [{"rule": "pattern", "value": "[A-Z0-9]{6,12}"}]},
        ]},
        {"key": "stay", "label": "Stay", "fields": [
            {"name": "nights", "type": "integer", "label": "Nights", "required": True, "cols": 4,
             "validators": [{"rule": "min", "value": 1}]},
            {"name": "rate", "type": "decimal", "label": "Rate per night", "cols": 4},
            {"name": "total", "type": "decimal", "label": "Total", "cols": 4,
             "calculate": {"op": "product", "of": ["nights", "rate"]}},
            {"name": "companions", "type": "repeater", "label": "Companions", "max_items": 6,
             "fields": [{"name": "name", "type": "text", "label": "Name", "required": True},
                        {"name": "age", "type": "integer", "label": "Age"}]},
        ]},
    ],
}

SCHOOL_ENROLMENT = {
    "schema_version": "1.0",
    "key": "school.enrolment",
    "title": "Enrolment",
    "mode": "hybrid",
    "source": {"model": "django_resaas.Person"},
    "layout": "tabs",
    "sections": [
        {"key": "student", "label": "Student", "fields": [
            {"name": "name", "from_schema": True, "required": True},
            {"name": "surname", "from_schema": True, "required": True},
            {"name": "date_of_birth", "from_schema": True, "type": "date", "required": True},
        ]},
        {"key": "guardian", "label": "Guardian", "fields": [
            {"name": "guardian", "type": "object", "label": "Guardian", "fields": [
                {"name": "name", "type": "text", "label": "Name", "required": True},
                {"name": "phone", "type": "phone", "label": "Phone", "required": True},
                {"name": "email", "type": "email", "label": "E-mail"},
            ]},
        ]},
        {"key": "course", "label": "Course", "fields": [
            {"name": "course", "type": "relation", "label": "Course", "required": True,
             "relation": {"endpoint": "catalog/products/"}},
            {"name": "scholarship", "type": "boolean", "label": "Scholarship"},
            {"name": "scholarship_document", "type": "file", "label": "Scholarship document",
             "visible_if": {"field": "scholarship", "op": "eq", "value": True},
             "required_if": {"field": "scholarship", "op": "eq", "value": True}},
        ]},
    ],
}

EXAMPLES = (CLINIC_TRIAGE, HOTEL_CHECK_IN, SCHOOL_ENROLMENT)
