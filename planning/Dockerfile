FROM debian:buster as builder

# arguments for builder scope
ARG PYTHON=python3.7
ARG HEXLITE_JAVA_PLUGIN_API_JAR_VERSION_TAG=1.4.0
ARG HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH=/opt/hexlite/java-api/target/hexlite-java-plugin-api-${HEXLITE_JAVA_PLUGIN_API_JAR_VERSION_TAG}.jar
ARG HEXLITE_OWLAPI_PLUGIN_JAR_WITH_PATH=/opt/hexlite-owlapi-plugin/plugin/target/owlapiplugin-1.1.0.jar

RUN mkdir -p /opt/lib/${PYTHON}/site-packages/

RUN set -ex ; \
  apt-get update ; \
  apt-get install -y --no-install-recommends \
    wget git ca-certificates \
    build-essential $PYTHON python3-setuptools python3-dev python3-pip lua5.3 \
    openjdk-11-jre-headless openjdk-11-jdk-headless

COPY requirements.txt /

RUN set -ex ; \
  $PYTHON -m pip install --upgrade pip ; \
  $PYTHON -m pip install -r /requirements.txt

# install maven for building hexlite Java API
# (not the one shipped with buster, because it does not work with openjdk-11)
RUN set -ex ; \
  cd /opt ; \
  wget https://downloads.apache.org/maven/maven-3/3.8.1/binaries/apache-maven-3.8.1-bin.tar.gz ; \
  tar xvf apache-maven-3.8.1-bin.tar.gz ; \
  mv apache-maven-3.8.1 /opt/maven

ENV MAVEN_HOME /opt/maven
ENV PATH /opt/bin:/opt/maven/bin:$PATH
ENV PYTHONPATH /opt/lib/$PYTHON/site-packages/:$PYTHONPATH

# hexlite
RUN set -ex ; \
  cd /opt ; \
  git clone https://github.com/hexhex/hexlite.git --branch   master

# build hexlite
RUN set -ex ; \
  cd /opt/hexlite ; \
  python3 setup.py install --prefix=/opt ; \
  mvn compile package install

# run tests (optional)
RUN set -ex ; \
  cd /opt/hexlite/tests ; \
  CLASSPATH=${HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH} \
  ./run-tests.sh

#
# owlapi plugin
#

# clone
RUN set -ex ; \
  cd /opt ; \
  git clone https://github.com/hexhex/hexlite-owlapi-plugin.git --branch v1.2

# build
# TODO update version of JAR
RUN set -ex ; \
  cd /opt/hexlite-owlapi-plugin/plugin ; \
  CLASSPATH=${HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH} \
  mvn compile package

# remove unnecessary files
RUN set -ex ; \
  cd /opt ; \
  find -name "*.class" |xargs rm ; \
  find -name ".git" |xargs rm -rf ; \
  rm -rf jpype

# run tests (optional)
RUN set -ex ; \
  cd /opt/hexlite-owlapi-plugin/examples/koala ; \
  CLASSPATH=${HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH}:${HEXLITE_OWLAPI_PLUGIN_JAR_WITH_PATH} \
  hexlite --pluginpath /opt/hexlite/plugins/ \
    --plugin javaapiplugin  at.ac.tuwien.kr.hexlite.OWLAPIPlugin \
    --number 33 --stats --flpcheck=none querykoala1.hex ; \
  CLASSPATH=${HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH}:${HEXLITE_OWLAPI_PLUGIN_JAR_WITH_PATH} \
  hexlite --pluginpath /opt/hexlite/plugins/ \
    --plugin javaapiplugin  at.ac.tuwien.kr.hexlite.OWLAPIPlugin \
    --number 33 --stats --flpcheck=none querykoala2.hex

# this image is 1.1 GB

#
#
# here starts the slim image (532 MB)
#
#

FROM debian:buster-slim

# arguments for final image scope (must be repeated from above in second image)
ARG PYTHON=python3.7
ARG HEXLITE_JAVA_PLUGIN_API_JAR_VERSION_TAG=1.4.0
ARG HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH=/opt/hexlite/java-api/target/hexlite-java-plugin-api-${HEXLITE_JAVA_PLUGIN_API_JAR_VERSION_TAG}.jar
ARG HEXLITE_OWLAPI_PLUGIN_JAR_WITH_PATH=/opt/hexlite-owlapi-plugin/plugin/target/owlapiplugin-1.1.0.jar

ENV PATH /opt/bin:$PATH
ENV PYTHONPATH /opt/lib/${PYTHON}/site-packages/:$PYTHONPATH

RUN set -ex ; \
  mkdir /usr/share/man/man1/ ; \
  apt-get update ; \
  apt-get install -y --no-install-recommends \
    wget \
    $PYTHON python3-dev python3-setuptools python3-pip lua5.3 \
    openjdk-11-jre-headless ; \
    apt autoremove -y --purge ; apt clean ; apt autoclean

COPY requirements.txt /

# we only need build-essential for pip3 install, so we remove it afterwards
RUN set -ex ; \
  apt-get install -y --no-install-recommends build-essential ; \
  $PYTHON -m pip install --upgrade pip ; \
  $PYTHON -m pip install -r /requirements.txt ; \
  apt-get remove -y --purge build-essential ; \
  apt autoremove -y --purge ; apt clean ; apt autoclean

WORKDIR /opt
COPY --from=builder /opt .

# run test again 
RUN set -ex ; \
  cd /opt/hexlite-owlapi-plugin/examples/koala/ ; \
  CLASSPATH=${HEXLITE_JAVA_PLUGIN_API_JAR_WITH_PATH}:${HEXLITE_OWLAPI_PLUGIN_JAR_WITH_PATH} \
  hexlite --pluginpath /opt/hexlite/plugins/ \
    --plugin javaapiplugin at.ac.tuwien.kr.hexlite.OWLAPIPlugin \
    --number 33 --stats --flpcheck=none querykoala1.hex

#
# until here we mostly built hexlite and the owlapi plugin (and tested it)
# (we also install grpc requirements)
#
# now add the gRPC component
#

# copy sources
RUN mkdir /app /app/ai4industry /app/ai4industry/hexcaller /app/ai4industry/hexplugins/
COPY config.json planning.proto /app/
COPY src/ai4industry/* /app/ai4industry/
COPY src/ai4industry/hexcaller/* /app/ai4industry/hexcaller/
COPY ontology/* /app/
COPY encodings/including_skillmatching.hex /app/encoding.hex
COPY hexplugins/*.py /app/ai4industry/hexplugins/
COPY log4j2.xml /app/

ENV PYTHONPATH /app/:$PYTHONPATH

# adhere to container specification by also providing these two files
COPY planning.proto /model.proto
COPY license.json /license.json

WORKDIR /app

# compile protobuf
RUN python3 -m grpc_tools.protoc --python_out=/app/ai4industry/ --grpc_python_out=/app/ai4industry/ --proto_path=. *.proto

EXPOSE 8061

# run server
CMD python3 -m ai4industry.app
