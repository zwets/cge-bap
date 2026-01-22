# Dockerfile for the CGE Bacterial Analysis Pipeline (BAP)
# ======================================================================

# Base image: Miniconda with Python 3.13
FROM docker.io/continuumio/miniconda3:25.3.1-1

# ----------------------------------------------------------------------
# System dependencies
# ----------------------------------------------------------------------

ENV DEBIAN_FRONTEND=noninteractive

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
        libboost-system-dev && \
    apt-get -qq clean && \
    rm -rf /var/lib/apt/lists/*

# Prevent bash history spam; add convenience aliases
RUN echo "unset HISTFILE" >> /etc/bash.bashrc && \
    echo "alias ls='ls --color=auto' l='ls -CF' la='l -a' ll='l -l' lla='ll -a'" \
    >> /etc/bash.bashrc

# ----------------------------------------------------------------------
# Python dependencies (Conda)
# ----------------------------------------------------------------------

RUN conda install -c conda-forge -c bioconda --quiet --yes \
        nomkl \
        'biopython>=1.85' \
        'pandas>=2.1.4' \
        'numpy>=1.26.2' \
        'pyrodigal>=3.6.3' \
        psutil \
        tabulate \
        'python-dateutil>=2.8.2' \
        'gitpython>=3.1.40' && \
    conda list && \
    conda clean -qafy

# ----------------------------------------------------------------------
# External tools
# ----------------------------------------------------------------------

RUN mkdir -p /usr/src
WORKDIR /usr/src

# Copy external sources
COPY ext ext

# BLAST
ENV PATH=/usr/src/ext/ncbi-blast/bin:$PATH \
    BLAST_USAGE_REPORT=false

# unfasta
ENV PATH=/usr/src/ext/unfasta:$PATH

# SKESA
RUN cd ext/skesa && \
    make clean && make -j6 -f Makefile.nongs && \
    mv skesa gfa_connector /usr/local/bin/ && \
    cd .. && rm -rf skesa

# Flye
RUN cd ext/flye && \
    pip install -q --root-user-action ignore --no-cache-dir . && \
    cd .. && rm -rf flye

# KCST
RUN cd ext/kcst/src && \
    make clean && make -j6 && \
    mv khc ../bin/kcst ../data/make-kcst-db.sh /usr/local/bin/ && \
    cd ../.. && rm -rf kcst

# KMA
RUN cd ext/kma && \
    make clean && make -j6 && \
    cp kma kma_index kma_shm /usr/local/bin/ && \
    cd .. && rm -rf kma

# kma-retrieve
RUN cd ext/odds-and-ends && \
    cp kma-retrieve /usr/local/bin/ && \
    cd .. && rm -rf odds-and-ends

# fastq-stats
RUN cd ext/fastq-utils && \
    make clean && make fastq-stats && \
    cp fastq-stats /usr/local/bin/ && \
    cd .. && rm -rf fastq-utils

# picoline
RUN cd ext/picoline && \
    pip install -q --root-user-action ignore --no-cache-dir . && \
    cd .. && rm -rf picoline

# cgecore (patched)
RUN cd ext/cgecore && \
    cp src/cgecore/alignment.py src/cgecore/alignment/__init__.py && \
    pip install -q --root-user-action ignore --no-cache-dir . && \
    cd .. && rm -rf cgecore

# cgelib
RUN cd ext/cgelib && \
    pip install -q --root-user-action ignore --no-cache-dir . && \
    cd .. && rm -rf cgelib

# ----------------------------------------------------------------------
# CGE services
# ----------------------------------------------------------------------

# ResFinder
RUN python3 -m compileall ext/resfinder/src/resfinder && \
    printf '#!/bin/sh\nexport PYTHONPATH=/usr/src/ext/resfinder/src\nexec python3 -m resfinder "$@"\n' \
    > /usr/local/bin/resfinder && \
    chmod +x /usr/local/bin/resfinder

# VirulenceFinder
RUN python3 -m compileall ext/virulencefinder/src/virulencefinder && \
    printf '#!/bin/sh\nexport PYTHONPATH=/usr/src/ext/virulencefinder/src\nexec python3 -m virulencefinder "$@"\n' \
    > /usr/local/bin/virulencefinder && \
    chmod +x /usr/local/bin/virulencefinder

# PlasmidFinder
RUN python3 -m compileall ext/plasmidfinder/src/plasmidfinder && \
    printf '#!/bin/sh\nexport PYTHONPATH=/usr/src/ext/plasmidfinder/src\nexec python3 -m plasmidfinder "$@"\n' \
    > /usr/local/bin/plasmidfinder && \
    chmod +x /usr/local/bin/plasmidfinder

# SpeciesFinder (replaces kmerfinder)
RUN python3 -m compileall ext/speciesfinder/src/speciesfinder && \
    printf '#!/bin/sh\nexport PYTHONPATH=/usr/src/ext/speciesfinder/src\nexec python3 -m speciesfinder "$@"\n' \
    > /usr/local/bin/speciesfinder && \
    chmod +x /usr/local/bin/speciesfinder

# Patch cgMLSTFinder ete3 import
RUN sed -i -Ee 's@^from ete3 import@#from ete3 import@' \
    ext/cgmlstfinder/cgMLST.py

# Precompile remaining services
RUN python3 -m compileall \
    ext/cgmlstfinder \
    ext/choleraefinder \
    ext/mlst \
    ext/pmlst

# Service paths
ENV PATH=$PATH\
:/usr/src/ext/cgmlstfinder\
:/usr/src/ext/choleraefinder\
:/usr/src/ext/speciesfinder\
:/usr/src/ext/mlst\
:/usr/src/ext/pmlst

# ----------------------------------------------------------------------
# BAP application
# ----------------------------------------------------------------------

COPY src ./

RUN pip install -q --root-user-action ignore --no-cache-dir .

WORKDIR /workdir

CMD ["BAP", "--help"]
