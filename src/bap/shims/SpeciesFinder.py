#!/usr/bin/env python3
#
# bap.shims.SpeciesFinder - service shim to the SpeciesFinder backend
#

import os, glob, logging
from pico.workflow.executor import Task
from pico.jobcontrol.job import JobSpec, Job
from .base import ServiceExecution, UserException
from .versions import BACKEND_VERSIONS

# Our service name and current backend version
SERVICE, VERSION = "SpeciesFinder", BACKEND_VERSIONS['speciesfinder']

# Backend resource parameters: cpu, memory, disk, run time reqs
MAX_CPU = 1
MAX_MEM = 8
MAX_TIM = 10 * 60


class SpeciesFinderShim:
    '''Service shim that executes the backend.'''

    def execute(self, sid, xid, blackboard, scheduler):
        '''Invoked by the executor.  Creates, starts and returns the Task.'''

        execution = SpeciesFinderExecution(SERVICE, VERSION, sid, xid, blackboard, scheduler)

        # Get the execution parameters from the blackboard
        try:
            sf_scheme = execution.get_user_input('sf_s')
            db_path, tax_file = find_db(execution.get_db_path('speciesfinder'), sf_scheme)
            inputs = list(map(os.path.abspath, execution.get_fastq_or_contigs_paths()))
            params = [
                '-db', db_path,
                '-o', '.',
                '-i' ] + inputs
            if tax_file:
                params.extend(['-tax', tax_file])

            job_spec = JobSpec('speciesfinder', params, MAX_CPU, MAX_MEM, MAX_TIM)
            execution.store_job_spec(job_spec.as_dict())
            execution.start(job_spec, sf_scheme)

        # Failing inputs will throw UserException
        except UserException as e:
            execution.fail(str(e))

        # Deeper errors additionally dump stack
        except Exception as e:
            logging.exception(e)
            execution.fail(str(e))

        return execution


class SpeciesFinderExecution(ServiceExecution):
    '''A single execution of the service, returned by the shim's execute().'''

    _job = None

    def start(self, job_spec, scheme):
        if self.state == Task.State.STARTED:
            self._job = self._scheduler.schedule_job('kf_%s' % scheme, job_spec, os.path.join(SERVICE,scheme))


    # Parse the output produced by the backend service, return list of hits
    def collect_output(self, job):
        '''Collect the job output and put on blackboard.
           This method is called by super().report() once job is done.'''

        # Depending on whether there was a tax file
        results_file = job.file_path('results.txt')
        have_tax = os.path.exists(results_file)
        if not have_tax:
            results_file = job.file_path('results.res')
            if not os.path.isfile(results_file):
                self.fail("service ran but no results.txt or results.res file in %s", job.file_path(""))
                return False

        # The result list
        hits = list()      # list of detailed hit objects

        with open(results_file, 'r') as f:

            # The res (no tax) file has these columns, where Template matches one in the database.name file
            # - Template (Accession " " Desc),Score,Expected,Template_length,Template_Identity,Template_Coverage,Query_Identity,Query_Coverage,Depth,q_value,p_value
            # The tax file has these (note Accession here is not one from the res file, but the new GCF accession (and Assembly is unique)
            # - Assembly=Accession,Score,Expected,Template_length,Template_Identity,Template_Coverage,Query_Identity,Query_Coverage,Depth,q_value,p_value,Accession Number,Description,TAXID,Taxonomy,TAXID,Species

            # Skip header
            f.readline()
            line = f.readline()

            # Parse all hits
            while line:

                rec = line.split('\t')

                # Bail out completely if line doesn't have the right number of record
                if (have_tax and len(rec) != 17) or (not have_tax and len(rec) != 11):
                    self.fail('invalid line in SpeciesFinder results: %s' % line)
                    return

                # The accession and description are at 13,14 in tax, and joined at 0 in non-tax
                acc_dsc = [rec[11].strip(), rec[12].strip()] if have_tax else rec[0].strip().split(' ')

                # Construct the hit object from the shared fields
                hit = { 'accession' : acc_dsc[0],
                        'desc' : acc_dsc[1],
                        'score' : int(rec[1]),
                        'expected' : int(rec[2]),
                        'slen' : int(rec[3]),
                        'sident' : float(rec[4]),
                        'scov' : float(rec[5]),
                        'qident' : float(rec[6]),
                        'qcov' : float(rec[7]),
                        'depth' : float(rec[8]),
                        'q_value' : float(rec[9]),
                        'p_value' : float(rec[10]) }

                # Add the taxonomy if we have it
                if have_tax:
                    hit['strain_taxid'] = int(rec[13])
                    hit['lineage'] = [s.strip() for s in rec[14].split(';')]
                    hit['taxid'] = int(rec[15])
                    hit['species'] = rec[16].strip()

                # Append to the list of hits
                hits.append(hit)

                # Iterate to next line
                line = f.readline()

        # Store result
        self.store_results(hits)

        # Store species to global BAP findings
        if have_tax and len(hits):
            self._blackboard.add_detected_species(hits[0].get('species'))

        # Store closest reference in global BAP findings
        if len(hits):
            self._blackboard.put_closest_reference(hits[0].get('accession'), hits[0].get('desc'))


# Locates database under db_root, returns (db_path, tax_file)
# or raises an exception with appriopriate error message
def find_db(db_root, name):

    # Locate the database by checking for a .seq.b file
    matches = glob.glob(os.path.join(db_root, name, f"{name}*.seq.b"))
    if not matches:
        raise UserException("database '%s' not found; databases are: %s", name,
            ', '.join(map(os.path.dirname, glob.glob(f"{name}/{name}*.seq.b", root_dir = db_root))))
    db_path = matches[0].replace('.seq.b','')

    # Locate the optional tax file
    tax = db_path + '.tax'
    if not os.path.isfile(tax):
        tax = None

    return (db_path, tax)

