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

import matplotlib.pyplot as plt
import subset_generators as sg

# Parse arguments
parser = argparse.ArgumentParser()

parser.add_argument('-dr', '--do-random', action='store_true',
                    help='Run the random subset test')

parser.add_argument('-ds', '--do-sequential', action='store_true',
                    help='Run the sequential subset test')

parser.add_argument('-uc', '--until-close', action='store_true',
                    help='If this flag is used, the random subset generator will pull samples '+
                         'until the value is to within the error factor of the true value.')

parser.add_argument('--error-factor', default=0.2, type=float,
                    help='The target error factor in dB')

parser.add_argument('-rr', '--repeat-random', default=50, type=int,
                    help='The number of times to repeat the random subset generator test.')

parser.add_argument('-d', '--dur', default=2.0, type=float,
                    help='The total amount of the file to subsample, in seconds.')

parser.add_argument('-sh', '--skip-hash', action='store_true', 
                    help='If present, skip the hash check on the mp3s')

parser.add_argument('-sf', '--save-figs', action='store_true',
                    help='If used, figures will be saved.')

parser.add_argument('-shf', '--show-figs', action='store_true',
                    help='If used, figures will be displayed.')

parser.add_argument('-pd', '--plot-decimation', default=1,
                    help='For large arrays, it may be preferable to decimate the arrays to save memory.')

parser.add_argument('-mis', '--min-samples', default=100, type=int,
                    help='Minimum number of samples to collect in until-close mode.')
parser.add_argument('-ms', '--max-samples', default=10000000, type=int,
                    help='Maximum number of samples before you give up.')

args = parser.parse_args()

# Constants
media_loc = 'media'
mp3_loc = os.path.join(media_loc, 'mp3')
wav_loc = os.path.join(media_loc, 'wav')

sequential_fig_outputs = 'outputs/sequential'

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
                print(sha256_hash.hexdigest())
                warnings.warn("File " + demo_file['name'] + '.' + demo_file['type'] + 
                              ' has non-matching checksum, skipping.', RuntimeWarning)
                continue

    f_locations.append(mp3_target_location)
    f_types.append(demo_file['type'])


def update_running_sum(samp, running_sum_sq, n_samps):
    """
    Update the running sum and return the RMS.
    """
    running_sum_sq += samp**2
    rms = sqrt(running_sum_sq / n_samps)

    return (running_sum_sq, rms)

calc_dbfs = lambda rms, segment: (20 * log(rms / segment.max_possible_amplitude, 10)) if rms > 0 else -float('infinity')
files_processed = []

