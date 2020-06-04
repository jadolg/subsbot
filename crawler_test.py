import unittest

from crawler import Serie


class TestCrawler(unittest.TestCase):
    def test_get_series_list(self):
        series_list = Serie.get_series_list()
        self.assertIsInstance(series_list, list)
        self.assertGreater(len(series_list), 0)
        self.assertEqual('3822', series_list[0].id)
        self.assertEqual('#blackAF', series_list[0].name)
        self.assertEqual('[3822] -> #blackAF', series_list[0].__str__())

    def test_get_seasons_and_episodes(self):
        series_list = Serie.get_series_list()
        serie = series_list[0]
        self.assertEqual(serie.get_seasons(), ['1', ])
        episodes_season_one = serie.get_episodes('1')
        self.assertGreater(len(episodes_season_one), 0)
        first_episode = episodes_season_one[0]
        self.assertEqual(first_episode.id, '71932')
        self.assertEqual(first_episode.name, '#blackAF 1x01 - because of slavery')
        self.assertEqual(first_episode.subtitles,
                         [('English', 'https://www.tusubtitulo.com/updated/1/71932/0'),
                          ('Español (España)', 'https://www.tusubtitulo.com/updated/5/71932/1'),
                          ('Español (Latinoamérica)', 'https://www.tusubtitulo.com/updated/6/71932/2'),
                          ])
        self.assertEqual(first_episode.__str__(),
                         "[5275] -> `10 Things I Hate About You 1x01 - Pilot` -> [('Español (Latinoamérica)', 'https://www.tusubtitulo.com/updated/6/5275/0'), ('Español (España)', 'https://www.tusubtitulo.com/updated/5/5275/1')]")
