#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import math
import argparse
import itertools
import importlib

sys.path.insert(0, 'python-bloomfilter/')
import pybloom as pb

from topology import *
from packetstructs import *

#
## Common settings

# Number of generated packets (iterations)
packets = 100000

# Number of hops before entering the loop (list)
Brange = [5] # [0, 2, 3, 5, 7, 10]

# The length of the loop
Lrange = [20] # xrange(15, 25)

# Number of success loop detection before
# reporting it (called Th in the paper)
detections = [1] # [1, 2, 4]

# Generate loops and/or loop-free paths
#   When generating loop-free paths, the paths
#   has the length of X = B + X
genloops = False
genpaths = False

# Generate loops using a topology
topoloops = True

# Generate paths using a topology
topopaths = False

# Generate paths based on the loops length
lbasedpaths = True


# Topology parser and source file (stanford)
topoparser = 'stanford'
topofile = (
	"topologies/stanford-backbone/port_map.txt",
	"topologies/stanford-backbone/backbone_topology.tf")

# Topology parser and source file (zoo)
# topoparser = 'zoo'
# topofile = 'topologies/topology-zoo/UsCarrier.gml'
# topofile = 'topologies/topology-zoo/archive/Geant2012.gml'
# topofile = 'topologies/topology-zoo/archive/Bellsouth.gml'
# topofile = 'topologies/topology-zoo/AttMpls.gml'
# topofile = 'topologies/topology-zoo/archive/Cesnet201006.gml'
# topofile = 'topologies/topology-zoo/eu_nren_graphs/graphs/interconnect.gml'
# topofile = 'topologies/topology-zoo/eu_nren_graphs/graphs/condensed.gml'
# topofile = 'topologies/topology-zoo/eu_nren_graphs/graphs/condensed_west_europe.gml'

# Topology parser and source file (rocket)
# topoparser = 'rocket'
# topofile = 'topologies/rocketfuel/maps-n-paths/101\:101/edges'

# Topology parser and source file (fattree)
# topoparser = 'fattree'
# topofile = '4'
# topofile = '2'

# Enable Unroller and/or BF simulator and/or BF simulator prime dot
enunroller = True
enbloomfilter = False
enPrimeDot = False

#
## Unroller simulator settings

# b: how aggressively the resetting intervals are increased
brange = [4] # xrange(2, 5)

# (c, H) pairs, where
# c: number of chunks the phase is partitioned to
# H: number of hash functions
cHrange = [(1,1)] # [(1,1), (2,2), (4,4), (8,4), (8,8), (1,4), (4,1), (4,2), (2,4)]
# cHrange = itertools.product([1], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])

# z: stored number of bits of the switch identifier
zrange = [32] # xrange(2, 32+1) # xrange(2, 32+1)


#
## Bloomfilter simulator settings

# Expected capacity of the BF (# of hops)
bf_capacity = 7

# Expected error rates of the BF (affects number of hash functions)
bf_error_rates = [0.01, 0.001, 0.0001, 0.00001]


#
## Parse commandline arguments

parser = argparse.ArgumentParser()
parser.add_argument('-r', '--runs', type=int, default=None,
	help='number of runs')
parser.add_argument('config', metavar='CONFIG', type=str, nargs='?',
	help='configuration file')

args = parser.parse_args()


#
## Import external configuration if set

if args.config:
	dirname = os.path.dirname(args.config)
	basename = os.path.basename(args.config)
	modname = os.path.splitext(basename)[0]

	sys.path.insert(0, dirname)
	globals().update(importlib.import_module(modname).__dict__)


#
## Generate bf_error_rates if not set

if enbloomfilter:
	if not len(bf_error_rates):
		bf_num_bits_pairs = [(pb.BloomFilter(bf_capacity, p).num_bits, p) for p in [(z+1)/1000000. for z in xrange(999999)]]
		bf_error_rates = [w for (i,(q,w)) in enumerate(bf_num_bits_pairs) if q < bf_num_bits_pairs[i-1][0]]


#
## Override number of runs if set

if args.runs:
	packets = args.runs


#
## Create topology if necessary

if topoloops or topopaths:
	topo = Topology.load(topofile, parser=topoparser, create_hosts=True, allcycles=True, directed=False)

	BLs = []
	if topoloops:
		BLs = topo.generate_loops(packets, pathbased=True)

	Xs = []
	if topopaths:
		if lbasedpaths:
				Xs = [B+L for B, L in topo.generate_loops(packets)]
		else:
			Xs = topo.generate_paths(packets)


#
## Simulate Unroller structure

if enunroller:
	PacketMinSketch.print_header()
	for dets in detections:
		for b in brange:
			for c, H in cHrange:
				for z in zrange:
					if genloops or genpaths:
						for B in Brange:
							for L in Lrange:
								pstruct = PacketMinSketch(b = b, c = c, H = H, size = z, detections = dets)
								if genloops: simulate_loops(pstruct, (B,L), packets)
								if genpaths: simulate_paths(pstruct, B+L, packets)
								pstruct.csvrep()
							if len(Lrange) > 1: print
						if len(Brange) > 1: print
					if topoloops or topopaths:
						pstruct = PacketMinSketch(b = b, c = c, H = H, size = z, detections = dets)
						simulate_loops(pstruct, BLs)
						simulate_paths(pstruct, Xs)
						pstruct.csvrep()
				if len(zrange) > 1: print
			if len(cHrange) > 1: print
		if len(brange) > 1: print
	if len(detections) > 1: print
	print


#
## Simulate BloomFilter structure

if enbloomfilter:
	PacketBloomFilter.print_header()
	for dets in detections:
		for bf_error_rate in bf_error_rates:
			if genloops or genpaths:
				for B in Brange:
					for L in Lrange:
						pstruct = PacketBloomFilter(bf_capacity, bf_error_rate, detections = dets)
						if genloops: simulate_loops(pstruct, (B,L), packets)
						if genpaths: simulate_paths(pstruct, B+L, packets)
						pstruct.csvrep()
					if len(Lrange) > 1: print
				if len(Brange) > 1: print
			if topoloops or topopaths:
				pstruct = PacketBloomFilter(bf_capacity, bf_error_rate, detections = dets)
				simulate_loops(pstruct, BLs)
				simulate_paths(pstruct, Xs)
				pstruct.csvrep()
		if len(bf_error_rates) > 1: print
	if len(detections) > 1: print
	print

#
## Simulate BloomFilter structure

if enPrimeDot:
	PacketPrimeDot.print_header()
	for dets in detections:
		if genloops or genpaths:
			for B in Brange:
				for L in Lrange:
					pstruct = PacketPrimeDot(detections = dets)
					if genloops: simulate_loops(pstruct, (B,L), packets)
					if genpaths: simulate_paths(pstruct, B+L, packets)
					pstruct.csvrep()
				if len(Lrange) > 1: print
			if len(Brange) > 1: print
		if topoloops or topopaths:
			pstruct = PacketPrimeDot(detections = dets)
			simulate_loops(pstruct, BLs)
			simulate_paths(pstruct, Xs)
			pstruct.csvrep()
	print

## TODO set capacity according the generated loops
