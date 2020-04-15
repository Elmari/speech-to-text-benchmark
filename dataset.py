import os
import sys

import soundfile
from bs4 import BeautifulSoup


class Dataset(object):
    def size(self):
        raise NotImplementedError()

    def size_hours(self):
        return sum(soundfile.read(self.get(i)[0])[0].size / (16000 * 3600) for i in range(self.size()))

    def get(self, index):
        raise NotImplementedError()

    def __str__(self):
        raise NotImplementedError()

    @classmethod
    def create(cls, dataset_type):
        if dataset_type == 'librispeech':
            return LibriSpeechDataset(
                os.path.join(os.path.dirname(__file__), os.path.normpath('resources/data/LibriSpeech/test-clean')))
        elif dataset_type == 'tudade':
            return TudaDeDataset('resources/data/german-speechdata-package-v2/test', False, False)
        else:
            raise ValueError("cannot create %s of type '%s'" % (cls.__name__, dataset_type))


class LibriSpeechDataset(Dataset):
    def __init__(self, root):
        self._data = list()

        print('Initializing librispeech')

        for speaker_id in os.listdir(root):
            speaker_dir = os.path.join(root, speaker_id)
            print('Speaker Dir %s' % speaker_dir)
            for chapter_id in os.listdir(speaker_dir):
                chapter_dir = os.path.join(speaker_dir, chapter_id)
                print('chapter %s' % chapter_dir)

                transcript_path = os.path.join(chapter_dir, '%s-%s.trans.txt' % (speaker_id, chapter_id))
                with open(transcript_path, 'r') as f:
                    transcripts = dict(x.split(' ', maxsplit=1) for x in f.readlines())

                for flac_file in os.listdir(chapter_dir):
                    if flac_file.endswith('.flac'):
                        print("ends with flac")
                        wav_file = flac_file.replace('.flac', '.wav')
                        print("renamed")
                        wav_path = os.path.join(chapter_dir, wav_file)
                        if not os.path.exists(wav_path):
                            print("wav does not exist")
                            try:
                                flac_path = os.path.join(chapter_dir, flac_file)
                                print("path is %s" % flac_path)
                                pcm, sample_rate = soundfile.read(flac_path)
                                soundfile.write(wav_path, pcm, sample_rate)
                            except Exception as e:
                                print("an error occured")

                            print("wrote file")
                        self._data.append((wav_path, transcripts[wav_file.replace('.wav', '')]))
                        print("appended to list")

    def size(self):
        return len(self._data)

    def get(self, index):
        return self._data[index]

    def __str__(self):
        return 'LibriSpeech'


class TudaDeDataset(Dataset):

    def __init__(self, root, cleaned, without_punctuation):
        self._data = list()
        self.cleaned = cleaned
        self.without_punctuation = without_punctuation

        for filename in os.listdir(root):
            if not filename.endswith('.xml'): continue
            print("processing file %s " % filename)
            fullname = os.path.join(root, filename)
            media = os.path.join(root, filename.replace('.xml', '_Kinect-RAW.wav'))
            if not os.path.exists(media): continue
            infile = open(fullname, "r")
            contents = infile.read()
            soup = BeautifulSoup(contents, 'lxml')
            if cleaned:
                transcript = soup.find('cleaned_sentence').string
            else:
                transcript = soup.find('sentence').string

            if transcript is not None:
                if without_punctuation:
                    transcript = transcript.replace(".", "")
                    transcript = transcript.replace(",", "")
                    transcript = transcript.replace("!", "")
                    transcript = transcript.replace("?", "")
                    transcript = transcript.replace(";", "")
                    transcript = transcript.replace("\"", "")
                    transcript = transcript.replace("(", "")
                    transcript = transcript.replace(")", "")
                    transcript = transcript.replace(":", "")

                self._data.append((media, transcript))
            else:
                print("Is none: %s" % filename)
                sys.exit()

            infile.close()

    def size(self):
        return len(self._data)

    def get(self, index):
        return self._data[index]

    def __str__(self):
        return 'Tuda-DE'
