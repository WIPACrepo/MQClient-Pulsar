#!/bin/bash

if [[ `basename "$PWD"` != "MQClient-Pulsar" && $PWD != "/home/circleci/project" ]] ; then
	echo "ERROR: Run from 'MQClient-Pulsar/' (not '$PWD')"
	exit 1
fi

export WIPACTEL_EXPORT_STDOUT=${WIPACTEL_EXPORT_STDOUT:="TRUE"}
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318/v1/traces"
export WIPACTEL_SERVICE_NAME_PREFIX=mqclient-pulsar

pip install tox
tox --notest -vv
. .tox/py/bin/activate

docker run -it \
    -p 6650:6650 \
    -p 8079:8079 \
    -v $PWD/data:/pulsar/data \
    apachepulsar/pulsar:latest \
    bin/pulsar standalone

`dirname "$0"`/run.sh