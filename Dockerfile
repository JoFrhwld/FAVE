FROM ubuntu:14.04
MAINTAINER Patrick Callier "pcallier@lab41.org"

RUN apt-get update && \
  apt-get install -y build-essential git-core python python-pip && \
  gcc-multilib g++multilib libc6 libc6-dev

# Install HTK (must be in build directory)
# The licensing terms for this likely do NOT
# permit pushing to Docker Hub. Beware!
ADD HTK-3.4.1.tar.gz /opt/
# Modify source
RUN sed -i '1650s/ labid / labpr /' /opt/htk/HTKLib/HRec.c && \
# Build
    export CPPFLAGS=-UPHNALG && \
	cd /opt/htk && \
	./configure --without-x --disable-hslab && \
	make all && \
	make install


# Install SoX
RUN apt-get -y install sox

# Install numpy and dependencies
RUN pip install numpy

ENTRYPOINT [ "/bin/bash", "-c", "--" ]

