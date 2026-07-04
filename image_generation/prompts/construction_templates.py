"""Prompt template identifiers for construction organization scenes."""

CONSTRUCTION_TEMPLATE_KEYS = [
    "foundation_pit_construction",
    "rebar_binding",
    "formwork_installation",
    "concrete_pouring",
    "hoisting_operation",
    "temporary_facility_layout",
    "safe_civilized_construction",
    "material_yard_management",
    "road_pipeline_construction",
    "campus_renovation_scene",
    "municipal_drainage_construction",
    "birdseye_site_render",
    "technical_bid_cover",
]

DEFAULT_TEMPLATE_BY_TASK_TYPE = {
    "technical_bid_illustration": "technical_bid_cover",
    "realistic_construction_scene": "foundation_pit_construction",
    "site_photo_edit": "campus_renovation_scene",
    "safety_civilization_scene": "safe_civilized_construction",
    "temporary_facility_layout": "temporary_facility_layout",
    "machinery_operation_scene": "hoisting_operation",
    "material_yard_scene": "material_yard_management",
    "construction_process_diagram": "road_pipeline_construction",
    "birdseye_render": "birdseye_site_render",
    "cover_image": "technical_bid_cover",
    "chinese_signage_scene": "safe_civilized_construction",
}
