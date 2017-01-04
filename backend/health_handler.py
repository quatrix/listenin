from base_handler import BaseHandler


def _get_last_sample_date(club):
    try:
        return club['samples'][0]['date']
    except (IndexError, TypeError):
        return None


class HealthHandler(BaseHandler):
    def get_last_upload(self, club_id):
        return _get_last_sample_date(self.settings['clubs'].get(club_id))

    def get_all_last_upload(self):
        return {
            club['club_id']: {'last_upload': _get_last_sample_date(club)}
            for club in self.settings['clubs'].all()
        }

    def get(self):
        club_id = self.get_argument('club_id')

        if club_id == 'all':
            self.finish(self.get_all_last_upload())
        else:
            self.finish({
                'last_upload': self.get_last_upload(club_id)
            })
