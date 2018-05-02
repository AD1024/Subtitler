from ffmpy import *

import json
from xfyun import Speech
from vad import *

FRAME_DURATION = 30  # ms
FRAME_SHIFT = 300  # ms
SAMPLE_RATE = 16000  # sample rate
AUTHENTICATION_FILE = 'subtitler_apikey.json'
aip_client = None
LOGGER = True
DEV_MODE = True


def log(msg=''):
    '''
    logger
    :param msg: message
    :return: decorated method
    '''

    def decorate(func):
        @functools.wraps(func)
        def wrapper(*args, **kargs):
            if LOGGER and msg:
                print(msg)
            return func(*args, **kargs)

        return wrapper

    return decorate


def raise_error(msg):
    print(msg)
    exit(-1)


@log('Extracting audio')
def extract_audio(file):
    '''
    Extract audio from the input video and write into `audio.wav`
    :param file: file name(with suffix)
    :return: None
    '''
    ffmpeg_instance = FFmpeg(
        inputs={file: None},
        outputs={'audio.wav': '-ar 16000 -ac 1 -y'},
    )
    try:
        ffmpeg_instance.run()
    except FFRuntimeError:
        raise_error('Error while processing {}'.format(file))


def to_srt_time(sec):
    convert = lambda x: x if len(x) == 2 else '0' + x
    hr = sec // 3600
    minu = (int(sec) % 3600) // 60
    mu = int(round(sec - int(sec), 3) * 1000)
    se = int(sec) % 60
    return '{}:{}:{}.{}'.format(convert(str(int(hr))), convert(str(int(minu))), se, mu)


@log('Processing speech segments & writting into srt file')
def process_segmentation():
    vad = VoiceActivityDetector("audio.wav")
    frames = vad.get_voice_chunks(FRAME_DURATION, FRAME_SHIFT, save_files=True if DEV_MODE else False)
    client = Speech()
    with contextlib.closing(open(srt_filename, 'w')) as fp:
        cnt = 0
        tot = len(frames)
        for frame in frames:
            cnt += 1
            print('Processing: {} of {}'.format(cnt, tot))
            result = json.loads(client.asr(frame.bytes))
            result['data'] = result['data'].encode('ISO-8859-1').decode()
            if result['code'] == "0":
                if len(result['data']) > 0:
                    fp.write('{}\n'.format(cnt))
                    fp.write(to_srt_time(frame.timestamp) + '-->'
                             + to_srt_time(frame.timestamp + frame.duration) + '\n')
                    fp.write(result['data'] + '\n\n')
            else:
                print('Error occured while processing: {} to {}'.format(
                    to_srt_time(frame.timestamp), to_srt_time(frame.timestamp + frame.duration)))
                print('Errono: code {}\n message: {}'.format(result['code'], result['desc']))


if __name__ == '__main__':
    file_name = input('Enter video file: ')
    srt_filename = input('Save subtitle to: ')
    srt_filename += '.srt'
    if DEV_MODE:
        FRAME_DURATION = int(input('Duration per frame(ms): '))
        FRAME_SHIFT = int(input('Offset between frames(ms): '))
    extract_audio(file_name)
    process_segmentation()
    print('Finished')
