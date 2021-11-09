#!/bin/bash

if [[ `basename "$PWD"` != "MQClient-Pulsar" && $PWD != "/home/circleci/project" ]] ; then
	echo "ERROR: Run from 'MQClient-Pulsar/' (not '$PWD')"
	exit 1
fi

python examples/worker.py &
python examples/server.py