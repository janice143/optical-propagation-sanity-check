"""Core data model for propagation validation.

Provides the fundamental data structures: Grid, Wave, SampledField,
FieldSource, ROI, PropagationConfig, SimulationContract, and Report.
"""

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import (
    SampledField,
    FieldSource,
    SquareAperture,
    UniformField,
    GaussianBeam,
    AiryBeam,
)
from propagation_sanity.core.roi import ROI
from propagation_sanity.core.propagation_config import (
    PropagationMethod,
    EvanescentPolicy,
    PropagationConfig,
)
from propagation_sanity.core.simulation import SimulationContract
from propagation_sanity.core.report import (
    AssessmentType,
    ThresholdProvenance,
    ResultStatus,
    ReportItem,
    ValidationReport,
)

__all__ = [
    "Grid",
    "Wave",
    "SampledField",
    "FieldSource",
    "SquareAperture",
    "UniformField",
    "GaussianBeam",
    "AiryBeam",
    "ROI",
    "PropagationMethod",
    "EvanescentPolicy",
    "PropagationConfig",
    "SimulationContract",
    "AssessmentType",
    "ThresholdProvenance",
    "ResultStatus",
    "ReportItem",
    "ValidationReport",
]
