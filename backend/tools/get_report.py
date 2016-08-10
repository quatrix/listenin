from __future__ import print_function, division
import datetime
import calendar
import click
import json
from collections import defaultdict
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from dateutil import tz

client = Elasticsearch(['http://listenin.io:9200'], timeout=20)


class NoData(Exception):
    pass


def mean(lst):
    return sum(lst) / len(lst)


def gen_date_matrix(start_hour, hours, days=7, days_back_offset=0):
    start_day = datetime.datetime.now()
    start_day -= datetime.timedelta(days=days+days_back_offset)
    start_day = start_day.replace(hour=start_hour, minute=0, second=0, microsecond=0)

    matrix = []

    for days_offset in xrange(days):
        start = start_day + datetime.timedelta(days=days_offset)
        m = {
            'start': start,
            'offsets': [],
        }

        for hours_offset in hours:
            end = start + datetime.timedelta(hours=hours_offset)
            m['offsets'].append({'start': start, 'end': end})
            m['end'] = end
            start = end
        
        matrix.append(m)

    return matrix


def create_matches_in_range_query(*qs, **kwargs):
    range_query = Q('range', **{
        '@timestamp': {
            'gte': kwargs['start'],
            'lte': kwargs['end'],
            'time_zone': 'Israel',
        }
    })

    must = [Q('match', **q) for q in qs]
    must.append(range_query)

    return Search(using=client).query(Q('bool', must=must))


def get_uploads_percent(venue, start, end, upload_interval):
    # returns upload percent
    r = get_venue_uploads(venue, start, end).execute()

    expected_uploads = (end-start).total_seconds() / upload_interval
    uploads = int(r.hits.total / expected_uploads * 100)

    return uploads


def get_venue_uploads(venue, start, end):
    return create_matches_in_range_query(
        {'boxid': {'query': venue, 'type': 'phrase'}},
        {'message': 'success'},
        {'uri': '/upload/'},
        start=start,
        end=end,
    )

def get_recognized_songs_count(venue, start, end):
    rq = Q('bool', minimum_should_match=1, should=[Q('exists', field='gracenote'), Q('exists', field='acrcloud')])

    uploads_recognized = get_venue_uploads(venue, start, end).query(rq)

    d = uploads_recognized.to_dict()
    d['query']['bool']['minimum_should_match'] = 1
    return uploads_recognized.update_from_dict(d).execute().hits.total


def get_terms(venue, start, end, term, min_doc_count=2):
    s = get_venue_uploads(venue, start, end)
    s.aggs.bucket('groupby', 'terms', field=term, min_doc_count=min_doc_count)
    return s.execute().aggregations.groupby.buckets


def get_top_moods(venue, start, end, top_n=2):
    # returns top n moods
    terms = get_terms(venue, start, end, 'gracenote.mood.1.TEXT.raw')
    return [term.key for term in terms[:top_n]]


def utc_to_localtime(d, local_tz):
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz(local_tz)

    utc = datetime.datetime.strptime(d, '%Y-%m-%dT%H:%M:%S.%fZ')
    utc = utc.replace(tzinfo=from_zone)
    return utc.astimezone(to_zone)




def get_last_upload_hour(venue, start, end):
    s = get_venue_uploads(venue, start, end).sort('-@timestamp')[0].execute()

    if s:
        return utc_to_localtime(s[0]['@timestamp'], local_tz='Israel').strftime('%H:%M')


def get_top_with_ranges(venue, ranges, field):
    ranges_query = [Q('range', **{
        '@timestamp': {
            'gte': r['start'],
            'lte': r['end'],
            'time_zone': 'Israel',
        }
    }) for r in ranges]

    qs = [
        {'message': 'success'},
        {'uri': '/upload/'},
    ]

    if venue is not None:
        qs.append({'boxid': {'query': venue, 'type': 'phrase'}})
    
    must = [Q('match', **q) for q in qs]

    s = Search(using=client).query(Q('bool', must=must, minimum_should_match=1, should=ranges_query))
    s.aggs.bucket('groupby', 'terms', min_doc_count=2, field=field)
    return s.execute().aggregations.groupby.buckets


def get_top_albums(venue, ranges):
    albums = get_top_with_ranges(venue, ranges, 'gracenote.album_gnid.raw')

    res = []

    for album in albums:
        if not album.key:
            continue

        q = {'gracenote.album_gnid.raw': album.key}

        gracenote = Search(using=client).query('match', **q)[0].execute()[0]['gracenote']

        res.append({
            'album': gracenote['album_title'],
            'artist': gracenote['album_artist_name'],
            'count': album.doc_count,
        })

    return res

