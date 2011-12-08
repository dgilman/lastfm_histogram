
from __future__ import division
import datetime
import time
from lxml import etree
import urllib2
import sqlite3
import sys
import json
import os

one_second = datetime.timedelta(seconds=1)

apikey = "FIX ME"
username = "lordgilman"

baseurl = "http://ws.audioscrobbler.com/2.0/?api_key=%s&user=%s" % (apikey, username)

def getpage(url):
   return urllib2.urlopen(urllib2.Request(url, headers={"User-Agent":"last.fm-histogrammer"})).readlines()

chart_periods_xml = getpage(baseurl + "&method=user.getWeeklyChartList")
chart_periods = []
t = etree.fromstringlist(chart_periods_xml)
for chart in t.xpath("//chart"):
   chart_periods.append((chart.attrib["from"], chart.attrib["to"]))

start_time = datetime.datetime.now()
end_time = datetime.datetime.now()
album_track_plays = {}
print "%s Starting chart fetching" % str(datetime.datetime.now())
for chart in chart_periods:
   cache_file = "chartcache/%s_%s_%s" % (username, chart[0], chart[1])
   end_time = datetime.datetime.now()
   td = end_time - start_time
   td_secs = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
   if abs(end_time - start_time) < one_second:
      time.sleep(1 - td_secs)
   if os.path.exists(cache_file):
      #cache hit
      weekly_album_xml = open(cache_file).readlines()
   else:
      start_time = datetime.datetime.now()
      weekly_album_xml = getpage(baseurl + "&method=user.getWeeklyAlbumChart&from=%s&to=%s" % (chart[0], chart[1]))
      with open(cache_file, "w") as fd:
         fd.writelines(weekly_album_xml)
   t = etree.fromstringlist(weekly_album_xml)
   for album in t.xpath("//album"):
      album_mbid = album.xpath("mbid")[0].text
      if album_mbid is None:
         continue
      if album_mbid in album_track_plays:
         album_track_plays[album_mbid] += int(album.xpath("playcount")[0].text)
      else:
         album_track_plays[album_mbid] = int(album.xpath("playcount")[0].text)

conn = sqlite3.connect("album_cache.sqlite")
c = conn.cursor()

xmlns = {'mb': 'http://musicbrainz.org/ns/mmd-2.0#'}

start_time = datetime.datetime.now()
end_time = datetime.datetime.now()
print "%s Starting album lookup" % str(datetime.datetime.now())
for album in album_track_plays.items():
   c.execute("select * from album_cache where mbid = ?", (album[0],))
   results = c.fetchall()
   if len(results) == 0:
      end_time = datetime.datetime.now()
      td = end_time - start_time
      td_secs = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
      if abs(end_time - start_time) < one_second:
         time.sleep(1 - td_secs)
      start_time = datetime.datetime.now()
      try:
         album_info = getpage("http://musicbrainz.org/ws/2/release/%s?inc=recordings" % album[0])
      except urllib2.HTTPError: # 404
         c.execute("insert into album_cache (mbid, year, tracks) values (?, ?, ?);", (album[0], 0, 0))
         continue
      t  = etree.fromstringlist(album_info)
      release_date_e = t.xpath("//mb:release/mb:date", namespaces=xmlns)
      if len(release_date_e) > 0:
         release_year = int(release_date_e[0].text[0:4])
      else:
         release_year = 0
      tracks_e = t.xpath("//mb:medium-list/mb:medium[1]/mb:track-list", namespaces=xmlns)
      if len(tracks_e) > 0:
         tracks = int(tracks_e[0].attrib["count"])
      else:
         tracks = 0
      c.execute("insert into album_cache (mbid, year, tracks) values (?, ?, ?);", (album[0], release_year, tracks))
      conn.commit()
   else:
      continue

# check f9daf032-948a-389a-b6a7-69284e0dd2d6

unweighted_year = {}
weighted_year = {}

# album_track_plays[mbid]; # of plays
# album_cache[mbid]: year, # of tracks
print "%s Starting unweighted population" % str(datetime.datetime.now())
#unweighted
for album in album_track_plays.iteritems():
   c.execute("select year, tracks from album_cache where mbid = ?", (album[0],))
   year, tracks = c.fetchall()[0]
   if year == 0 or tracks == 0:
      continue
   if year in unweighted_year:
      unweighted_year[year] += 1
   else:
      unweighted_year[year] = 1

print "%s Starting weighted population" % str(datetime.datetime.now())
#weighted
for album in album_track_plays.iteritems():
   c.execute("select year, tracks from album_cache where mbid = ?", (album[0],))
   year, tracks = c.fetchall()[0]
   if year == 0 or tracks == 0:
      continue
   if year in weighted_year:
      weighted_year[year] += (album_track_plays[album[0]] // tracks)
   else:
      weighted_year[year] = (album_track_plays[album[0]] // tracks)

print "%s Starting list creation" % str(datetime.datetime.now())
weighted_list = [(k,v) for k,v in weighted_year.iteritems() if v > 0]
unweighted_list = [(k,v) for k,v in unweighted_year.iteritems() if v > 0]

print "%s Creating string for writing and writing file" % str(datetime.datetime.now())
chart_page = """<html>
<head>
<title>%s's last.fm album histograms</title>
<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.6.1/jquery.min.js"     type="text/javascript"></script>
<script src="js/highcharts.js" type="text/javascript"></script>
<script type="text/javascript">
var unweighted = jQuery.parseJSON('%s');
var weighted = jQuery.parseJSON('%s');
sets = [weighted, unweighted];
for (var set = 0; set < sets.length; set++) {
   for (var i = 0; i < sets[set].length; i++) {
      sets[set][i][0] = Date.UTC(sets[set][i][0], 1, 1);
   }
}
function tooltipper() { return "<b>Year</b>: " + new Date(this.x).getFullYear() + "<br/><b># Albums</b>: " + this.y; };
var unweighted_options = {
    chart: {
        renderTo: 'unweighted_div',
        type: 'column',
    },
    title: {
        text: 'Unweighted album release histogram'
    },
    xAxis: {
       endOnTick: false,
       type: 'datetime',
       title: {
         text: 'Year'
        }
    },
    yAxis: {
       min: 0,
       endOnTick: false,
        title: {
            text: 'Albums'
        }
    },
    tooltip: {formatter: tooltipper},
    legend: {enabled: false},
    series: [{data: unweighted}]
};
var weighted_options = {
    chart: {
        renderTo: 'weighted_div',
        type: 'column',
    },
    title: {
        text: 'Weighted (by plays) album release histogram'
    },
    xAxis: {
       endOnTick: false,
       type: 'datetime',
       title: {
         text: 'Year'
        }
    },
    yAxis: {
       min: 0,
       endOnTick: false,
        title: {
            text: 'Albums'
        }
    },
    tooltip: {formatter: tooltipper},
    legend: {enabled: false},
    series: [{data: weighted}]
};
$(document).ready( function() {
    var weighted_chart = new Highcharts.Chart(weighted_options);
    var unweighted_chart = new Highcharts.Chart(unweighted_options);
});
</script>
</head>
<body>
<div id="unweighted_div"></div>
<div id="weighted_div"></div>
</body>
</html>""" % (username, json.dumps(unweighted_list), json.dumps(weighted_list))

with open('charts/%s.html' % username, "w") as fd:
   fd.write(chart_page)



conn.close()

