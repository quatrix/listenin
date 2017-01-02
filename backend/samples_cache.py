"""
Samples cache
"""

from collections import defaultdict
import json
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

    def latest(self, box_id):
        """
        Returns latest sample for box
        """

        try:
            return self._samples[box_id][0]
        except (KeyError, IndexError):
            return None

    def add(self, sample, metadata, box_id):
        """
        Insert sample into box samples while keeping samples size n_samples
        """

        self._write_metadata(sample, metadata, box_id)

        if len(self._samples[box_id]) == self.n_samples:
            self._samples[box_id].pop()

        self._samples[box_id].insert(0, self._enrich_sample(sample, box_id))

    def toggle_hiddeness(self, box_id, sample):
        metadata = json.loads(open(self._get_json_path(box_id, sample)).read())
        metadata['hidden'] = not metadata.get('hidden', False)
        self._write_metadata(sample, metadata, box_id)

        for s in self._samples[box_id]:
            if s['_created'] == sample:
                s['metadata']['hidden'] = not s['metadata'].get('hidden', False)
                break

    def replace_latest(self, sample, metadata, box_id):
        """
        Replaces last sample with new sample
        """

        self._write_metadata(sample, metadata, box_id)

        os.unlink(self._get_json_path(box_id, self._samples[box_id][0]['_created']))
        self._samples[box_id][0] = self._enrich_sample(sample, box_id)

    def _populate_samples_cache(self):
        for box_id in os.listdir(self.samples_root):
            self._samples[box_id] = self._enrich_samples(self._get_samples(box_id), box_id)

    def _get_samples(self, box_id):
        path = os.path.join(self.samples_root, box_id)
        samples = [sample for sample in os.listdir(path) if sample.endswith('.json')]
        samples = [number_part_of_sample(sample) for sample in samples]
        return sorted(samples, reverse=True)[:self.n_samples]

    def _get_metadata(self, sample, box_id):
        return get_metadata_from_json(self._get_json_path(box_id, sample))

    def _enrich_sample(self, sample, box_id):
        return {
            '_created': sample,
            'date': unix_time_to_readable_date(sample),
            'link': os.path.join(self.base_url, 'uploads', box_id, '{}.mp3'.format(sample)),
            'metadata': self._get_metadata(sample, box_id),
        }

    def _enrich_samples(self, samples, box_id):
        return [self._enrich_sample(sample, box_id) for sample in samples]

    def _write_metadata(self, sample, metadata, box_id):
        open(self._get_json_path(box_id, sample), 'w').write(json.dumps(metadata))

    def _get_json_path(self, box_id, sample):
        return os.path.join(self.samples_root, box_id, '{}.json'.format(sample))
