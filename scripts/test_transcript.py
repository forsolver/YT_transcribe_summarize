import sys
from youtube_transcript_api import YouTubeTranscriptApi, _errors

vids = sys.argv[1:]
if not vids:
    print('Usage: python test_transcript.py <video_id> [<video_id> ...]')
    sys.exit(1)

for vid in vids:
    print('='*40)
    print('Video:', vid)
    try:
        tr = None
        try:
            tr = YouTubeTranscriptApi.get_transcript(vid, languages=['en'])
        except Exception as e:
            print('en err:', e)
        if not tr:
            try:
                tr = YouTubeTranscriptApi.get_transcript(vid, languages=['ru'])
            except Exception as e:
                print('ru err:', e)
        if not tr:
            try:
                list_tr = YouTubeTranscriptApi.list_transcripts(vid)
                print('available:', [f"{t.language_code}{' (gen)' if t.is_generated else ''}{' [T]' if t.is_translatable else ''}" for t in list_tr])
                for item in list_tr:
                    try:
                        tr = item.fetch()
                        if tr:
                            print('fetched', item.language_code, 'lines', len(tr))
                            break
                    except Exception as e_fetch:
                        print('fetch err', item.language_code, e_fetch)
                    if item.is_translatable:
                        try:
                            tr = item.translate('en').fetch()
                            if tr:
                                print('translated', item.language_code, '-> en lines', len(tr))
                                break
                        except Exception as e_trans:
                            print('translate err', item.language_code, e_trans)
            except Exception as e:
                print('list err:', e)
        if tr:
            print('Fetched lines:', len(tr))
            print('First snippet:', tr[0])
        else:
            print('Could not fetch transcript')
    except Exception as e:
        print('Error', e) 