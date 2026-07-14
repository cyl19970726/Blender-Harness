from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Tuple

from ....io import ContractError


@dataclass(frozen=True)
class OperationSpec:
    operation: str
    method: str
    endpoint: str
    artifact_role: str
    expected_types: Tuple[str, ...]
    validation_level: str = "official_only"
    is_async: bool = True
    submit_enabled: bool = False
    primary_output_fields: Tuple[str, ...] = ()
    preview_output_fields: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["expected_types"] = list(self.expected_types)
        value["primary_output_fields"] = list(self.primary_output_fields)
        value["preview_output_fields"] = list(self.preview_output_fields)
        return value


# Snapshot of the public Tripo v3 surface used by Blender Harness on 2026-07-13.
# Registry presence means that the adapter knows how to submit/poll/fetch the
# operation. It does not mean that the operation has been live-verified or that
# its output is approved as a Blender asset.
OPERATIONS: Dict[str, OperationSpec] = {
    "geometry.text": OperationSpec(
        "geometry.text", "POST", "/generation/text-to-model",
        "raw_geometry_candidate", ("GLB",),
    ),
    "geometry.image": OperationSpec(
        "geometry.image", "POST", "/generation/image-to-model",
        "raw_geometry_candidate", ("GLB",),
    ),
    "geometry.multiview": OperationSpec(
        "geometry.multiview", "POST", "/generation/multiview-to-model",
        "raw_geometry_candidate", ("GLB",), "synthetic_contract", True, True,
        ("model_url",), ("rendered_image_url",),
    ),
    "multiview.generate": OperationSpec(
        "multiview.generate", "POST", "/generation/image-to-multiview",
        "multiview_reference_candidate", ("PNG", "JPEG"),
    ),
    "multiview.edit": OperationSpec(
        "multiview.edit", "POST", "/generation/edit-multiview",
        "multiview_reference_candidate", ("PNG", "JPEG"),
    ),
    "model.import": OperationSpec(
        "model.import", "POST", "/models/import",
        "imported_model_candidate", ("GLB", "GLTF", "FBX", "OBJ", "STL"),
    ),
    "texture.generate": OperationSpec(
        "texture.generate", "POST", "/models/texture",
        "textured_asset_candidate", ("GLB",),
    ),
    "topology.retopology": OperationSpec(
        "topology.retopology", "POST", "/mesh/decimate",
        "retopology_candidate", ("GLB", "FBX", "OBJ"),
    ),
    "parts.segment": OperationSpec(
        "parts.segment", "POST", "/mesh/segment",
        "part_set_candidate", ("GLB",),
    ),
    "parts.complete": OperationSpec(
        "parts.complete", "POST", "/mesh/complete",
        "completed_part_candidate", ("GLB",),
    ),
    "rig.check": OperationSpec(
        "rig.check", "POST", "/animations/rig-check",
        "riggability_report", ("JSON",), is_async=False,
    ),
    "rig.auto": OperationSpec(
        "rig.auto", "POST", "/animations/rig",
        "draft_rigged_character", ("GLB", "FBX"),
    ),
    "motion.preset": OperationSpec(
        "motion.preset", "POST", "/animations/retarget",
        "animated_character_candidate", ("GLB", "FBX"),
    ),
    "format.convert": OperationSpec(
        "format.convert", "POST", "/models/convert",
        "converted_asset_candidate", ("GLB", "GLTF", "FBX", "OBJ", "STL", "USDZ"),
    ),
}


def validate_request(operation: str, request: Dict[str, Any]) -> Tuple[str, ...]:
    if operation not in OPERATIONS:
        raise ContractError("unsupported Tripo operation: %s" % operation)
    if not isinstance(request, dict):
        raise ContractError("Tripo request must be a JSON object")
    if not OPERATIONS[operation].submit_enabled:
        raise ContractError(
            "Tripo operation %s is official_only and not enabled for submit" % operation
        )
    warnings = []
    if operation == "geometry.multiview":
        inputs = request.get("inputs")
        if not isinstance(inputs, list) or len(inputs) != 4:
            raise ContractError("Tripo geometry.multiview requires four inputs")
        if all(isinstance(item, dict) and "path" in item for item in inputs):
            views = [str(item.get("view") or "").lower() for item in inputs]
            if views != ["front", "left", "back", "right"]:
                raise ContractError(
                    "local Tripo multiview inputs must be ordered front, left, back, right"
                )
        elif not all(isinstance(item, str) and item for item in inputs):
            raise ContractError(
                "Tripo multiview inputs must be four file tokens or four {view,path} objects"
            )
        model = request.get("model")
        if not isinstance(model, str) or not model:
            raise ContractError("Tripo geometry.multiview requires an explicit model version")
        face_limit = request.get("face_limit")
        if face_limit is not None and (not isinstance(face_limit, int) or not 48 <= face_limit <= 20000):
            raise ContractError("Tripo face_limit must be an integer from 48 to 20000")
        if request.get("texture") is False and request.get("pbr") is True:
            warnings.append("pbr=true has no useful effect when texture=false")
    return tuple(warnings)
