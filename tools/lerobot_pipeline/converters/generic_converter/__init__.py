from typing import TYPE_CHECKING, Any

from .adapter import BaseAdapter
from .metadata import (
    annotate_dataset_info,
    annotate_feature,
    annotate_features,
    validate_feature_descriptions,
)
from .utils import ConversionTask, FeatureSpec, TaskMetadata

if TYPE_CHECKING:
    from .pipeline import aggregate_roots, run_converter


def __getattr__(name: str) -> Any:
    if name in {"aggregate_roots", "run_converter"}:
        from . import pipeline

        return getattr(pipeline, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BaseAdapter",
    "ConversionTask",
    "FeatureSpec",
    "TaskMetadata",
    "annotate_feature",
    "annotate_features",
    "annotate_dataset_info",
    "aggregate_roots",
    "run_converter",
    "validate_feature_descriptions",
]
