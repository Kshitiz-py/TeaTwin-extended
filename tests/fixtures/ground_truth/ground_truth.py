"""
Ground truth mappings for paper evaluation.

For each entity + variant, defines the correct CMSD field → api_path mapping.
Used to compute LLM accuracy: "how many fields did the LLM get right?"

The ground truth for 'clean' variant is the canonical answer.
Other variants use the same semantic mapping with different api_path values.
"""

# =============================================================================
# RESOURCE — Ground Truth
# =============================================================================
# CMSD Resource has 34 direct fields + 5 inherited. Not all are mappable from
# the mock SAP /resources endpoint (config fields, reference fields may be absent).
#
# Mappable fields from mock SAP /resources:
#   identifier, name, description, resource_type, resource_class_id,
#   capacity, availability (÷100), mttr_seconds (→Duration), mtbf_seconds (→Duration),
#   mcbf, reliability, cycle_time_seconds (→Duration),
#   desired_replenishment_time_seconds (→Duration), transport_capacity,
#   tow_bar_length, worker_count, decision_rule, routing_rule,
#   size (→GrossDimensions), hourly_rate (→Currency)

RESOURCE_GROUND_TRUTH = {
    "identifier":                   "identifier",
    "name":                         "name",
    "description":                  "description",
    "resource_type":                "resource_type",
    "resource_class":               "resource_class_id",          # → ResourceClassReference
    "capacity":                     "capacity",
    "availability":                 "availability",               # ÷100
    "mttr":                         "mttr_seconds",               # → Duration
    "mtbf":                         "mtbf_seconds",               # → Duration
    "mcbf":                         "mcbf",
    "reliability":                  "reliability",
    "cycle_time":                   "cycle_time_seconds",         # → Duration
    "desired_replenishment_time":   "desired_replenishment_time_seconds",  # → Duration
    "transport_capacity":           "transport_capacity",
    "tow_bar_length":               "tow_bar_length",
    "worker_count":                 "worker_count",
    "decision_rule":                "decision_rule",
    "routing_rule":                 "routing_rule",
    "size":                         "size",                       # → GrossDimensions (nested)
    "hourly_rate":                  "hourly_rate",                # → Currency
}

# Fields the API has but CMSD doesn't map to top-level Resource fields
# (these go into nested config objects or are not modeled in CMSD)
RESOURCE_UNMAPPABLE = [
    "buffer_type", "buffer_capacity",
    "conveyor_speed", "conveyor_length", "conveyor_accumulating",
    "energy",
]

# Total API fields in clean Resource response: 26
# Mappable to CMSD Resource: 20 (listed above)
# Unmappable: 6 (listed above)
# Schema coverage: 20/26 = 76.9%


# =============================================================================
# RESOURCE CLASS — Ground Truth
# =============================================================================
# CMSD ResourceClass: identifier, name, description, resource_type,
#                      hourly_rate (→Currency), size (→GrossDimensions)

RESOURCECLASS_GROUND_TRUTH = {
    "identifier":       "identifier",
    "name":             "name",
    "description":      "description",
    "resource_type":    "resource_type",
    "hourly_rate":      "hourly_rate",    # → Currency
    "size":             "size",           # → GrossDimensions (nested)
}

# Total API fields: 7 (identifier, name, description, resource_type, hourly_rate, size + resource_type again)
# Mappable: 6 (100%)


# =============================================================================
# ORDER — Ground Truth
# =============================================================================
# CMSD Order: identifier, name, description, status, due_date, release_date, order_lines[]
# Mock /orders returns: identifier, status, due_date, release_date, priority, line_count
# Note: order_lines is NOT populated from the list endpoint — it needs a detail endpoint
# Note: priority and line_count have no direct CMSD field on Order top-level

ORDER_GROUND_TRUTH = {
    "identifier":       "identifier",
    "status":           "status",
    "due_date":         "due_date",
    "release_date":     "release_date",
}

ORDER_UNMAPPABLE = ["priority", "line_count"]
# Schema coverage: 4/6 = 66.7%


# =============================================================================
# PART TYPE — Ground Truth
# =============================================================================
# CMSD PartType: identifier, name, description, bill_of_materials (ref),
#                 process_plan (ref), size (→GrossDimensions), weight (→Weight)
# Mock /part-types returns: identifier, name, description, size, weight_kg, color, shape_3d

PARTTYPE_GROUND_TRUTH = {
    "identifier":       "identifier",
    "name":             "name",
    "description":      "description",
    "size":             "size",           # → GrossDimensions (nested)
    "weight":           "weight_kg",      # → Weight (unit needed)
}

PARTTYPE_UNMAPPABLE = ["color", "shape_3d"]
# Schema coverage: 5/7 = 71.4%


