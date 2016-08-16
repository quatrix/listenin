"""
Samples cache
"""

from collections import defaultdict
import os

from utils import unix_time_to_readable_date, number_part_of_sample, get_metadata_from_json

class SamplesCache(object):
    """
    Samples cache
    """

    def __init__(self, samples_root, n_samples, base_url):
        self.samples_root = samples_root
        self.n_samples = n_samples
        self.base_url = base_url

        self._samples = defaultdict(list)
        self._populate_samples_cache()

    def all(self):
        """
        Returns dict of clubs -> samples
        """

        return self._samples

    def latest(self, club):
        """
        Returns latest sample for club
        """

        try:
            return self._samples[club][0]
        except (KeyError, IndexError):
            return None

    def add(self, sample, club):
        """
        Insert sample into club samples while keeping samples size n_samples
        """

        if len(self._samples[club]) == self.n_samples:
            self._samples[club].pop()

        self._samples[club].insert(0, self._enrich_sample(sample, club))

    def replace_latest(self, sample, club):
        """
        Replaces last sample with new sample
        """

        os.unlink(self._get_json_path(club, self._samples[club][0]['_created']))
        self._samples[club][0] = self._enrich_sample(sample, club)

    def _populate_samples_cache(self):
        for club in os.listdir(self.samples_root):
            self._samples[club] = self._enrich_samples(self._get_samples(club), club)

    def _get_samples(self, club):
        path = os.path.join(self.samples_root, club)
        samples = [sample for sample in os.listdir(path) if sample.endswith('.json')]
        samples = [number_part_of_sample(sample) for sample in samples]
        return sorted(samples, reverse=True)[:self.n_samples]

    def _enrich_sample(self, sample, club):
        return {
            '_created': sample,
            'date': unix_time_to_readable_date(sample),
            'link': '{}/uploads/{}/{}.mp3'.format(self.base_url, club, sample),
            'metadata': get_metadata_from_json(self._get_json_path(club, sample)),
        }

    def _enrich_samples(self, samples, club):
        return [self._enrich_sample(sample, club) for sample in samples]

    def _get_json_path(self, club, sample):
        return os.path.join(self.samples_root, club, '{}.json'.format(sample))
