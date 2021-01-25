FROM --platform=linux/amd64 ubuntu:14.04
MAINTAINER Patrick Callier "pcallier@lab41.org"

RUN apt-get update
RUN apt-get install -y build-essential git-core python2.7 python-pip \
  gcc-multilib g++-multilib libc6 libc6-dev

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
RUN apt-get install -y python2.7-dev
RUN pip2 install numpy==1.16.6

# Install fave-align and fave-extract
#  git clone https://github.com/JoFrhwld/FAVE && \
ADD ./ /opt/FAVE
RUN cd /opt/FAVE && \
  # git checkout a6e2aeb3ba61e2af79157d0ace0e4a8cc40b1511 && \ # would overwrite my edits
  echo 'export PATH=$PATH:/opt/FAVE/FAVE-align:/opt/FAVE/FAVE-extract' >> /etc/profile


ENTRYPOINT [ "/bin/bash", "-lc", "--" ]

