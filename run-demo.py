"""
File normalization demo


Read in some specified files and determine the proper normalization for the entire file, then
compare to various subsets of the entire file.

Note: I'm accessing the private _data array from pydub.AudioSegment, so that could be subject
to change.
"""

from __future__ import division

import json
import os
import gc
import urllib
import hashlib
import argparse
import warnings

from pydub import AudioSegment
from pydub.pyaudioop import getsample

from math import log, sqrt
import numpy as np

import subset_generators as sg

# Parse arguments
parser = argparse.ArgumentParser()

parser.add_argument('-uc', '--until-close', action='store_true',
                    help='If this flag is used, the random subset generator will pull samples '+
                         'until the value is to within the error factor of the true value.')

parser.add_argument('--error-factor', default=0.2, type=float,
                    help='The target error factor in dB')

parser.add_argument('-r', '--repeat-random', default=50, type=int,
                    help='The number of times to repeat the random subset generator test.')

parser.add_argument('-rd', '--rand-dur', default=2.0, type=float,
                    help='The total amount of the file to randomly subsample, seconds.')

parser.add_argument('-sh', '--skip-hash', action='store_true', 
                    help='If present, skip the hash check on the mp3s')

args = parser.parse_args()

# Constants
media_loc = 'media'
mp3_loc = os.path.join(media_loc, 'mp3')
wav_loc = os.path.join(media_loc, 'wav')

# Make sure that we have all the files for the demo.
with open('demo-file-info.json', 'r') as jsonfile:
    finfo = json.load(jsonfile)

f_list = finfo['file_list']
f_locations = []
f_types = []
for demo_file in f_list:
    # Download each file as an mp3. We'll convert to a wav in a second step, in case anything
    # goes wrong in the conversion we'll already have the mp3s ready to go.
    mp3_target_location = os.path.join(mp3_loc, demo_file['name'] + '.' + demo_file['type'])
    
    if not os.path.exists(mp3_target_location):
        if not os.path.exists(mp3_loc):
            os.makedirs(mp3_loc)

        urllib.urlretrieve(demo_file['url'], mp3_target_location)

    
    # Calculate the sha256 checksum
    if not args.skip_hash:
        with open(mp3_target_location, 'rb') as mdfile:
            sha256_hash = hashlib.sha256()
            sha256_hash.update(mdfile.read())

            if sha256_hash.hexdigest() != demo_file['checksum']:
                warnings.warn("File " + demo_file['name'] + '.' + demo_file['type'] + 
                              ' has non-matching checksum, skipping.', RuntimeWarning)
                continue

    f_locations.append(mp3_target_location)
    f_types.append(demo_file['type'])


calc_dbfs = lambda rms, segment: (20 * log(rms / segment.max_possible_amplitude, 10)) if rms > 0 else -float('infinity')
files_processed = []

# Start calculating RMS values.
for floc, ftype in zip(f_locations, f_types):
    cname = os.path.split(floc)[1]

    seg = None
    gc.collect()        # These files can be large in memory - clean up explicitly.
    
    seg = AudioSegment.from_file(floc, ftype)
    total_samps = len(seg._data) // seg.sample_width

    true_dbfs = seg.dBFS
    
    print('{}\nTrue dBFS: {:f}'.format(cname, true_dbfs))

    # Random subset
    rand_dbfses = []
    rand_dbfses_final = []
    n_samp_vals = []
    
    for ii in xrange(args.repeat_random):
        if args.until_close:
            # Select a random subset of the segment and start calculating the RMS.
            # Stop when it reaches the designated error factor
            rsub = sg.RandomSubsetGenerator(total_samps)
        else:
            rsub = sg.RandomSubsetGenerator(total_samps, n=np.ceil(args.rand_dur * seg.frame_rate))

        samps = []
        rand_dbfs = []
        running_sum_sq = 0
        n_samps = 0

        for ind in rsub:
            n_samps += 1
            samp = getsample(seg._data, seg.sample_width, ind)

            samps.append(samp)

            # Calculate RMS
            running_sum_sq += samp ** 2
            rms = sqrt(running_sum_sq / n_samps)
            dbfs = calc_dbfs(rms, seg)

            rand_dbfses.append(dbfs)

            if args.until_close and abs(dbfs - true_dbfs) < args.error_factor:
                break

        n_samp_vals.append(n_samps)
        rand_dbfses.append(rand_dbfs)
        rand_dbfses_final.append(dbfs)

    if args.until_close:
        mean_n_samps = np.mean(n_samp_vals)
        samps2ms = 1000 / seg.frame_rate
        print(('Final dBFS: {:f}\n'+ 
              'Mean number of samples: {mean_n:f} ({mean_ns:f} ms)\n' + 
              'Min number of samples: {min_n:f} ({min_ns:f} ms)\n' +
              'Max number of samples: {max_n:f} ({max_ns:f} ms)\n')
              .format(dbfs,
                      mean_n=mean_n_samps,
                      mean_ns=mean_n_samps * samps2ms,
                      min_n=np.min(n_samp_vals),
                      min_ns=np.min(n_samp_vals) * samps2ms,
                      max_n=np.max(n_samp_vals),
                      max_ns=np.max(n_samp_vals) * samps2ms))
    else:
        mean_db = np.mean(rand_dbfses_final)
        max_db = np.max(rand_dbfses_final)
        min_db = np.min(rand_dbfses_final)

        print(('Mean dBFS: {mean:f} (Error: {meane:f})\n' +
               'Min dBFS: {min:f} (Error: {mine:f})\n' + 
               'Max dBFS: {max:f} (Error: {maxe:f})\n' + 
               'Standard Deviation:  {std:f}\n').format(mean=mean_db,
                                                        meane=abs(true_dbfs-mean_db),
                                                        min=min_db,
                                                        mine=abs(true_dbfs-min_db),
                                                        max=max_db,
                                                        maxe=abs(true_dbfs-max_db),
                                                        std=np.std(rand_dbfses_final)))



    cfile = {
              'name': cname,
              'true_dbfs': true_dbfs,
              'rand_dbfses': rand_dbfses,
              'rand_samps': samps,
              'n_samps': n_samp_vals
            }

    files_processed.append(cfile)
