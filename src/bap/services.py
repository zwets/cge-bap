#!/usr/bin/env python3
#
# bap.services - Defines the services used by the BAP workflow
#
#   This module defines the SERVICES dict that maps each Service.* enum
#   defined in .workflow to a class (called a 'shim') that implements
#   the service.
#

# Import the Services enum
from .workflow import Services

# Import the shim classes that implement each service
from .shims.base import UnimplementedService
from .shims.cgMLSTFinder import cgMLSTFinderShim
from .shims.CholeraeFinder import CholeraeFinderShim
from .shims.ContigsMetrics import ContigsMetricsShim
from .shims.DisinFinder import DisinFinderShim
from .shims.GetReference import GetReferenceShim
from .shims.GFAConnector import GFAConnectorShim
from .shims.Flye import FlyeShim
from .shims.KCST import KCSTShim
from .shims.KmerFinder import KmerFinderShim
from .shims.MLSTFinder import MLSTFinderShim
from .shims.PlasmidFinder import PlasmidFinderShim
from .shims.pMLST import pMLSTShim
from .shims.PointFinder import PointFinderShim
from .shims.ReadsMetrics import ReadsMetricsShim
from .shims.ResFinder import ResFinderShim
from .shims.SKESA import SKESAShim
from .shims.VirulenceFinder import VirulenceFinderShim

SERVICES = {
    Services.CONTIGSMETRICS:    ContigsMetricsShim(),
    Services.READSMETRICS:      ReadsMetricsShim(),
    Services.SKESA:             SKESAShim(),
    Services.FLYE:              FlyeShim(),
    Services.GFACONNECTOR:      GFAConnectorShim(),
    Services.KCST:              KCSTShim(),
    Services.MLSTFINDER:        MLSTFinderShim(),
    Services.KMERFINDER:        KmerFinderShim(),
    Services.GETREFERENCE:      GetReferenceShim(),
    Services.RESFINDER:         ResFinderShim(),
    Services.POINTFINDER:       PointFinderShim(),
    Services.DISINFINDER:       DisinFinderShim(),
    Services.VIRULENCEFINDER:   VirulenceFinderShim(),
    Services.PLASMIDFINDER:     PlasmidFinderShim(),
    Services.PMLSTFINDER:       pMLSTShim(),
    Services.CGMLSTFINDER:      cgMLSTFinderShim(),
    Services.CHOLERAEFINDER:    CholeraeFinderShim(),
}

# Check that every enum that is defined has a mapping to a service
for s in Services:
    assert s in SERVICES, "No service shim defined for service %s" % s

