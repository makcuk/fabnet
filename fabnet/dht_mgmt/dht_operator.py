import os
import time
import threading
from fabnet.core.operator import Operator
from hash_ranges_table import HashRangesTable
from fabnet.dht_mgmt.fs_mapped_ranges import FSHashRanges
from fabnet.core.fri_base import FabnetPacketRequest
from fabnet.utils.logger import logger
from fabnet.dht_mgmt.constants import DS_INITIALIZE, DS_NORMALWORK, \
            WAIT_RANGE_TIMEOUT, MIN_HASH, MAX_HASH, DHT_CYCLE_TRY_COUNT, \
            INIT_DHT_WAIT_NEIGHBOUR_TIMEOUT, WAIT_RANGES_TIMEOUT
from fabnet.core.constants import RC_OK, NT_SUPERIOR, NT_UPPER


class DHTOperator(Operator):
    def __init__(self, self_address, home_dir='/tmp/', certfile=None, is_init_node=False):
        Operator.__init__(self, self_address, home_dir, certfile, is_init_node)

        self.status = DS_INITIALIZE
        self.ranges_table = HashRangesTable()
        if is_init_node:
            self.ranges_table.append(MIN_HASH, MAX_HASH, self.self_address)

        self.save_path = os.path.join(home_dir, 'dht_range')
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

        self.__dht_range = FSHashRanges.discovery_range(self.save_path)
        self.__split_requests_cache = []
        self.__start_dht_try_count = 0
        self.__init_dht_thread = None
        if is_init_node:
            self.status = DS_NORMALWORK
        else:
            self.__init_dht_thread = InitDHTThread(self)
            self.__init_dht_thread.start()

    def stop(self):
        if self.__init_dht_thread and self.__init_dht_thread.is_alive():
            self.__init_dht_thread.stop()
            self.__init_dht_thread.join()

    def __get_next_max_range(self):
        max_range = None
        for range_obj in self.ranges_table.iter_table():
            if range_obj.node_address in self.__split_requests_cache:
                continue

            if not max_range:
                max_range = range_obj
                continue

            if max_range.length() < range_obj.length():
                max_range = range_obj

        return max_range


    def __get_next_range_near(self, start, end):
        found_range = self.ranges_table.find(start)
        if found_range and found_range.node_address not in self.__split_requests_cache:
            return found_range

        found_range = self.ranges_table.find(end)
        if found_range and found_range.node_address not in self.__split_requests_cache:
            return found_range

        return None


    def start_as_dht_member(self):
        dht_range = self.get_dht_range()

        nochange = False
        curr_start = dht_range.get_start()
        curr_end = dht_range.get_end()

        if dht_range.is_max_range() or self.__split_requests_cache:
            new_range = self.__get_next_max_range()
        else:
            new_range = self.__get_next_range_near(curr_start, curr_end)
            if new_range and (new_range.start != curr_start or new_range.end != curr_end):
                nochange = True

        logger.debug('Selected range for split: %s'% new_range)
        if new_range is None:
            #wait and try again
            if self.__start_dht_try_count == DHT_CYCLE_TRY_COUNT:
                logger.error('Cant initialize node as a part of DHT')
                self.__start_dht_try_count = 0
                return

            logger.info('No ready range for me on network... So, sleep and try again')
            self.__start_dht_try_count += 1
            self.__split_requests_cache = []
            time.sleep(WAIT_RANGE_TIMEOUT)
            return self.start_as_dht_member()

        if nochange:
            new_dht_range = dht_range
        else:
            new_dht_range = FSHashRanges(long(new_range.start + new_range.length()/2), long(new_range.end), self.save_path)
            self.update_dht_range(new_dht_range)
            new_dht_range.restore_from_trash() #try getting new range data from trash

        self.__split_requests_cache.append(new_range.node_address)

        logger.info('Call SplitRangeRequest to %s'%(new_range.node_address,))
        parameters = { 'start_key': new_dht_range.get_start(), 'end_key': new_dht_range.get_end() }
        req = FabnetPacketRequest(method='SplitRangeRequest', sender=self.self_address, parameters=parameters)
        ret_code, ret_msg = self.call_node(new_range.node_address, req)
        if ret_code != RC_OK:
            logger.error('Cant start SplitRangeRequest operation on node %s. Details: %s'%(new_range.node_address, ret_msg))
            return self.start_as_dht_member()


    def get_dht_range(self):
        self._lock()
        try:
            return self.__dht_range
        finally:
            self._unlock()

    def update_dht_range(self, new_dht_range):
        self._lock()
        old_dht_range = self.__dht_range
        self.__dht_range = new_dht_range
        self._unlock()

        old_dht_range.move_to_trash()


class InitDHTThread(threading.Thread):
    def __init__(self, operator):
        threading.Thread.__init__(self)
        self.operator = operator
        self.stopped = True

    def run(self):
        self.stopped = False
        try:
            while not self.stopped:
                if not self.operator.ranges_table.empty():
                    break

                neighbours = self.operator.get_neighbours(NT_UPPER) + \
                         self.operator.get_neighbours(NT_SUPERIOR)

                for neighbour in neighbours:
                    logger.info('Requesting ranges table from %s'%neighbour)
                    packet_obj = FabnetPacketRequest(method='GetRangesTable', sender=self.operator.self_address)
                    rcode, rmsg = self.operator.call_node(neighbour, packet_obj)
                    if rcode == RC_OK:
                        time.sleep(WAIT_RANGES_TIMEOUT)
                        break
                    else:
                        logger.error('Cant start GetRangesTable on %s. Details: %s'%(neighbour, rmsg))

                time.sleep(INIT_DHT_WAIT_NEIGHBOUR_TIMEOUT)
        except Exception, err:
            logger.error('[InitDHTThread] %s'%err)
        finally:
            logger.info('InitDHTThread finished')

    def stop(self):
        self.stopped = True