# =============================================================================
# SCHEMA COVERAGE SUMMARY
# =============================================================================
SCHEMA_COVERAGE = {
    "Resource":      {"api_fields": 26, "mappable": 20, "pct": 76.9},
    "ResourceClass": {"api_fields": 7,  "mappable": 6,  "pct": 100.0},
    "Order":         {"api_fields": 6,  "mappable": 4,  "pct": 66.7},
    "PartType":      {"api_fields": 7,  "mappable": 5,  "pct": 71.4},
}


# =============================================================================
# VARIANT API_PATH MAPPINGS
# =============================================================================
# For legacy/german/deep variants, the api_path changes but the semantics stay.
# These maps convert clean api_path → variant api_path.

# Built from the LEGACY_MAP in generate_variants.py
LEGACY_API_PATH = {
    "identifier":                                   "FLD001",
    "name":                                         "FLD002",
    "description":                                  "FLD003",
    "resource_type":                                "FLD004",
    "resource_class_id":                            "FLD005",
    "capacity":                                     "FLD006",
    "availability":                                 "FLD007",
    "mttr_seconds":                                 "FLD008",
    "mtbf_seconds":                                 "FLD009",
    "mcbf":                                         "FLD010",
    "reliability":                                  "FLD011",
    "cycle_time_seconds":                           "FLD012",
    "desired_replenishment_time_seconds":           "FLD013",
    "transport_capacity":                           "FLD014",
    "tow_bar_length":                               "FLD015",
    "worker_count":                                 "FLD016",
    "decision_rule":                                "FLD017",
    "routing_rule":                                 "FLD018",
    "size":                                         "FLD019",
    "hourly_rate":                                  "FLD020",
    "status":                                       "FLD101",
    "due_date":                                     "FLD102",
    "release_date":                                 "FLD103",
    "priority":                                     "FLD104",
    "line_count":                                   "FLD105",
    "weight_kg":                                    "FLD201",
    "color":                                        "FLD202",
    "shape_3d":                                     "FLD203",
}

GERMAN_API_PATH = {
    "identifier":                                   "kennung",
    "name":                                         "bezeichnung",
    "description":                                  "beschreibung",
    "resource_type":                                "maschinentyp",
    "resource_class_id":                            "maschinenklasse_id",
    "capacity":                                     "kapazitaet",
    "availability":                                 "verfuegbarkeit",
    "mttr_seconds":                                 "mttr_sekunden",
    "mtbf_seconds":                                 "mtbf_sekunden",
    "mcbf":                                         "mcbf",
    "reliability":                                  "zuverlaessigkeit",
    "cycle_time_seconds":                           "zykluszeit_sekunden",
    "desired_replenishment_time_seconds":           "nachfuellzeit_sekunden",
    "transport_capacity":                           "transportkapazitaet",
    "tow_bar_length":                               "zugdeichsel_laenge",
    "worker_count":                                 "mitarbeiter_anzahl",
    "decision_rule":                                "entscheidungsregel",
    "routing_rule":                                 "routing_regel",
    "size":                                         "abmessungen",
    "hourly_rate":                                  "stundensatz",
    "status":                                       "status",
    "due_date":                                     "faelligkeitsdatum",
    "release_date":                                 "freigabedatum",
    "priority":                                     "prioritaet",
    "line_count":                                   "positionsanzahl",
    "weight_kg":                                    "gewicht_kg",
    "color":                                        "farbe",
    "shape_3d":                                     "3d_form",
}

# Deep variant: data is at data.payload.items[], and the items themselves
# still use clean field names. The LLM needs to recognize the envelope.
DEEP_COUNT_PATH = "data.payload.items"


# =============================================================================
# SPECIAL TYPE COERCION NOTES
# =============================================================================
# These fields need non-trivial type coercion. The LLM should identify this
# and propose transformations. A correct mapping includes the right transform.

TYPE_COERCION_REQUIRED = {
    "Resource": {
        "resource_class":   "int → ResourceClassReference(resource_class_identifier=str)",
        "availability":     "float(0-100) → Decimal(0-1) via divide_by 100",
        "mttr":             "int(seconds) → Duration(value=Decimal, unit='second')",
        "mtbf":             "int(seconds) → Duration(value=Decimal, unit='second')",
        "cycle_time":       "int(seconds) → Duration(value=Decimal, unit='second')",
        "desired_replenishment_time": "int(seconds) → Duration",
        "size":             "nested dict {length,width,height} → GrossDimensions",
        "hourly_rate":      "float → Currency(value=Decimal, unit='EUR')",
        "reliability":      "float(0-100) → Decimal(0-1) via divide_by 100",
        "tow_bar_length":   "nullable float → Length(value=Decimal, unit='mm')",
    },
    "ResourceClass": {
        "hourly_rate":      "float → Currency(value=Decimal, unit='EUR')",
        "size":             "nested dict → GrossDimensions",
    },
    "Order": {
        "due_date":         "ISO string → datetime",
        "release_date":     "ISO string → datetime",
        "status":           "string → OrderStatus enum",
    },
    "PartType": {
        "size":             "nested dict → GrossDimensions",
        "weight":           "float(kg) → Weight(value=Decimal, unit='kg')",
    },
}