# Start calculating RMS values.
for floc, ftype in zip(f_locations, f_types):
    cname = os.path.split(floc)[1][:-4]

    seg = None
    gc.collect()        # These files can be large in memory - clean up explicitly.
    
    seg = AudioSegment.from_file(floc, ftype)
    total_samps = len(seg._data) // seg.sample_width

    true_dbfs = seg.dBFS
    
    print('{}\nTrue dBFS: {:f}'.format(cname+'.mp3', true_dbfs))

    #
    # Random subset
    #
    if args.do_random:
        rand_dbfses = []
        rand_dbfses_final = []
        n_samp_vals = []
        samprange = total_samps if args.until_close else np.ceil(args.dur * seg.frame_rate)
        if samprange > args.max_samples:
            samprange = args.max_samples
        
        for ii in xrange(args.repeat_random):
            rsub = sg.RandomSubsetGenerator(total_samps, n=samprange)

            samps = []
            rand_dbfs = []
            running_sum_sq = 0
            n_samps = 0

            for ind in rsub:
                n_samps += 1
                samp = getsample(seg._data, seg.sample_width, ind)

                samps.append(samp)

                # Calculate RMS
                running_sum_sq, rms = update_running_sum(samp, running_sum_sq, n_samps)
                dbfs = calc_dbfs(rms, seg)

                rand_dbfses.append(dbfs)

                if args.until_close and n_samps > args.min_samples and \
                   abs(dbfs - true_dbfs) < args.error_factor:
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

    #
    # Start from beginning, end and middle
    #
    if args.do_sequential:
        running_sum_sq_s = 0
        running_sum_sq_m = 0
        running_sum_sq_e = 0

        middle_ind = total_samps//2

        n_samps_s = 0
        n_samps_m = 0
        n_samps_e = 0

        s_done = False
        m_done = False
        e_done = False

        keep_arrays = args.show_figs or args.save_figs
        dbfses_s = []
        dbfses_m = []
        dbfses_e = []

        samprange = total_samps if args.until_close else int(np.ceil(args.dur * seg.frame_rate))

        if samprange > args.max_samples:
            samprange = args.max_samples

        for ii in xrange(samprange):
            if not s_done:
                samp = getsample(seg._data, seg.sample_width, ii)
                n_samps_s += 1

                running_sum_sq_s, rms_s = update_running_sum(samp, running_sum_sq_s, n_samps_s)
                dbfs_s = calc_dbfs(rms_s, seg)

                if keep_arrays and (ii % self.plot_decimation == 0):
                    dbfses_s.append(dbfs_s)

                if args.until_close and abs(dbfs_s - true_dbfs) < args.error_factor:
                    s_done = True
            
            if not m_done:
                samp = getsample(seg._data, seg.sample_width, (ii+middle_ind)%total_samps)
                n_samps_m += 1

                running_sum_sq_m, rms_m = update_running_sum(samp, running_sum_sq_m, n_samps_m)
                dbfs_m = calc_dbfs(rms_m, seg)

                if keep_arrays and (ii % self.plot_decimation == 0):
                    dbfses_m.append(dbfs_m)

                if args.until_close and abs(dbfs_m - true_dbfs) < args.error_factor:
                    m_done = True

            if not e_done:
                samp = getsample(seg._data, seg.sample_width, total_samps-(ii+1))
                n_samps_e += 1

                running_sum_sq_e, rms_e = update_running_sum(samp, running_sum_sq_e, n_samps_e)
                dbfs_e = calc_dbfs(rms_e, seg)

                if keep_arrays and (ii % self.plot_decimation == 0):
                    dbfses_e.append(dbfs_e)

                if args.until_close and abs(dbfs_e - true_dbfs) < args.error_factor:
                    e_done = True

            if s_done and m_done and e_done:
                break

        print(('Start number of samples: {start_ns:d} ({start_db:f} dB)\n' +
              'Middle number of samples: {middle_ns:d} ({middle_db:f} dB)\n' +
              'End number of samples: {end_ns:d} ({end_db:f} dB)\n')
              .format(start_ns=n_samps_s,
                      start_db=dbfs_s,
                      middle_ns=n_samps_m,
                      middle_db=dbfs_m,
                      end_ns=n_samps_e,
                      end_db=dbfs_e))

        if args.show_figs or args.save_figs:
            fig = plt.figure(figsize=(8, 3))
            
            phs, = plt.plot(range(n_samps_s), dbfses_s, '-b')
            phm, = plt.plot(range(n_samps_m), dbfses_m, '-r')
            phe, = plt.plot(range(n_samps_e), dbfses_e, '-g')

            pht, = plt.plot([0, np.max([n_samps_s, n_samps_m, n_samps_e])], [true_dbfs, true_dbfs],
                            '--k')

            plt.xlim(0, np.max([n_samps_s, n_samps_m, n_samps_e]))

            plt.legend([pht, phs, phm, phe], ['True dbFS', 'Start', 'Middle', 'End'], loc='best', fontsize=9)

            fig.canvas.set_window_title('Sequential Subset: '+cname)

            plt.title('Sequential Subset: ' + cname, fontsize=10)

            plt.xlabel('Samples', fontsize=9)
            plt.ylabel('Loudness (dB)', fontsize=9)

            plt.tick_params(axis='both', labelsize=7)

            plt.tight_layout()

            if args.save_figs:
                if not os.path.exists(sequential_fig_outputs):
                    os.makedirs(sequential_fig_outputs)

                if args.until_close:
                    cfname = cname + ' (Until Close).png'
                else:
                    cfname = cname + ' ({:08d samples}).png'.format(n_samps_s)

                plt.savefig(os.path.join(sequential_fig_outputs, cfname), format='png',
                            transparent=True, dpi=300)

            if not args.show_figs:
                fig.close()
