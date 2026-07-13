from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from ....io import ContractError


MATURITY = {"official_only", "recorded_fixture", "live_verified", "blender_verified"}


@dataclass(frozen=True)
class OperationSpec:
    key: str
    capability: str
    submit_action: str
    status_action: Optional[str]
    query_kind: str
    artifact_role: str
    expected_types: Tuple[str, ...]
    default_concurrency: int
    maturity: str = "official_only"
    warning: Optional[str] = None

    @property
    def is_async(self) -> bool:
        return self.query_kind in {"query", "describe"}

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["is_async"] = self.is_async
        return value


_SPECS = [
    OperationSpec(
        "geometry.pro", "professional_3d_generation", "SubmitHunyuanTo3DProJob",
        "QueryHunyuanTo3DProJob", "query", "raw_geometry_candidate",
        ("OBJ", "GLB", "FBX", "STL", "USDZ"), 3,
    ),
    OperationSpec(
        "geometry.rapid", "rapid_3d_generation", "SubmitHunyuanTo3DRapidJob",
        "QueryHunyuanTo3DRapidJob", "query", "rapid_geometry_candidate",
        ("OBJ", "GLB", "FBX", "STL", "USDZ", "MP4"), 1,
    ),
    OperationSpec(
        "profile.generate", "profile_to_3d", "SubmitProfileTo3DJob",
        "DescribeProfileTo3DJob", "describe", "profile_character_candidate",
        ("OBJ", "GLB", "FBX"), 1,
    ),
    OperationSpec(
        "rig.auto", "auto_rigging", "SubmitAutoRiggingJob",
        "DescribeAutoRiggingJob", "describe", "draft_rigged_character",
        ("FBX",), 1,
        warning="AutoRig success proves skeleton presence, not deformation quality.",
    ),
    OperationSpec(
        "motion.text", "text_to_motion", "SubmitHunyuanTo3DMotionJob",
        "DescribeHunyuanTo3DMotionJob", "describe", "motion_source_skeleton",
        ("FBX",), 1,
        warning="Project evidence shows this output is a motion source; Blender retarget remains required.",
    ),
    OperationSpec(
        "texture.generate", "texture_generation", "SubmitTextureTo3DJob",
        "DescribeTextureTo3DJob", "describe", "textured_asset_candidate",
        ("OBJ", "GLB", "FBX"), 1,
    ),
    OperationSpec(
        "topology.reduce", "topology_reduction", "SubmitReduceFaceJob",
        "DescribeReduceFaceJob", "describe", "reduced_topology_candidate",
        ("OBJ", "GLB", "IMAGE"), 1,
        warning="Automatic reduction must pass Blender wireframe and deformation review.",
    ),
    OperationSpec(
        "parts.generate", "part_generation", "SubmitHunyuan3DPartJob",
        "QueryHunyuan3DPartJob", "query", "part_set_candidate",
        ("OBJ", "GLB", "FBX"), 1,
    ),
    OperationSpec(
        "uv.unwrap", "uv_unwrap", "SubmitHunyuanTo3DUVJob",
        "DescribeHunyuanTo3DUVJob", "describe", "uv_asset_candidate",
        ("OBJ", "GLB", "FBX"), 1,
    ),
    OperationSpec(
        "format.convert", "format_conversion", "Convert3DFormat",
        None, "sync", "converted_asset_candidate",
        ("FBX", "STL", "USDZ", "MP4", "GIF"), 20,
    ),
]

