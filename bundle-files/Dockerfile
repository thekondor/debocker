FROM ${image}
MAINTAINER Tomasz Buchert <tomasz@debian.org>

ENV DEBIAN_FRONTEND noninteractive

#
# ADD ./steps /root/steps
#

ADD ./steps/01-upgrade /root/steps/01-upgrade
RUN /root/steps/01-upgrade '${args_01}'

ADD ./steps/02-install-utils /root/steps/02-install-utils
RUN /root/steps/02-install-utils '${args_02}'

ADD ./control /root/control
ADD ./steps/03-install-deps /root/steps/03-install-deps
RUN /root/steps/03-install-deps '${args_03}'

COPY ./source/* ./info /root/source/
ADD ./steps/04-extract-source /root/steps/04-extract-source
RUN ./root/steps/04-extract-source '${args_04}'

ADD ./steps/05-build /root/steps/05-build
ADD ./buildinfo /root/source/
RUN /root/steps/05-build '${args_05}'

ADD ./steps/build-tar /root/steps/build-tar
