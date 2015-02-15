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