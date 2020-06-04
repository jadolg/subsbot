import re

import cloudscraper

scraper = cloudscraper.create_scraper()


class Episode:
    id = 0
    name = 'no name'
    subtitles = []

    def __init__(self, id, name, subtitles):
        self.id = id
        self.name = name
        self.subtitles = subtitles

    def __str__(self):
        return f'[{self.id}] -> `{self.name}` -> {self.subtitles}'


class Serie:
    id = 0
    name = "no name"

    @staticmethod
    def get_series_list():
        scraper = cloudscraper.create_scraper()
        result = []
        series_page = scraper.get('https://www.tusubtitulo.com/series.php').text
        for serie in re.findall(
                '<td class="line0"><img class="icon" src="images/icon-television.png" height="16" width="16"><a href="/show/(.*?)">(.*?)<',
                series_page):
            result.append(Serie(id=serie[0], name=serie[1]))
        return result

    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __str__(self):
        return f'[{self.id}] -> {self.name}'

    def get_seasons(self):
        result = []
        temporadas_page = scraper.get(f'https://www.tusubtitulo.com/show/{self.id}').text
        for temporada in re.findall('<a href="#" data-season="(.*?)">(.*?)</a>', temporadas_page):
            result.append(temporada[0])
        return result

    def get_episodes(self, season):
        result = []
        scraper = cloudscraper.create_scraper()
        episodes_page = scraper.get(
            f'https://www.tusubtitulo.com/ajax_loadShow.php?show={self.id}&season={season}').text
        for episodio_text in re.findall('<table width="80%" border="0" cellpadding="0" cellspacing="0">(.*?)</table>',
                                        episodes_page, re.DOTALL):
            for episodio in re.findall("<a href='//www.tusubtitulo.com/episodes/(\d+)/(.*?)'>(.*?)</a>", episodio_text):
                subtitles = []
                for download in re.findall(f'(\d+/{episodio[0]}/\d+)">', episodes_page):
                    lang = 'Unknow'
                    for i in re.findall(
                            f'<td width="41%" class="language">\n\s*(.*?)\s*</td>\n\s*<td width="17%">\n.*?\n\s*<td>\n\s*<img src="//www.tusubtitulo.com/images/download.png" width=16" height="16" /><a href="//www.tusubtitulo.com/updated/{download}">',
                            episodio_text):
                        lang = i
                        break
                    subtitles.append((lang, f'https://www.tusubtitulo.com/updated/{download}'))

                result.append(Episode(id=episodio[0], name=episodio[2], subtitles=subtitles))

        return result
