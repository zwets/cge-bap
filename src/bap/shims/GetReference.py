#!/usr/bin/env python3
#
# bap.shims.GetReference - service shim to the GetReference backend
#

import os, logging, functools
from pico.workflow.executor import Task
from pico.jobcontrol.job import JobSpec, Job
from .base import ServiceExecution, UserException, SkipException
from .KmerFinder import find_db as find_kmer_db
from .versions import BACKEND_VERSIONS

# Our service name and current backend version
SERVICE, VERSION = "GetReference", BACKEND_VERSIONS['odds-and-ends']

# Backend resource parameters: cpu, memory, disk, run time reqs
MAX_CPU = 1
MAX_MEM = 1
MAX_TIM = 1 * 60

# The Service class
class GetReferenceShim:
    '''Service shim that executes the backend.'''

    def execute(self, sid, xid, blackboard, scheduler):
        '''Invoked by the executor.  Creates, starts and returns the Task.'''

        # Check whether running is applicable, else throw to SKIP execution
        closest = blackboard.get_closest_reference(dict())
        accession = closest.get('accession')
        if not accession:
            raise SkipException('no closest reference accession was found')

        execution = GetReferenceExecution(SERVICE, VERSION, sid, xid, blackboard, scheduler)

        # From here run the execution, and FAIL it on exception
        try:
            # Retrieve the KMA database to retrieve the sequence from
            kf_dbroot = execution.get_db_path('kmerfinder')
            kf_search = execution.get_user_input('kf_s')
            kma_db, _tax = find_kmer_db(kf_dbroot, kf_search)

            # Write to accession.fna (assuming it has no weird chars)
            out_file = accession + '.fna'
            params = [ 
                '--out-file', out_file,
                kma_db,
                accession
            ]

            job_spec = JobSpec('kma-retrieve', params, MAX_CPU, MAX_MEM, MAX_TIM)
            execution.store_job_spec(job_spec.as_dict())
            execution.start(job_spec, out_file)

        # Failing inputs throw UserException and we mark it FAILED
        except UserException as e:
            execution.fail(str(e))

        # Deeper errors additionally dump stack
        except Exception as e:
            logging.exception(e)
            execution.fail(str(e))

        return execution

# Single execution of the service
class GetReferenceExecution(ServiceExecution):
    '''A single execution of the service.'''

    _job = None
    _out_file = None

    def start(self, job_spec, out_file):
        if self.state == Task.State.STARTED:
            self._out_file = out_file
            self._job = self._scheduler.schedule_job('kma-retrieve', job_spec, 'Reference')

    def collect_output(self, job):

        path = job.file_path(self._out_file)

        if os.path.isfile(path):
            length = 0
            with open(path, 'r') as f:
                length = functools.reduce(lambda a, l: a if l.startswith('>') else a + len(l.strip()), f, 0)
            self.store_results({ 'fasta_file': path, 'genome_length': length })
            self._blackboard.put_closest_reference_path(path)
            self._blackboard.put_closest_reference_length(length)
        else:
            self.fail("backend job produced no output, check: %s", job.file_path(""))

