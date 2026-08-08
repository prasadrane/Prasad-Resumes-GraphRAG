"""
Unit tests for static_graph_reader.py
"""

import unittest
from src.query.static_graph_reader import search_static_graph, read_precomputed_entities

class TestStaticGraphReader(unittest.TestCase):

    def test_read_precomputed_entities(self):
        entities = read_precomputed_entities()
        self.assertIsInstance(entities, list)

    def test_search_static_graph(self):
        res = search_static_graph(["AWS", "Python"])
        self.assertIsInstance(res, list)

if __name__ == "__main__":
    unittest.main()
