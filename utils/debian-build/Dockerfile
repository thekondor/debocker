FROM debian:unstable
MAINTAINER Tomasz Buchert <tomasz@debian.org>

# Create an image that contains basic env.
# for building packages
# see 02 in steps

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y update && \
    apt-get -y upgrade && \
    apt-get -y --no-install-recommends install \
            devscripts pbuilder build-essential aptitude lintian && \
    apt-get clean

# rm -rf /var/lib/apt/lists/*

# TODO
# remove stuff below too?
# rm -rf /usr/share/doc &&
# rm -rf /usr/share/man &&
# rm -rf /usr/share/locale
