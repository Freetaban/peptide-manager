"""
Models package - espone tutte le classi modello e repository.
"""

from .base import BaseModel, Repository
from .supplier import Supplier, SupplierRepository
from .peptide import Peptide, PeptideRepository
from .batch import Batch, BatchRepository
from .batch_composition import BatchComposition, BatchCompositionRepository
from .preparation import Preparation, PreparationRepository
from .protocol import Protocol, ProtocolRepository
from .administration import Administration, AdministrationRepository
from .certificate import Certificate, CertificateDetail, CertificateRepository
from .protocol_template import (
    ProtocolTemplate,
    ProtocolTemplateRepository,
    ProtocolTemplatePeptide,
    ProtocolTemplatePeptideRepository
)
from .treatment_plan import (
    TreatmentPlan, 
    TreatmentPlanRepository,
    TreatmentPlanPreparation,
    TreatmentPlanPreparationRepository
)
from .planner import (
    PlanPhase,
    PlanPhaseRepository,
    ResourceRequirement,
    ResourceRequirementRepository,
    PlanSimulation,
    PlanSimulationRepository
)
from .vendor_product import (
    VendorProduct,
    VendorProductRepository,
    ConsumableDefault,
    ConsumableDefaultRepository
)
from .treatment_plan_template import (
    TreatmentPlanTemplate,
    TreatmentPlanTemplateRepository,
    TemplateBuilder
)

__all__ = [
    'BaseModel',
    'Repository',
    'Supplier',
    'SupplierRepository',
    'Peptide',
    'PeptideRepository',
    'Batch',
    'BatchRepository',
    'BatchComposition',
    'BatchCompositionRepository',
    'Preparation',
    'PreparationRepository',
    'Protocol',
    'ProtocolRepository',
    'Administration',
    'AdministrationRepository',
    'Certificate',
    'CertificateDetail',
    'CertificateRepository',
    'ProtocolTemplate',
    'ProtocolTemplateRepository',
    'ProtocolTemplatePeptide',
    'ProtocolTemplatePeptideRepository',
    'TreatmentPlan',
    'TreatmentPlanRepository',
    'TreatmentPlanPreparation',
    'TreatmentPlanPreparationRepository',
    # Planner models
    'PlanPhase',
    'PlanPhaseRepository',
    'ResourceRequirement',
    'ResourceRequirementRepository',
    'PlanSimulation',
    'PlanSimulationRepository',
    # Vendor products
    'VendorProduct',
    'VendorProductRepository',
    'ConsumableDefault',
    'ConsumableDefaultRepository',
    # Treatment plan templates
    'TreatmentPlanTemplate',
    'TreatmentPlanTemplateRepository',
    'TemplateBuilder',
]