OPERATIONS: Dict[str, OperationSpec] = {spec.key: spec for spec in _SPECS}
REQUIRED_OPERATION_KEYS = frozenset({
    "geometry.pro", "geometry.rapid", "profile.generate", "rig.auto", "motion.text",
    "texture.generate", "topology.reduce", "parts.generate", "uv.unwrap", "format.convert",
})
REQUIRED_ACTIONS = frozenset({
    "SubmitHunyuanTo3DProJob", "QueryHunyuanTo3DProJob",
    "SubmitHunyuanTo3DRapidJob", "QueryHunyuanTo3DRapidJob",
    "SubmitProfileTo3DJob", "DescribeProfileTo3DJob",
    "SubmitAutoRiggingJob", "DescribeAutoRiggingJob",
    "SubmitHunyuanTo3DMotionJob", "DescribeHunyuanTo3DMotionJob",
    "SubmitTextureTo3DJob", "DescribeTextureTo3DJob",
    "SubmitReduceFaceJob", "DescribeReduceFaceJob",
    "SubmitHunyuan3DPartJob", "QueryHunyuan3DPartJob",
    "SubmitHunyuanTo3DUVJob", "DescribeHunyuanTo3DUVJob",
    "Convert3DFormat",
})


def all_actions() -> List[str]:
    actions: List[str] = []
    for spec in OPERATIONS.values():
        actions.append(spec.submit_action)
        if spec.status_action:
            actions.append(spec.status_action)
    return actions


def validate_registry() -> None:
    missing_operations = REQUIRED_OPERATION_KEYS.difference(OPERATIONS)
    if missing_operations:
        raise ContractError("Hunyuan registry is missing required operations: %s" % sorted(missing_operations))
    actions = all_actions()
    if len(actions) != len(set(actions)):
        raise ContractError("Hunyuan registry action names must be unique")
    missing_actions = REQUIRED_ACTIONS.difference(actions)
    if missing_actions:
        raise ContractError("Hunyuan registry is missing required actions: %s" % sorted(missing_actions))
    for spec in OPERATIONS.values():
        if spec.maturity not in MATURITY:
            raise ContractError("invalid maturity for %s" % spec.key)
        if spec.query_kind == "query" and not (spec.status_action or "").startswith("Query"):
            raise ContractError("query operation has wrong status action: %s" % spec.key)
        if spec.query_kind == "describe" and not (spec.status_action or "").startswith("Describe"):
            raise ContractError("describe operation has wrong status action: %s" % spec.key)
        if spec.query_kind == "sync" and spec.status_action is not None:
            raise ContractError("sync operation must not have a status action: %s" % spec.key)


def _file_object(payload: Dict[str, Any], operation: str, field: str = "File3D") -> Dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise ContractError("%s requires %s" % (operation, field))
    if not isinstance(value.get("Url"), str) or not value["Url"].strip():
        raise ContractError("%s %s.Url is required" % (operation, field))
    if not isinstance(value.get("Type"), str) or not value["Type"].strip():
        raise ContractError("%s %s.Type is required" % (operation, field))
    return value


def _validate_generation_source(payload: Dict[str, Any], operation: str) -> None:
    present = [name for name in ("Prompt", "ImageBase64", "ImageUrl") if payload.get(name)]
    generate_type = payload.get("GenerateType")
    if not present:
        raise ContractError("%s requires Prompt, ImageBase64 or ImageUrl" % operation)
    if generate_type == "Sketch":
        image_modes = [name for name in ("ImageBase64", "ImageUrl") if payload.get(name)]
        if len(image_modes) > 1:
            raise ContractError("Sketch accepts only one image input mode")
    elif len(present) != 1:
        raise ContractError("%s prompt and image modes are mutually exclusive" % operation)


