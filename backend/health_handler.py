from base_handler import BaseHandler


class HealthHandler(BaseHandler):
    def get_last_upload(self, box):
        try:
            return self.settings['samples'].all()[box][0]['date']
        except IndexError:
            return None

    def get_all_last_upload(self):
        return {
            box: {'last_upload': self.get_last_upload(box)}
            for box in self.settings['samples'].all().keys()
        }

    def get(self):
        box = self.get_argument('box')

        if box == 'all':
            self.finish(self.get_all_last_upload())
        else:
            self.finish({
                'last_upload': self.get_last_upload(box)
            })
