#!/bin/bash
# tests whether debocker can build itself

set -eux

cd ..
debocker build
