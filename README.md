lastfm_histogram
================

Creates a histogram of the release years of your last.fm albums!  I think it's cool.  It produces correct output but is slow.

Demo
----

http://dgilman.github.com/lastfm_histogram/

Usage
-----

*If you don't want to run this program email me at gil at gilslotd dot com and I'll create your chart for you*

1. Get a last.fm api key for free
2. Plug the api key and your username into fetch.py
3. Run and wait
4. The chart is put in charts/username.html

Todo
----
* Use a local MusicBrainz database to make things much faster
* Move the filesystem cache into a database
* Fetch charts and albums in parallel


Non-commercial redistribution
-----------------------------

The included highcharts software is not free for commercial use.  See http://shop.highsoft.com/highcharts.html