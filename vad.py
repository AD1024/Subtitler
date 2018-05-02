import webrtcvad
import contextlib
import wave
import functools


def read_wave(file):
    with contextlib.closing(wave.open(file, 'rb')) as wf:
        channels = wf.getnchannels()
        assert channels == 1
        sample_width = wf.getsampwidth()
        assert sample_width == 2
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000)
        audio = wf.readframes(wf.getnframes())
        return audio, sample_rate


def write_wave(path, audio, sample_rate):
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


class Frame:
    def __init__(self, byts, timestamp, duration):
        self.bytes = byts
        self.timestamp = timestamp
        self.duration = duration

    def __add__(self, other):
        if self.timestamp <= other.timestamp:
            return Frame(self.bytes + other.bytes, self.timestamp, self.duration + other.duration)
        else:
            return Frame(other.bytes + self.bytes, other.timestamp, self.duration + other.duration)


class VoiceActivityDetector:

    def __init__(self, wave_file):
        self.audio, self.sample_rate = read_wave(wave_file)

    def get_voice_chunks(self, frame_duration, padding_frame_duration, mode=1, save_files=False):
        n = int(self.sample_rate * (frame_duration / 1000.0) * 2)
        offset = 0
        timestamp = 0.0
        duration = float(n) / self.sample_rate / 2.0
        frames = []
        while offset + n < len(self.audio):
            frames.append(Frame(self.audio[offset:offset + n], timestamp, duration))
            timestamp += duration
            offset += n

        collect_chunks = False
        import collections
        padding_frames = int(padding_frame_duration / frame_duration)
        buf = collections.deque(maxlen=padding_frames)
        voice_chucks = []
        vad = webrtcvad.Vad(mode=mode)
        results = []
        for frame in frames:
            has_voice = vad.is_speech(frame.bytes, self.sample_rate)
            if not collect_chunks:
                buf.append((frame, has_voice))
                num_voice = len(list(filter(lambda x: x[1], buf)))
                if num_voice > buf.maxlen * 0.9:
                    collect_chunks = True
                    for f, s in buf:
                        voice_chucks.append(f)
                    buf.clear()
            else:
                voice_chucks.append(frame)
                buf.append((frame, has_voice))
                num_novoice = len(list(filter(lambda x: not x[1], buf)))
                if num_novoice > buf.maxlen * 0.9:
                    collect_chunks = False
                    results.append(functools.reduce(lambda x, y: x + y, voice_chucks))
                    buf.clear()
                    voice_chucks.clear()
        if voice_chucks:
            results.append(functools.reduce(lambda x, y: x + y, voice_chucks))
        if save_files:
            for i, frame in enumerate(results):
                write_wave(f'save_audio/results-{i}.wav', frame.bytes, self.sample_rate)
        return results