def validate_request(operation: str, payload: Dict[str, Any]) -> List[str]:
    if operation not in OPERATIONS:
        raise ContractError("unknown Hunyuan operation: %s" % operation)
    if not isinstance(payload, dict) or not payload:
        raise ContractError("Hunyuan request must be a non-empty object")
    warnings: List[str] = []
    spec = OPERATIONS[operation]
    if spec.warning:
        warnings.append(spec.warning)

    if operation == "geometry.pro":
        _validate_generation_source(payload, operation)
        model = str(payload.get("Model", "3.0"))
        generate_type = payload.get("GenerateType", "Normal")
        if model not in {"3.0", "3.1"}:
            raise ContractError("geometry.pro Model must be 3.0 or 3.1")
        if generate_type not in {"Normal", "LowPoly", "Geometry", "Sketch"}:
            raise ContractError("geometry.pro GenerateType is invalid")
        if len(str(payload.get("Prompt", ""))) > 1024:
            raise ContractError("geometry.pro Prompt must be <= 1024 characters")
        if model == "3.1" and generate_type == "LowPoly":
            raise ContractError("geometry.pro Model 3.1 does not support LowPoly")
        if payload.get("PolygonType") is not None:
            if generate_type != "LowPoly" or payload["PolygonType"] not in {"triangle", "quadrilateral"}:
                raise ContractError("geometry.pro PolygonType is only valid for LowPoly")
        if payload.get("ResultFormat") is not None and str(payload["ResultFormat"]).upper() not in {"STL", "USDZ", "FBX"}:
            raise ContractError("geometry.pro ResultFormat must be STL, USDZ or FBX when explicitly set")
        faces = payload.get("FaceCount")
        if faces is not None and (not isinstance(faces, int) or not 3000 <= faces <= 1500000):
            raise ContractError("geometry.pro FaceCount must be 3000..1500000")
        views = payload.get("MultiViewImages", [])
        if not isinstance(views, list):
            raise ContractError("geometry.pro MultiViewImages must be a list")
        seen_views = set()
        for view in views:
            if not isinstance(view, dict) or view.get("ViewType") not in {
                "left", "right", "back", "top", "bottom", "left_front", "right_front"
            }:
                raise ContractError("geometry.pro contains an invalid MultiViewImages ViewType")
            if view["ViewType"] in seen_views:
                raise ContractError("geometry.pro MultiViewImages ViewType values must be unique")
            seen_views.add(view["ViewType"])
            sources = [key for key in ("ViewImageUrl", "ViewImageBase64") if view.get(key)]
            if len(sources) != 1:
                raise ContractError("each geometry.pro multi-view item requires one image source")
            if model == "3.0" and view.get("ViewType") in {"top", "bottom", "left_front", "right_front"}:
                raise ContractError("geometry.pro Model 3.0 does not support this multi-view angle")
    elif operation == "geometry.rapid":
        _validate_generation_source(payload, operation)
        forbidden = sorted(set(payload).intersection({"MultiViewImages", "FaceCount", "GenerateType"}))
        if forbidden:
            raise ContractError("geometry.rapid does not support: %s" % ", ".join(forbidden))
        if len(str(payload.get("Prompt", ""))) > 200:
            raise ContractError("geometry.rapid Prompt must be <= 200 characters")
        result_format = payload.get("ResultFormat")
        if result_format is not None and str(result_format).upper() not in {"OBJ", "GLB", "STL", "USDZ", "FBX", "MP4"}:
            raise ContractError("geometry.rapid ResultFormat is invalid")
        if payload.get("EnableGeometry") is True and str(result_format or "").upper() == "OBJ":
            raise ContractError("geometry.rapid EnableGeometry cannot be combined with OBJ ResultFormat")
    elif operation == "rig.auto":
        file3d = _file_object(payload, operation)
        if str(file3d["Type"]).upper() not in {"GLB", "FBX"}:
            raise ContractError("rig.auto supports GLB or FBX")
        motion_type = payload.get("MotionType")
        if motion_type is not None and (not isinstance(motion_type, int) or not 1 <= motion_type <= 48):
            raise ContractError("rig.auto MotionType must be 1..48")
        warnings.extend([
            "AutoRig humanoid input should be a clean A/T pose.",
            "Loose clothing, weapons, mounts, wings and complex accessories may invalidate this route.",
        ])
    elif operation == "motion.text":
        prompt = payload.get("Prompt")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 128:
            raise ContractError("motion.text Prompt must be 1..128 characters")
        duration = payload.get("Duration")
        if duration is not None and (not isinstance(duration, int) or not 1 <= duration <= 12):
            raise ContractError("motion.text Duration must be 1..12 seconds")
        if payload.get("Model") is not None and payload["Model"] != "HY-Motion-1.0":
            raise ContractError("motion.text Model must be HY-Motion-1.0")
        if payload.get("RetargetFile") is not None:
            retarget = _file_object(payload, operation, "RetargetFile")
            if str(retarget["Type"]).upper() != "FBX":
                raise ContractError("motion.text RetargetFile must be FBX")
        for field_name in ("EnableMesh", "EnableRewrite", "EnableDurationEst"):
            if payload.get(field_name) is not None and not isinstance(payload[field_name], bool):
                raise ContractError("motion.text %s must be boolean" % field_name)
        if payload.get("RetargetFile") is not None or payload.get("EnableMesh") is True:
            warnings.append("RetargetFile/EnableMesh are passed through but are not production proof in this project.")
    elif operation == "parts.generate":
        file3d = _file_object(payload, operation, "File")
        if str(file3d["Type"]).upper() != "FBX":
            raise ContractError("parts.generate currently requires FBX input")
        if payload.get("Model") is not None and str(payload["Model"]) != "1.5":
            raise ContractError("parts.generate Model must be 1.5")
        if payload.get("EnableStagedGeneration") is True:
            warnings.append("EnableStagedGeneration may consume additional credits.")
    elif operation == "uv.unwrap":
        file3d = _file_object(payload, operation, "File")
        if str(file3d["Type"]).upper() not in {"FBX", "OBJ", "GLB"}:
            raise ContractError("uv.unwrap supports FBX, OBJ or GLB")
    elif operation == "topology.reduce":
        file3d = _file_object(payload, operation)
        if str(file3d["Type"]).upper() not in {"OBJ", "GLB"}:
            raise ContractError("topology.reduce supports OBJ or GLB")
        if payload.get("PolygonType") is not None and payload["PolygonType"] not in {"triangle", "quadrilateral"}:
            raise ContractError("topology.reduce PolygonType must be triangle or quadrilateral")
        if payload.get("FaceLevel") is not None and payload["FaceLevel"] not in {"high", "medium", "low"}:
            raise ContractError("topology.reduce FaceLevel must be high, medium or low")
    elif operation == "texture.generate":
        file3d = _file_object(payload, operation)
        if str(file3d["Type"]).upper() not in {"OBJ", "GLB"}:
            raise ContractError("texture.generate supports OBJ or GLB")
        if not payload.get("Prompt") and not payload.get("Image") and not payload.get("MultiViewImages"):
            raise ContractError("texture.generate requires Prompt, Image or MultiViewImages")
        if len(str(payload.get("Prompt", ""))) > 200:
            raise ContractError("texture.generate Prompt must be <= 200 characters")
        if payload.get("Model") is not None and str(payload["Model"]) not in {"3.0", "3.1"}:
            raise ContractError("texture.generate Model must be 3.0 or 3.1")
        texture_size = payload.get("TextureSize")
        if texture_size is not None and (not isinstance(texture_size, int) or not 720 <= texture_size <= 4096):
            raise ContractError("texture.generate TextureSize must be 720..4096")
        for field_name in ("EnableKeepUV", "EnablePBR"):
            if payload.get(field_name) is not None and not isinstance(payload[field_name], bool):
                raise ContractError("texture.generate %s must be boolean" % field_name)
    elif operation == "format.convert":
        file_url = payload.get("File3D")
        if not isinstance(file_url, str) or not file_url.strip():
            raise ContractError("format.convert File3D must be a URL string")
        output_format = payload.get("Format")
        if not isinstance(output_format, str) or output_format.upper() not in OPERATIONS[operation].expected_types:
            raise ContractError("format.convert Format must be FBX, STL, USDZ, MP4 or GIF")
    elif operation == "profile.generate":
        profile = payload.get("Profile")
        if not isinstance(profile, dict):
            raise ContractError("profile.generate requires Profile")
        profile_sources = [key for key in ("Base64", "Url") if profile.get(key)]
        if len(profile_sources) != 1:
            raise ContractError("profile.generate Profile requires exactly one Base64 or Url")

    if payload.get("ResultFormat") is not None:
        warnings.append("Explicit ResultFormat may change returned files or credit use; it is recorded in the manifest.")
    return warnings


validate_registry()
