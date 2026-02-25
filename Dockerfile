# Dockerfile for the CGE Bacterial Analysis Pipeline (BAP)
# ======================================================================

# For full reproducibility, pin the package versions installed by apt
# and conda when releasing to production, using 'package=version'.
# The 'apt-get' and 'conda list' commands output the versions in use.


# Load base Docker image
# ----------------------------------------------------------------------

# Use miniconda with Python 3.13
FROM docker.io/continuumio/miniconda3:25.3.1-1


# System dependencies
# ----------------------------------------------------------------------

# Debian packages
# - gcc and libz-dev for kma
# - g++ and gawk and libboost-iostreams for kcst
# - g++ and the libboost packages for SKESA
# - file for KCST

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get -qq update --fix-missing && \
    apt-get -qq install apt-utils && \
    dpkg --configure -a && \
    apt-get -qq install --no-install-recommends \
        make g++ gcc libc-dev libz-dev \
        gawk file \
        libboost-program-options-dev \
        libboost-iostreams-dev \
        libboost-regex-dev \
        libboost-timer-dev \
        libboost-chrono-dev \
        libboost-system-dev \
    && \
    apt-get -qq clean && \
    rm -rf /var/lib/apt/lists/*

# Stop container's bash from leaving .bash_histories everywhere
# and add convenience aliases for interactive (debugging) use
RUN echo "unset HISTFILE" >>/etc/bash.bashrc && \
    echo "alias ls='ls --color=auto' l='ls -CF' la='l -a' ll='l -l' lla='ll -a'" >>/etc/bash.bashrc


# Python dependencies
# ----------------------------------------------------------------------

# Python dependencies via Conda:
# - Install nomkl to prevent MKL being installed; we don't currently
#   use it, it's huge, and it is non-free (why does Conda pick it?)
# - Our jobcontrol module (picoline) requires psutil
# - Biopython and tabulate are used by all CGE services
# - ResFinder requires python-dateutil and gitpython
# - pandas required by cgelib since ResFinder 4.2.1
# - cgMLST requires ete3 in its make_nj_tree.py, which we don't use,
#   and spuriously in cgMLST.py, where we comment it out (see patch).
# - pyrodigal for cgMSLT

RUN conda install -c conda-forge -c bioconda --quiet --yes \
        nomkl 'biopython>=1.85' 'pandas>=2.1.4' 'numpy>=1.26.2' 'pyrodigal>=3.6.3' \
        psutil tabulate 'python-dateutil>=2.8.2' 'gitpython>=3.1.40' && \
    conda list && \
    conda clean -qafy


# Other dependencies
# ----------------------------------------------------------------------

# SKESA, BLAST, Quast, Flye are available in the 'bioconda' channel, but
# yield myriad dependency conflicts, hence we install them from source.
#
#    conda install -c conda-forge -c bioconda --quiet --yes \
#        blast skesa quast


# Install External Deps
#----------------------------------------------------------------------

# Installation root
RUN mkdir -p /usr/src
WORKDIR /usr/src

# Copy the externals to /usr/src/ext
# Note the .dockerignore filters out a lot
COPY ext ext

# Install BLAST by putting its binaries on the PATH,
# and prevent 2.11.0 phone home bug by opting out
# https://github.com/ncbi/blast_plus_docs/issues/15
ENV PATH=/usr/src/ext/ncbi-blast/bin:$PATH \
    BLAST_USAGE_REPORT=false

# Install uf-stats by putting it on the PATH.
ENV PATH=/usr/src/ext/unfasta:$PATH

# Make and install skesa (and gfa_connector, saute)
RUN cd ext/skesa && \
    make clean && make -j 6 -f Makefile.nongs && \
    mv skesa gfa_connector /usr/local/bin/ && \
    cd .. && rm -rf skesa

# Make and install flye
RUN cd ext/flye && \
    pip install -q --root-user-action ignore --no-cache-dir . && \
    cd .. && rm -rf flye

# Make and install kcst
RUN cd ext/kcst/src && \
    make clean && make -j 6 && \
    mv khc ../bin/kcst ../data/make-kcst-db.sh /usr/local/bin/ && \
    cd ../.. && rm -rf kcst

# Make and install kma
RUN cd ext/kma && \
    make clean && make -j 6 && \
    cp kma kma_index kma_shm /usr/local/bin/ && \
    cd .. && rm -rf kma

# Install kma-retrieve
RUN cd ext/odds-and-ends && \
    cp kma-retrieve /usr/local/bin/ && \
    cd .. && rm -rf odds-and-ends

# Install fastq-stats
RUN cd ext/fastq-utils && \
    make clean && make fastq-stats && \
    cp fastq-stats /usr/local/bin/ && \
    cd .. && rm -rf fastq-utils

# Install the picoline module
RUN cd ext/picoline && \
    pip install -q --root-user-action ignore --no-cache-dir . && \
    cd .. && rm -rf picoline

# Install the cgecore module
# TEMPORARY patch for: https://bitbucket.org/genomicepidemiology/cgecore/issues/1/module-alignmentpy-hidden-by-module
RUN cd ext/cgecore && \
    cp src/cgecore/alignment.py src/cgecore/alignment/__init__.py && \
    pip install -q --root-user-action ignore --no-cache-dir . && \
    cd .. && rm -rf cgecore

# Install the cgelib module
RUN cd ext/cgelib && \
    pip install -q --root-user-action ignore --no-cache-dir . && \
    cd .. && rm -rf cgelib


# Install CGE Services
#----------------------------------------------------------------------

# ResFinder since 4.2.1 recommends pip installation, but then pulls in
# old cgecore which breaks virulencefinder and others (no .gz support),
# so we install the dependencies ourselves (see above) and --no-deps.

# OVERRIDE the override for now and install from source
#RUN pip install --no-color --no-deps --no-cache-dir resfinder

# Install speciesfinder module from source
RUN python3 -m compileall ext/speciesfinder/src/speciesfinder && \
    printf '#!/bin/sh\nexport PYTHONPATH=/usr/src/ext/speciesfinder/src\nexec python3 -m speciesfinder "$@"\n' \
    > /usr/local/bin/speciesfinder && \
    chmod +x /usr/local/bin/speciesfinder

# Install resfinder module from source
RUN python3 -m compileall ext/resfinder/src/resfinder && \
    printf '#!/bin/sh\nexport PYTHONPATH=/usr/src/ext/resfinder/src\nexec python3 -m resfinder "$@"\n' \
    > /usr/local/bin/resfinder && \
    chmod +x /usr/local/bin/resfinder

# Install virulencefinder module from source
RUN python3 -m compileall ext/virulencefinder/src/virulencefinder && \
    printf '#!/bin/sh\nexport PYTHONPATH=/usr/src/ext/virulencefinder/src\nexec python3 -m virulencefinder "$@"\n' \
    > /usr/local/bin/virulencefinder && \
    chmod +x /usr/local/bin/virulencefinder

# Install plasmidfinder module from source
RUN python3 -m compileall ext/plasmidfinder/src/plasmidfinder && \
    printf '#!/bin/sh\nexport PYTHONPATH=/usr/src/ext/plasmidfinder/src\nexec python3 -m plasmidfinder "$@"\n' \
    > /usr/local/bin/plasmidfinder && \
    chmod +x /usr/local/bin/plasmidfinder

# Patch out massive unused cgmlstfinder ete3 dependency
RUN sed -i -Ee 's@^from ete3 import@#from ete3 import@' \
        'ext/cgmlstfinder/cgMLST.py'

# Precompile the services
RUN python3 -m compileall \
    ext/cgmlstfinder \
    ext/choleraefinder \
    ext/mlst \
    ext/pmlst

# Add service script directories to PATH
ENV PATH $PATH""\
":/usr/src/ext/cgmlstfinder"\
":/usr/src/ext/choleraefinder"\
":/usr/src/ext/mlst"\
":/usr/src/ext/pmlst"


# Install the BAP code
#----------------------------------------------------------------------

# Copy contents of src into /usr/src
COPY src ./

# Install the BAP specific code
RUN pip install -q --root-user-action ignore --no-cache-dir .


# Set up workdir and default command
#----------------------------------------------------------------------

# Change to the mounted workdir as initial PWD
WORKDIR /workdir

# No ENTRYPOINT means that any binary on the PATH in the container can
# be run.  Set CMD so that without arguments, user gets BAP --help.
CMD ["BAP", "--help"]

