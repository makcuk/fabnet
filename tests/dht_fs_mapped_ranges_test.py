import unittest
import threading
import time
import os
import logging
import json
import shutil
from datetime import datetime
from fabnet.utils.logger import logger
from fabnet.dht_mgmt.fs_mapped_ranges import FSHashRanges

logger.setLevel(logging.DEBUG)

TEST_FS_RANGE_DIR = '/tmp/test_fs_ranges'
START_RANGE_HASH = '%040x'%0
END_RANGE_HASH = '%040x'%10000000000


class WriteThread(threading.Thread):
    def __init__(self, fs_ranges, start, end):
        threading.Thread.__init__(self)
        self.fs_ranges = fs_ranges
        self.start_i = start
        self.end_i = end

    def run(self):
        for i in range(self.start_i, self.end_i):
            self.fs_ranges.put('%040x'%((i+1000)*100), 'T'*1000)

class ReadThread(threading.Thread):
    def __init__(self, fs_ranges):
        threading.Thread.__init__(self)
        self.fs_ranges = fs_ranges

    def run(self):
        for i in xrange(100000):
            try:
                data = self.fs_ranges.get('%040x'%((i+1000)*100))
                if data != 'T'*1000:
                    print 'FAILED DATA [%s]: %s'%('%040x'%((i+1000)*100), len(data))
            except Exception, err:
                print 'GET DATA EXCEPTION: %s'%err


class TestFSMappedRanges(unittest.TestCase):
    def test00_init(self):
        if os.path.exists(TEST_FS_RANGE_DIR):
            shutil.rmtree(TEST_FS_RANGE_DIR)
        os.mkdir(TEST_FS_RANGE_DIR)

    def _test99_destroy(self):
        if os.path.exists(TEST_FS_RANGE_DIR):
            shutil.rmtree(TEST_FS_RANGE_DIR)

    def test01_discovery_ranges(self):
        fs_range = FSHashRanges(START_RANGE_HASH, END_RANGE_HASH, TEST_FS_RANGE_DIR)
        fs_range.put(100, 'Test data #1')
        fs_range.put(900, 'Test data #2')
        fs_range.put(10005000, 'Test data #3')
        fs_range.split_range(0, 100500)

        discovered_range = FSHashRanges.discovery_range(TEST_FS_RANGE_DIR)
        self.assertEqual(discovered_range.get_start(), long(START_RANGE_HASH, 16))
        self.assertEqual(discovered_range.get_end(), long(END_RANGE_HASH, 16))

        range_dir = discovered_range.get_range_dir()
        self.assertTrue(os.path.exists(os.path.join(range_dir, '%040x'%100)))
        self.assertTrue(os.path.exists(os.path.join(range_dir, '%040x'%900)))
        self.assertTrue(os.path.exists(os.path.join(range_dir, '%040x'%10005000)))


    def test02_main(self):
        fs_ranges = FSHashRanges(START_RANGE_HASH, END_RANGE_HASH, TEST_FS_RANGE_DIR)

        self.assertTrue(os.path.exists(os.path.join(TEST_FS_RANGE_DIR, '%s_%s'%(START_RANGE_HASH, END_RANGE_HASH))))

        wt = WriteThread(fs_ranges, 0, 40000)
        wt.start()
        wt1 = WriteThread(fs_ranges, 40000, 70000)
        wt1.start()
        wt2 = WriteThread(fs_ranges, 70000, 100000)
        wt2.start()

        time.sleep(2)
        ret_range, new_range = fs_ranges.split_range('%040x'%0, '%040x'%((25000)*100))
        for key, data in ret_range.iter_range():
            if data != 'T'*1000:
                print 'FAILED ITER DATA [%s]: %s'%(key, len(data))

        wt.join()
        wt1.join()
        wt2.join()

        fs_ranges.join_subranges()

        rt = ReadThread(fs_ranges)
        rt.start()

        data = fs_ranges.get_subranges()
        self.assertEqual(data, None)
        fs_ranges.split_range('%040x'%0, '%040x'%((45000)*100))

        ret_range, new_range = fs_ranges.get_subranges()
        size = ret_range.get_range_size()
        self.assertTrue(size > 0)

        ret_range.move_to_trash()
        fs_ranges.move_to_trash()

        free_size = new_range.get_free_size()
        self.assertTrue(size > 0)

        new_range.restore_from_trash()

        self.assertTrue(os.path.exists(os.path.join(TEST_FS_RANGE_DIR, 'trash')))

        rt.join()
        new_range.put('%040x'%100500, 'final data test')
        data = new_range.get('%040x'%100500)
        self.assertEqual(data, 'final data test')

        try:
            new_range.extend('%040x'%0, '%040x'%100)
        except:
            pass
        else:
            raise Exception('Expected error in this case.')

        extended_range = new_range.extend('%040x'%0, '%040x'%((45000)*100-1))
        data = extended_range.get('%040x'%100500)
        self.assertNotEqual(data, 'final data test')


if __name__ == '__main__':
    unittest.main()

