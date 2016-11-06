import unittest
from cache_tagging import defer

try:
    from unittest import mock
except ImportError:
    import mock


class DeferredTestCase(unittest.TestCase):
    def test_parent(self):
        d1 = defer.Deferred(None, defer.NoneDeferredIterator)
        d2 = defer.Deferred(None, defer.NoneDeferredIterator)
        d1.parent = d2
        d3 = defer.Deferred(None, defer.NoneDeferredIterator)
        d2.parent = d3

        d4 = defer.Deferred(None, defer.NoneDeferredIterator)
        d5 = defer.Deferred(None, defer.NoneDeferredIterator)
        d4.parent = d5

        d1.parent = d4

        d_order = [d1, d2, d3, d4, d5, None]
        for i in range(0, 4):
            self.assertIs(d_order[i].parent, d_order[i + 1],
                          "d{0}.parent is not d{1}".format(i + 1, i + 2))
        for i in range(0, 4):
            self.assertIs(d_order[i].iterator.state, d_order[i + 1].iterator.state,
                          "d{0}.iterator.state is not d{1}.iterator.state".format(i + 1, i + 2))


class GetManyDeferredIteratorTestCase(unittest.TestCase):

    def test_get_many(self):
        cached = {
            'tag_1': 'tag_1_value',
            'tag_2': 'tag_2_value',
            'tag_3': 'tag_3_value',
            'tag_4': 'tag_4_value',
            'locked_tag_1': 'locked_tag_1_value',
            'locked_tag_2': 'locked_tag_2_value',
            'locked_tag_3': 'locked_tag_3_value',
            'locked_tag_4': 'locked_tag_4_value',
        }
        executor1 = mock.Mock(side_effect=lambda keys, versions: cached)
        deferred = defer.Deferred(executor1, defer.GetManyDeferredIterator, None)
        deferred.add_callback(
            lambda _, caches: {'result1_' + k: v for k, v in caches.items()},
            set(('tag_1', 'tag_2',))
        )

        executor2 = mock.Mock(side_effect=lambda keys, versions: cached)
        deferred2 = defer.Deferred(executor2, defer.GetManyDeferredIterator, 1)
        deferred2.add_callback(
            lambda _, caches: {'result2_' + k: v for k, v in caches.items()},
            set(('tag_3', 'tag_4',))
        )
        deferred += deferred2

        deferred3 = defer.Deferred(executor1, defer.GetManyDeferredIterator, None)
        deferred3.add_callback(
            lambda _, caches: {'result3_' + k: v for k, v in caches.items()},
            set(('locked_tag_1', 'locked_tag_2',))
        )
        deferred += deferred3
        result3 = deferred.get()

        self.assertDictEqual(result3, {
            'result3_locked_tag_1': 'locked_tag_1_value',
            'result3_locked_tag_2': 'locked_tag_2_value',
        })

        result2 = deferred.get()
        self.assertDictEqual(result2, {
            'result2_tag_3': 'tag_3_value',
            'result2_tag_4': 'tag_4_value',
        })

        result1 = deferred.get()
        self.assertDictEqual(result1, {
            'result1_tag_1': 'tag_1_value',
            'result1_tag_2': 'tag_2_value',
        })

        self.assertEqual(executor1.call_count, 1)
        self.assertSetEqual(set(executor1.call_args[0][0]),
                            set(('tag_1', 'tag_2', 'locked_tag_1', 'locked_tag_2',)))
        self.assertIsNone(executor1.call_args[0][1])
        self.assertDictEqual(executor1.call_args[1], dict())

        self.assertEqual(executor2.call_count, 1)
        self.assertSetEqual(set(executor2.call_args[0][0]),
                            set(('tag_3', 'tag_4',)))
        self.assertEqual(executor2.call_args[0][1], 1)
        self.assertDictEqual(executor2.call_args[1], dict())