def get_top_tracks(venue, ranges):
    # returns top tracks
    tracks = get_top_with_ranges(venue, ranges, 'gracenote.track_gnid.raw')   

    res = []

    for track in tracks:
        if not track.key:
            continue

        q = {'gracenote.track_gnid.raw': track.key}

        gracenote = Search(using=client).query('match', **q)[0].execute()[0]['gracenote']

        res.append({
            'title': gracenote['track_title'],
            'album': gracenote['album_title'],
            'artist': gracenote['album_artist_name'],
            'count': track.doc_count,
        })

    return res

def get_top_generes(venue, start, end, top_n=4):
    # returns top n generes

    terms = get_terms(venue, start, end, 'gracenote.genre.2.TEXT.raw', min_doc_count=1)
    uploads_recognized = get_recognized_songs_count(venue, start, end)

    if uploads_recognized == 0:
        return []

    return [{
        'name': term['key'],
        'freq': int(term['doc_count'] / uploads_recognized * 100),
        'total': term['doc_count']
    } for term in terms[:top_n]]


def get_general_upload_stats(venue, start, end, upload_interval):
    upload_percent = get_uploads_percent(
        venue,
        start=start,
        end=end,
        upload_interval=upload_interval
    )

    uploads_total = get_venue_uploads(venue, start, end).execute().hits.total

    if uploads_total == 0:
        raise NoData

    uploads_recognized = get_recognized_songs_count(venue, start, end)

    if upload_percent > 80:
        status = 'ok'
    elif upload_percent > 30:
        status = 'warn'
    else:
        status = 'crit'

    return {
        'percent': upload_percent,
        'total': uploads_total,
        'recognized': int(uploads_recognized / uploads_total * 100),
        'status': status,
    }

def get_bpm(venue, start, end):
    # returns min/max/avg bpm
    bpm = get_venue_uploads(venue, start, end).query('exists', field='gracenote')[:999].execute()

    bpms = []

    for b in bpm:
        try:
            bpms.append(int(b['gracenote']['tempo']['3']['TEXT'].replace('s','')))
        except KeyError:
            pass

    if not bpms:
        return {
            'mean': 0,
        }

    return {
       'mean': int(mean(bpms)),
    }


@click.command()
@click.option('--venue', help='venue name', default='radio')
@click.option('--upload-interval', help='upload interval', default=60 * 4)
@click.option('--blink-interval', help='blink interval', default=5)
@click.option('--days', help='for how many days to generate report', default=7)
@click.option('--start-hour', help='when place opens', default=21)
@click.option('--start-day', help='how many days back to start', default=0)
def main(venue, upload_interval, blink_interval, days, start_hour, start_day):
    matrix = gen_date_matrix(days_back_offset=start_day, start_hour=start_hour, hours=[2, 3, 3], days=days)
    mid_end = gen_date_matrix(days_back_offset=start_day, start_hour=23, hours=[6], days=days)

    report = {
        'venue': venue,
        'top_tracks': get_top_tracks(venue=venue, ranges=mid_end),
        'top_tracks_tlv': get_top_tracks(venue=None, ranges=mid_end),
        'days': [],
    }

    for m in matrix:
        day_name = '{} {}'.format(calendar.day_name[m['start'].weekday()], m['start'].strftime('%m/%d'))

        res = {
            'day': day_name,
            'parts': [],
            'bpm': get_bpm(venue, m['start'], m['end']),
        }

        try:
            res['upload_stats'] = get_general_upload_stats(venue, m['start'], m['end'], upload_interval)
        except NoData:
            report['days'].append(res)
            continue

        try:
            res['top_genre'] = get_top_generes(venue, m['start'], m['end'], top_n=1)[0]['name']
        except (KeyError, IndexError):
            pass

        for o in m['offsets']:
            try:
                res['parts'].append({
                    'name': '{}:00 - {}:00'.format(o['start'].hour, o['end'].hour),
                    'upload_stats': get_general_upload_stats(venue, o['start'], o['end'], upload_interval),
                    'genres': get_top_generes(venue, o['start'], o['end']),
                    'bpm': get_bpm(venue, o['start'], o['end']),
                })
            except NoData:
                pass

        report['days'].append(res)

    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()


