#!/usr/bin/env python3
#
# bap.shims.PlasmidFinder - service shim to the PlasmidFinder backend
#

import os, json, logging, tempfile
from pico.workflow.executor import Task
from pico.jobcontrol.job import JobSpec, Job
from .base import ServiceExecution, UserException
from .versions import BACKEND_VERSIONS

# Our service name and current backend version
SERVICE, VERSION = "PlasmidFinder", BACKEND_VERSIONS['plasmidfinder']

# Backend resource parameters: cpu, memory, disk, run time
MAX_CPU = 1
MAX_MEM = 1
MAX_TIM = 10 * 60


class PlasmidFinderShim:
    '''Service shim that executes the backend.'''

    def execute(self, sid, xid, blackboard, scheduler):
        '''Invoked by the executor.  Creates, starts and returns the Task.'''

        execution = PlasmidFinderExecution(SERVICE, VERSION, sid, xid, blackboard, scheduler)

        # Get the execution parameters from the blackboard
        try:
            db_path = execution.get_db_path('plasmidfinder')
            min_ident = execution.get_user_input('pf_i')
            min_cov = execution.get_user_input('pf_c')
            search_list = list(filter(None, execution.get_user_input('pf_s', '').split(',')))
            # Note: errors out if only Nanopore reads available (which we can't handle yet)
            inputs = list(map(os.path.abspath, execution.get_illufq_or_contigs_paths()))

            params = [
                '-q',
                '-j', 'data.json',
                '-p', db_path,
                '-t', min_ident,
                '-l', min_cov,
                '-i' ] + inputs
            if search_list:
                params.extend(['-d', ','.join(search_list)])

            execution.start(db_path, params, search_list)

        # Failing inputs will throw UserException
        except UserException as e:
            execution.fail(str(e))

        # Deeper errors additionally dump stack
        except Exception as e:
            logging.exception(e)
            execution.fail(str(e))

        return execution


class PlasmidFinderExecution(ServiceExecution):
    '''A single execution of the service, returned by the shim's execute().'''

    _service_name = 'plasmidfinder'
    _search_dict = None
    _tmp_dir = None
    _job = None

    # Start the execution on the scheduler
    def start(self, db_path, params, search_list):
        '''Start a job for plasmidfinder, with the given parameters.'''

        cfg_dict = parse_config(db_path)
        self._search_dict = find_databases(cfg_dict, search_list)

        job_spec = JobSpec('plasmidfinder', params, MAX_CPU, MAX_MEM, MAX_TIM)
        self.store_job_spec(job_spec.as_dict())

        if self.state == Task.State.STARTED:
            self._tmp_dir = tempfile.TemporaryDirectory()
            job_spec.args.extend(['--tmp_dir', self._tmp_dir.name])
            self._job = self._scheduler.schedule_job('plasmidfinder', job_spec, 'PlasmidFinder')

    # Collect the output produced by the backend service and store on blackboard
    def collect_output(self, job):
        '''Collect the job output and put on blackboard.
           This method is called by super().report() once job is done.'''

        # Clean up the tmp dir used by backend
        self._tmp_dir.cleanup()
        self._tmp_dir = None

        res_out = dict()

        out_file = job.file_path('data.json')
        try:
            with open(out_file, 'r') as f: json_in = json.load(f)
        except Exception as e:
            logging.exception(e)
            self.fail('failed to open or load JSON from file: %s' % out_file)
            return

        # PlasmidFinder since 3.0.1 has standardised JSON with these elements:
        # seq_regions (plasmid loci), seq_variations (empty), phenotypes (empty)

        # We include these but change them from objects to lists, so this:
        #   'seq_regions' : { 'XYZ': { ..., 'key' : 'XYZ', ...
        # becomes:
        #   'seq_regions' : [ { ..., 'key' : 'XYZ', ... }, ...]
        # This is cleaner design (they have list semantics, not object), and
        # avoids issues downstream with keys containing JSON delimiters.

        for k, v in json_in.items():
            if k in ['seq_regions','seq_variations','phenotypes']:
                res_out[k] = [ o for o in v.values() ]
            else:
                res_out[k] = v

        for r in res_out['seq_regions']:
            self._blackboard.add_detected_plasmid(r.get('name','?unknown?'))

        self.store_results(res_out)


# Parse the config file into a dict of group->[database], or raise on error.
# Error includes the case where we find the same database (prefix) in two groups.
# Though this could theoretically be allowed, we error out as the backend doesn't
# (currently) handle this correctly: it counts the database in the first group only.

def parse_config(db_root):

    group_dbs = dict()
    databases = list()

    cfg = os.path.join(db_root, "config")
    if not os.path.exists(cfg):
        raise UserException('database config file missing: %s', cfg)

    with open(cfg) as f:
        for l in f:

            l = l.strip()
            if not l or l.startswith('#'): continue
            r = l.split('\t')
            if len(r) != 3:
                raise UserException('invalid database config line: %s', l)

            # See comment above, this should be possible in principle, but backend fails
            db = r[0].strip()
            if db in databases:
                raise UserException('non-unique database prefix in config: %s', db)
            databases.append(db)

            grp = r[1].strip()
            group_dbs[grp] = group_dbs.get(grp, []) + [db]

    return group_dbs


# Returns user-friendly string of databases (per group) from parsed config

def pretty_list_groups(cfg_dict):
    ret = ""
    for k, v in cfg_dict.items():
        ret += '%s (%s);' % (k, ', '.join(v))
    return ret

# If name matches a group, return tuple (group, [databases]) for that group,
# else if it matches a database inside some group, return (group, [name]),
# else error with the list of available groups and databases.

def find_database(cfg_dict, name):
    grp_dbs = cfg_dict.get(name)
    if grp_dbs is None:
        for grp in cfg_dict.keys():
            if name in cfg_dict.get(grp):
                return (grp,[name])
        raise UserException('unknown group or database: %s; available are: %s',
            name, pretty_list_groups(cfg_dict))
    else:
        return (name, grp_dbs)

# Return a dict group->[database] for the list of names.  Each name can name
# a group or database, as for find_database above.  If names is an empty list,
# returns the entire cfg_dict.

def find_databases(cfg_dict, names):
    db_dict = dict()
    for name in (names if names else cfg_dict.keys()):
        grp, dbs = find_database(cfg_dict, name)
        cur_dbs = db_dict.get(grp, [])
        for db in dbs:
            if db not in cur_dbs: cur_dbs.append(db)
        db_dict[grp] = cur_dbs
    return db_dict

