import unittest

from crawler import Serie


class TestCrawler(unittest.TestCase):
    def test_get_series_list(self):
        series_list = Serie.get_series_list()
        self.assertIsInstance(series_list, list)
        self.assertGreater(len(series_list), 0)
        self.assertEqual(series_list[0].id, '317')
        self.assertEqual(series_list[0].name, '10 Things I Hate About You')
        self.assertEqual(series_list[0].__str__(), '[317] -> 10 Things I Hate About You')

    def test_get_seasons_and_episodes(self):
        series_list = Serie.get_series_list()
        serie = series_list[0]
        self.assertEqual(serie.get_seasons(), ['1', '2'])
        episodes_season_one = serie.get_episodes('1')
        self.assertGreater(len(episodes_season_one), 0)
        first_episode = episodes_season_one[0]
        self.assertEqual(first_episode.id, '5275')
        self.assertEqual(first_episode.name, '10 Things I Hate About You 1x01 - Pilot')
        self.assertEqual(first_episode.subtitles,
                         [('Español (Latinoamérica)', 'https://www.tusubtitulo.com/updated/6/5275/0'),
                          ('Español (España)', 'https://www.tusubtitulo.com/updated/5/5275/1')])
        self.assertEqual(first_episode.__str__(),
                         "[5275] -> `10 Things I Hate About You 1x01 - Pilot` -> [('Español (Latinoamérica)', 'https://www.tusubtitulo.com/updated/6/5275/0'), ('Español (España)', 'https://www.tusubtitulo.com/updated/5/5275/1')]")
