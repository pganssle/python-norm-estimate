Podcasts are often mastered at fairly different, and even inconsistent levels. This is fairly easy
to fix if you know the RMS level of each episode, but it can be resource-intensive and time
consuming to read an entire episode (which is often an hour or more of audio) just to calculate
the total RMS. The resource consumption problem is compounded by the fact that often podcasts are
loaded directly onto phones, which are generally low-power devices.

However, in most cases, mastering problems are consistent throughout a podcast episode - it's rare
that the audio levels vary dramatically within a given episode. As such, you only really need to
process as much of the episode as it takes to get close to the true RMS of the entire episode.
If you aren't concerned about intermittent clipping, this can be done using a very small subset of
the episode.

This repository explores how to optimally sample the episode so as to get as close as possible to
the true RMS in the smallest number of samples, using various different sampling techniques.

The demo uses the following podcasts, of various mastering qualities:
* [Serial, Season 1 Episode 7: *The Opposite of Prosecution*](http://serialpodcast.org/season-one/7/the-opposite-of-the-prosecution) (`serial-episode-07.mp3`, 32m 34s)
* [Seattle Library Podcast - October 28, 2014: *Polio Then and Now: From Salk’s Game-Changing Vaccine to Today’s Resurgence*](http://www.spl.org/Audio/14_10_28_Rob_Lin.mp3) (`seattle-library-podcast-2014-10-28.mp3`, 1h 17m 02s)
* [Spy Museum Podcast - Author Debriefing: *Good Hunting, An American Spymaster's Story*](http://www.spymuseum.org/multimedia/spycast/episode/author-debriefing-good-hunting-an-american-spymasters-story/) (`spy-museum-podcast-2014-11-07.mp3`, 1h 07m 42s)
* [Federalist Society Events Audio - *Defining Regulatory Crimes*](http://www.fed-soc.org/multimedia/detail/defining-regulatory-crimes-event-audiovideo) (`federalist-society-events-2014-06-11`, 1h 19m 06s)

Choosing random samples from these files totaling 2 seconds (~88,000 samples usually), and repeated
100 times gives the following results:

    >>> python run-demo.py -r 100 -rd 2.0 
    serial-episode-07.mp3
    True dBFS: -19.037004
    Mean dBFS: -19.050726 (Error: 0.013722)
    Min dBFS: -19.174793 (Error: 0.137789)
    Max dBFS: -18.945533 (Error: 0.091471)
    Standard Deviation:  0.051313

    seattle-library-podcast-2014-10-28.mp3
    True dBFS: -34.131281
    Mean dBFS: -34.129630 (Error: 0.001652)
    Min dBFS: -34.256691 (Error: 0.125409)
    Max dBFS: -33.766060 (Error: 0.365222)
    Standard Deviation:  0.074481

    spy-museum-podcast-2014-11-07.mp3
    True dBFS: -21.946289
    Mean dBFS: -21.945140 (Error: 0.001149)
    Min dBFS: -22.051429 (Error: 0.105140)
    Max dBFS: -21.811977 (Error: 0.134312)
    Standard Deviation:  0.048184

    federalist-society-events-2014-06-11.mp3
    True dBFS: -25.349533
    Mean dBFS: -25.354348 (Error: 0.004814)
    Min dBFS: -25.534129 (Error: 0.184596)
    Max dBFS: -25.091527 (Error: 0.258006)
    Standard Deviation:  0.085039

Using [mp3Gain](https://en.wikipedia.org/wiki/MP3Gain) on these same files and setting the target
"normal" volume to be the value at which Serial is mastered, mp3Gain recommends a volume boost of
15.1 dB, 3 dB and 6 dB, respectively - almost exactly what this script would recommend. As you can
see, the most naive method of random sampling, using only 0.04-0.1% of the total length of the file
to ascertain the overall volume level with enough accuracy to significantly improve the quality of
one's listening experience!