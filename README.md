# CGE Bacterial Analysis Pipeline (BAP)

## Introduction

The CGE Bacterial Analysis Pipeline (BAP) is an analysis pipeline for
bacterial genomics, built around off-line versions of the
[CGE services](https://genomicepidemiology.org/service) maintained by
the Centre for Genomic Epidemiology (CGE) at the Technical University
of Denmark (DTU).

The BAP orchestrates a standard workflow that processes sequencing reads
and/or contigs, and produces the following:

 * Genome assembly (optional) (SKESA, Flye)
 * Basic QC metrics over reads a/o contigs (fastq-stats, uf-stats)
 * Species identification (KmerFinder, KCST)
 * MLST (KCST, MLSTFinder)
 * Resistance profiling (ResFinder, PointFinder, DisinfFinder)
 * Plasmid detection and typing (PlasmidFinder, pMLST)
 * Virulence gene finding (VirulenceFinder)
 * Core genome MLST (optional) (cgMLSTFinder)

The BAP comes with sensible default settings and a standard workflow, but
can be adjusted with command line parameters.

#### Supported Inputs

Since release 3.3.0, the BAP can process Illumina reads, Nanopore reads, or
assembled contigs.  You can pass it one of the following:

 * A single FASTA file with (assembled) contigs
 * A pair of Illumina paired-end reads files _or_ a single Illumina reads file
 * A single Nanopore reads file

#### Generated Outputs

The BAP generates a JSON file `bap-results.json` that integrates the detailed
output from all the services, and a tab-separated `bap-summary.tsv` with just
the most important results.

It also retains all raw output from the individual services that have run.

#### About Assemblies

The BAP can do assembly, but doesn't do this by default.  It will perform
assembly only if either some service requires contigs as its input, or you
explicitly instruct the BAP to do assembly (see below).

> **Note**: Nanopore reads are likely to trigger the BAP to do assembly,
> because not all back-end services are ready for Nanopore reads, whereas
> most can process Illumina reads without the need to assemble first.

The BAP makes no effort to produce "polished" assemblies; use dedicated
tools if that is your goal.  The BAP invokes assemblers (currently SKESA
for Illumina reads, Flye for Nanopore) with their recommended settings.
Both (claim to) do a decent job on unprocessed raw reads.


## Usage

Default run on a genome assembly:

    BAP assembly.fna

Same but on paired-end Illumina reads:

    BAP read_1.fq.gz read_2.fq.gz

Same but also produce the assembled genome:

    BAP -t DEFAULT,assembly read_1.fq.gz read_2.fq.gz

#### Targets

The `-t/--target` parameter specifies the analyses the BAP must do.
When omitted, it has value `DEFAULT`, which implies these targets:
`metrics`, `species`, `MLST`, `resistance`, `plasmids`, `virulence`
(`cgmlst` is not run by default due to its long runtime).

> Note how targets are 'logical' names for the tasks the BAP must do.
> The BAP will determine which services to involve, in what order,
> and what alternatives to try if a service fails.

See available targets:

    BAP --list-targets
    -> metrics species mlst resistance virulence plasmids ...

Perform _only_ assembly and species typing (by omitting the DEFAULT target):

    BAP -t assembly,species read_1.fq.gz read_2.fq.gz

Compute metrics only:

    BAP -t metrics read_1.fq.gz read_2.fq.gz

Do the defaults but _exclude_ metrics:

    BAP -x metrics read_1.fq.gz read_2.fq.gz

#### Service parameters

Service parameters can be passed to individual services in the pipeline.
For instance, to change ResFinder's identity and coverage thresholds:

    BAP --rf-i=0.95 --rf-c=0.8 assembly.fna

For an overview of available parameters, use `--help`:

    BAP --help

#### Advanced Usage

Call any of the backend services directly, not involving the BAP:

    bap-container-run kmerfinder --help
    bap-container-run SKESA --help

Run a terminal shell in the container:

    bap-container-run


## Installation

The BAP was developed to run on a moderately high-end Linux workstation
(see [history](#history-and-credits) below).  It is most easily installed
as a Podman, Singularity or Docker image.

The installation has two major steps: building the image, and downloading
the databases.

### Installation - Building the Image

Clone and enter this repository

    git clone https://github.com/zwets/cge-bap.git
    cd cge-bap

Download the backend services

    ext/update-backends.sh

Build the `cge-bap` image

    ./build.sh

    # Or manually do what build.sh does:
    #podman build -t localhost/cge-bap "." | tee build.log

Smoke test the container

    # Run 'BAP --help' in the container, using the bin/BAP wrapper.
    # (We set BAP_DB_DIR to a dummy as we have no databases yet)

    BAP_DB_DIR=/tmp bin/BAP --help

Index the test databases

    # This uses the kma_index and kcst indexers in the freshly built
    # image to index test/databases/*:

    scripts/index-databases.sh test/databases

Run on test data against the test databases:

    # Run tests
    cd test && ./run-tests.sh

If the tests above all end with with `[OK]`, you are good to go.  (Note
the test reads are just a small subset of a normal run, so the run output
for tests 02 and 03 is not representative.)

### Installation - CGE Databases

In the previous step we tested against the miniature test databases that
come with this repository.  In this step we install the real databases.

> NOTE: The download can take a _lot_ of time.  The KmerFinder and cgMLST
> databases in particular are very large (~100GB).  It is possible to run
> the BAP without these, but with loss of functionality.

Pick a location for the databases:

    # Remember to set this BAP_DB_DIR in bin/bap-container-run
    BAP_DB_DIR=/data/cge/db   # Path on my machine, replace by yours

Clone the CGE database repositories:

    mkdir -p "$BAP_DB_DIR"
    scripts/clone-databases.sh "$BAP_DB_DIR"

You now have databases for all services except KmerFinder and cgMLST.  To
download these (or a subset), follow the instructions in the repositories.

    cd "$BAP_DB_DIR/kmerfinder"
    less README.md   # has instructions on download and installation

Run tests against the real databases (ignore failure "does not match expected
output" as there may have been additions to the CGE databases):

    # With BAP_DB_DIR pointing at the installed databases
    test/test-04-fa-live.sh
    test/test-05-fq-live.sh

### Installation - Final Touches

If the tests succeeded, set `BAP_DB_DIR` in `bin/bap-container-run` to point
at the installed databases.

For convenience, add the `bin` directory to your `PATH` (edit your `~/.profile`),
or copy or symlink the `bin/BAP` script in `~/.local/bin` or `~/bin`.

Once this is done (you may need to logout and login), `BAP --help` should work.


## Development / Upgrades

To **upgrade to the latest BAP release**:

        git pull                # pulls the current edge
        git describe            # check that it is not a WIP commit
        git checkout x.y.z      # otherwise pick latest stable release
        ext/update-backends.sh  # remember always do this _before_ building
        ./build.sh`             # build and enjoy

To **update the CGE databases**

        # Just rerun the installation script (with same DB_DIR)
        scripts/clone-databases.sh DB_DIR

Updating any backend service can be done by changing its required version in
`ext/backend-versions.config`, then running:

        ext/update-backends.sh
        ./build.sh

Always **run tests after upgrading**:

        # Index the test databases (in the rare case they were upgraded)
        scripts/index-databases.sh test/databases

        # Runs the tests we ran above
        test/run-all-tests.sh


## History, Credits, License

### History

The CGE BAP is currently maintained thanks to funding from the Fleming Fund
SeqAfrica Project, a UK Aid investment to tackle AMR in LMICs.

The development of the CGE BAP (then called KCRI CGE BAP) previously took
place at the Kilimanjaro Clinical Research Institute, funded by Danish aid
through DANIDA Fellowship Centre grant DFC12-007DTU.

Prior to that, the original CGE BAP (citation below, source code at
<https://bitbucket.org/genomicepidemiology/cge-tools-docker.git>) was
conceived and developed at the Centre for Genomic Epidemiology at DTU.

The BAP was developed to run on modest hardware, including laptops that
could be used in the field.  It will still run comfortably on an 8-core,
32GB machine.

As the BAP evolved, its workflow logic became unwieldy and was factored into
a simple generic mechanism (now at <https://github.com/zwets/picoline>),
and BAP-specifics (workflow definitions and service shims), here in the
`src/bap` package.

### Citation

For publications please cite the URL <https://github.com/zwets/cge-bap>
of this repository, and the paper on the original concept:

_A Bacterial Analysis Platform: An Integrated System for Analysing Bacterial
Whole Genome Sequencing Data for Clinical Diagnostics and Surveillance._
Martin Christen Fr�lund Thomsen, Johanne Ahrenfeldt, Jose Luis Bellod Cisneros,
Vanessa Jurtz, Mette Voldby Larsen, Henrik Hasman, Frank M�ller Aarestrup,
Ole Lund; PLoS One. 2016; 11(6): e0157718.

Refer to the individual tools invoked by the BAP for their preferred citations.

#### Licence

Copyright 2016-2019 Center for Genomic Epidemiology, Technical University of Denmark  
Copyright 2018-2022 Kilimanjaro Clinical Research Institute, Tanzania  
Copyright 2023-2024 Marco van Zwetselaar <io@zwets.it>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

