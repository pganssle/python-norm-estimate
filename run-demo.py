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
import warnings

from pydub import AudioSegment
from pydub.pyaudioop import getsample

from math import log, sqrt

import subset_generators as sg

# Constants
media_loc = 'media'
mp3_loc = os.path.join(media_loc, 'mp3')
wav_loc = os.path.join(media_loc, 'wav')

error_factor = 0.2         # Stop if we're within this factor of the true value (in dB)

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
    
    if not (os.path.exists(mp3_target_location)  or  os.path.exists(wav_target_location)):
        if not os.path.exists(mp3_loc):
            os.makedirs(mp3_loc)
        
        urllib.urlretrieve(demo_file['url'], mp3_target_location)

    
    # Calculate the sha256 checksum
    with open(mp3_target_location, 'rb') as mdfile:
        sha256_hash = hashlib.sha256()
        sha256_hash.update(mdfile.read())

        if sha256_hash.hexdigest() != demo_file['checksum']:
            warnings.warn("File " + demo_file['name'] + '.' + demo_file['type'] + 
                          ' has non-matching checksum, skipping.', RuntimeWarning)
        else:
            f_locations.append(mp3_target_location)
            f_types.append(demo_file['type'])

files_processed = []

# Start calculating RMS values.
for floc, ftype in zip(f_locations, f_types):
    seg = None
    gc.collect()        # These files can be large in memory - clean up explicitly.
    seg = AudioSegment.from_file(floc, ftype)

    cname = os.path.split(floc)[1]

    true_dbfs = seg.dBFS

    print('{}\nTrue dBFS: {:f}'.format(cname, true_dbfs))

    # Select a random subset of the segment and start calculating the RMS.
    # Stop when it reaches the designated error factor
    rsub = sg.RandomSubsetGenerator(len(seg._data) // seg.sample_width)
    samps = []
    rand_dbfses = []
    running_sum_sq = 0
    n_samps = 0

    for ind in rsub:
        n_samps += 1
        samp = getsample(seg._data, seg.sample_width, ind)

        samps.append(samp)

        # Calculate RMS
        running_sum_sq += samp ** 2
        rms = sqrt(running_sum_sq / n_samps)
        dbfs = 20 * log(rms / seg.max_possible_amplitude, 10)

        rand_dbfses.append(dbfs)

        if abs(dbfs - true_dbfs) < error_factor or n_samps > 10000:
            break

    print('Final dBFS: {:f}\nNumber of samples: {:d}'.format(dbfs, n_samps))
    cfile = {
              'name': cname,
              'true_dbfs': true_dbfs,
              'rand_dbfses': rand_dbfses,
              'rand_samps': samps
            }

    files_processed.append(cfile)
