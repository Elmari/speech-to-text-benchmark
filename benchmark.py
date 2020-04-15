import argparse

import editdistance
from num2words import num2words

from dataset import *
from engine import *

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--engine_type', type=str, required=True)
    args = parser.parse_args()

    print('Engine type is %s' % str(args.engine_type))

    dataset = Dataset.create('tudade')
    print('loaded %s with %.2f hours of data' % (str(dataset), dataset.size_hours()))

    engine = ASREngine.create(ASREngines[args.engine_type])
    print('created %s engine' % str(engine))

    word_error_count = 0
    word_count = 0
    composite_errors = list()
    composite_error_count = 0

    millis = int(round(time.time() * 1000))

    for i in range(dataset.size()):
        print("sample %s of %s" % (str(i + 1), str(dataset.size())))
        path, ref_transcript = dataset.get(i)

        transcript = engine.transcribe(path)

        ref_words = ref_transcript.strip('\n ').lower().split()
        words = transcript.strip('\n ').lower().split()

        if isinstance(dataset, TudaDeDataset) and dataset.cleaned:
            for word in range(len(words)):
                if words[word].isnumeric(): words[word] = num2words(words[word], lang='de')

        for ref_word in range(len(ref_words)):
            for word in range(len(words)):
                if (ref_words[ref_word].startswith(words[word])
                        and ref_words[ref_word] != words[word] and word + 1 < len(words)):
                    comp = list()
                    comp.append(words[word])
                    for following in range(word + 1, len(words)):
                        if not ref_words[ref_word].startswith(''.join(comp) + words[following]): break
                        if ''.join(comp) is ref_words[ref_word]: break
                        comp.append(words[following])

                    if ''.join(comp) == ref_words[ref_word]:
                        composite_error_count += len(comp)
                        composite_errors.append((ref_words[ref_word], comp))

        distance = editdistance.eval(ref_words, words)
        print("Ref: %s" % ref_words)
        print("Got: %s" % words)
        print("Distance: %s" % str(distance))

        word_error_count += distance
        word_count += len(ref_words)

    print('word count: %d' % word_count)
    print('word error count : %d' % word_error_count)
    print('Composite error count : %d' % composite_error_count)
    print('word error rate without composite errors : %.2f' % (
            100 * float(word_error_count - len(composite_errors)) / word_count))
    print('word error rate : %.2f' % (100 * float(word_error_count) / word_count))
    end_millis = int(round(time.time() * 1000))
    print("Start: %s", str(millis))
    print("End: %s", str(end_millis))
