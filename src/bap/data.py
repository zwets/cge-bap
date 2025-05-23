#!/usr/bin/env python3
#
# bap.data
#
#   Defines the data structures that are shared across the BAP services.
#

import os, enum
from datetime import datetime
from pico.workflow.blackboard import Blackboard


### BAPBlackboard class
#
#   Wraps the generic Blackboard with an API that adds getters and putters for
#   data shared between BAP services, so they're not randomly grabbing around
#   in bags of untyped data.

class BAPBlackboard(Blackboard):
    '''Adds to the generic Blackboard getters and putters specific to the shared
       data definitions in the current BAP.'''

    def __init__(self, verbose=False):
        super().__init__(verbose)

    # BAP-level methods

    def start_run(self, service, version, user_inputs):
        self.put('bap/run_info/service', service)
        self.put('bap/run_info/version', version)
        self.put('bap/run_info/time/start', datetime.now().isoformat(timespec='seconds'))
        self.put('bap/user_inputs', user_inputs)

    def end_run(self, state):
        start_time = datetime.fromisoformat(self.get('bap/run_info/time/start'))
        end_time = datetime.now()
        self.put('bap/run_info/time/end', end_time.isoformat(timespec='seconds'))
        self.put('bap/run_info/time/duration', (end_time - start_time).total_seconds())
        self.put('bap/run_info/status', state)

    def put_user_input(self, param, value):
        return self.put('bap/user_inputs/%s' % param, value)

    def get_user_input(self, param, default=None):
        return self.get('bap/user_inputs/%s' % param, default)

    def add_warning(self, warning):
        '''Stores a warning on the 'bap' top level (note: use service warning instead).'''
        self.append_to('bap/warnings', warning)

    # Standard methods for BAP common data

    def put_db_root(self, path):
        '''Stores the root of the BAP services databases.'''
        self.put_user_input('db_root', path)

    def get_db_root(self):
        '''Retrieve the user_input/db_root, this must be set.'''
        db_root = self.get_user_input('db_root')
        if not db_root:
            raise Exception("database root path is not set")
        elif not os.path.isdir(db_root):
            raise Exception("db root path is not a directory: %s" % db_root)
        return os.path.abspath(db_root)

    # Sample ID

    def put_sample_id(self, id):
        '''Store id as the sample id in the summary.'''
        self.put('bap/summary/sample_id', id)

    def get_sample_id(self):
        return self.get('bap/summary/sample_id', 'unknown')

    # Contigs and reads

    def put_illufq_paths(self, paths):
        '''Stores the illumina paths as its own (pseudo) user input.'''
        self.put_user_input('illumina_fqs', paths)

    def get_illufq_paths(self, default=None):
        return self.get_user_input('illumina_fqs', default)

    def put_nanofq_path(self, path):
        '''Stores the Nanopore fastq path as its own (pseudo) user input.'''
        self.put_user_input('nano_fq', path)

    def get_nanofq_path(self, default=None):
        return self.get_user_input('nano_fq', default)

    def put_user_contigs_path(self, path):
        '''Stores the contigs path as its own (pseudo) user input.'''
        self.put_user_input('contigs', path)

    def get_user_contigs_path(self, default=None):
        return self.get_user_input('contigs', default)

    def put_assembled_contigs_path(self, path):
        '''Stores the path to the computed contigs.'''
        self.put('bap/summary/contigs', path)

    def get_assembled_contigs_path(self, default=None):
        return self.get('bap/summary/contigs', default)

    def put_graph_path(self, path):
        '''Stores the path to the GFA file.'''
        self.put('bap/summary/graph', path)

    def get_graph_path(self, default=None):
        return self.get('bap/summary/graph', default)

    # Species

    def put_user_species(self, lst):
        '''Stores list of species specified by user.'''
        self.put_user_input('species', lst)

    def get_user_species(self, default=None):
        return self.get_user_input('species', default)

    def add_detected_species(self, lst):
        self.append_to('bap/summary/species', lst, True)

    def get_detected_species(self, default=None):
        return self.get('bap/summary/species', default)

    def get_species(self, default=None):
        ret = list()
        ret.extend(self.get_user_species(list()))
        ret.extend(self.get_detected_species(list()))
        return ret if ret else default

    # Reference

    def put_closest_reference(self, acc, desc):
        '''Stores the accession and description of closest reference.'''
        self.put('bap/summary/closest/accession', acc)
        self.put('bap/summary/closest/name', desc)

    def put_closest_reference_path(self, path):
        '''Stores the path to the closest reference genome.'''
        self.put('bap/summary/closest/path', path)

    def put_closest_reference_length(self, length):
        '''Stores the length of the closest reference genome.'''
        self.put('bap/summary/closest/length', length)

    def get_closest_reference(self, default=None):
        '''Returns dict with fields accession, name, path, length, or the default.'''
        return self.get('bap/summary/closest', default)

    def get_closest_reference_path(self, default=None):
        return self.get_closest_reference({}).get('path', default)

    def get_closest_reference_length(self, default=None):
        return self.get_closest_reference({}).get('length', default)

    # MLST

    def add_mlst(self, name, st, loci, alleles, near):
        str = "%s %s [%s]" % (name, st, ' '.join(map(lambda l: '%s:%s' % l, zip(loci, alleles))))
        if near:
            str += " (near %s)" % ' '.join(near)
        self.append_to('bap/summary/mlst', str, True)

    def get_mlsts(self):
        return sorted(self.get('bap/summary/mlst', []))

    # Plasmids

    def put_user_plasmids(self, lst):
        '''Stores list of plasmids specified by user.'''
        self.put_user_input('plasmids', lst)

    def get_user_plasmids(self, default=None):
        return sorted(self.get_user_input('plasmids', default))

    def add_detected_plasmid(self, plasmid):
        self.append_to('bap/summary/plasmids', plasmid, True)

    def get_detected_plasmids(self, default=None):
        return sorted(self.get('bap/summary/plasmids', default))

    def get_plasmids(self, default=None):
        ret = list()
        ret.extend(self.get_user_plasmids(list()))
        ret.extend(self.get_detected_plasmids(list()))
        return ret if ret else default

    def add_pmlst(self, profile, st):
        str = "%s%s" % (profile, st)
        self.append_to('bap/summary/pmlsts', str)

    def get_pmlsts(self):
        return sorted(self.get('bap/summary/pmlsts', []))

    # Virulence

    def add_detected_virulence_gene(self, gene):
        self.append_to('bap/summary/virulence_genes', gene, True)

    def get_virulence_genes(self):
        return sorted(self.get('bap/summary/virulence_genes', []))

    # Resistance

    def add_amr_gene(self, gene):
        self.append_to('bap/summary/amr_genes', gene, True)

    def get_amr_genes(self):
        return sorted(self.get('bap/summary/amr_genes', []))

    def add_amr_class(self, classes):
        self.append_to('bap/summary/amr_classes', classes, True)

    def get_amr_classes(self):
        return sorted(self.get('bap/summary/amr_classes', []))

    def add_amr_antibiotic(self, pheno):
        self.append_to('bap/summary/amr_antibiotics', pheno, True)

    def get_amr_antibiotics(self):
        return sorted(self.get('bap/summary/amr_antibiotics', []))

    def add_amr_mutation(self, mut):
        self.append_to('bap/summary/amr_mutations', mut, True)

    def get_amr_mutations(self):
        return sorted(self.get('bap/summary/amr_mutations', []))

    def add_dis_gene(self, gene):
        self.append_to('bap/summary/dis_genes', gene, True)

    def get_dis_genes(self):
        return sorted(self.get('bap/summary/dis_genes', []))

    def add_dis_resistance(self, dis):
        self.append_to('bap/summary/dis_resistances', dis, True)

    def get_dis_resistances(self):
        return sorted(self.get('bap/summary/dis_resistances', []))

    # cgMLST

    def add_cgmlst(self, scheme, st, pct):
        str = '%s:%s(%s%%)' % (scheme, st, pct)
        self.append_to('bap/summary/cgmlst', str, True)

    def get_cgmlsts(self):
        return sorted(self.get('bap/summary/cgmlst', []))

