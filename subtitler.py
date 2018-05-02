from aip import AipSpeech
from ffmpy import *

import json
from vad import *

FRAME_DURATION = 10  # ms
SAMPLE_RATE = 16000  # sample rate
AUTHENTICATION_FILE = 'subtitler_apikey.json'
aip_client = None
LOGGER = True


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


def get_language_id(lang):
    '''
    Get language id for AipSpeech
    :param lang: language id in prompt
    :return: language id
    '''
    return dict(zip([chr(x) for x in range(ord('0'), ord('6'))]
                    , ['1536', '1537', '1737', '1637', '1837', '1936'])).get(lang, '1737')


def raise_error(msg):
    print(msg)
    exit(-1)


def set_up_aip():
    '''
    Config AipSpeech; read authentication information in local json file.
    You can config the file name in `AUTHENTICATION_FILE`
    :return: None
    '''
    try:
        app_auth_info = json.load(open(AUTHENTICATION_FILE, 'r'))
        global aip_client
        aip_client = AipSpeech(app_auth_info['app_id'],
                               app_auth_info['api_key'], app_auth_info['secret_key'])
    except IndexError:
        raise_error('Malformat File: aip authentication file')
    except FileNotFoundError:
        raise_error('authentication file not found')


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
def process_segmentation(lang):
    vad = VoiceActivityDetector("audio.wav")
    frames = vad.get_voice_chunks(30, 300)
    dev_id = get_language_id(lang)
    print(dev_id)
    with contextlib.closing(open(srt_filename, 'w')) as fp:
        cnt = 0
        tot = len(frames)
        for frame in frames:
            cnt += 1
            print('Processing: {} of {}'.format(cnt, tot))
            result = aip_client.asr(frame.bytes, 'pcm', 16000, {
                'dev_pid': dev_id,
            })
            if result['err_no'] == 0:
                fp.write(to_srt_time(frame.timestamp) + '--->' + to_srt_time(frame.timestamp + frame.duration) + '\n')
                fp.write(result['result'][0] + '\n')
            else:
                print('Error occured while processing: {} to {}'.format(
                    to_srt_time(frame.timestamp), to_srt_time(frame.timestamp + frame.duration)))
                print('Errono: code {}\n message: {}'.format(result['err_no'], result['err_msg']))


if __name__ == '__main__':
    print('Setting up BaiduAip ...')
    set_up_aip()
    lang_prompt = '''
        0: English (without punctuation | custom corpus supported)
        1: Mandarin (Input method model)
        2: English (with punctuation | custom corpus isn't supported)
        3: Cantonese
        4: Sichuanese
        5: Mandarin (long distance speech)
    '''
    file_name = input('Enter video file: ')
    language = input('Input video language: ' + lang_prompt)
    srt_filename = input('Save subtitle to: ')
    srt_filename += '.srt'
    extract_audio(file_name)
    process_segmentation(language)
    print('Finished')
