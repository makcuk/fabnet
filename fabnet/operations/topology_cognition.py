#!/usr/bin/python
"""
Copyright (C) 2012 Konstantin Andrusenko
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.

@package fabnet.operations.topology_cognition

@author Konstantin Andrusenko
@date September 7, 2012
"""
import os
import sqlite3
import threading
from datetime import datetime

from fabnet.core.operation_base import  OperationBase
from fabnet.core.fri_base import FabnetPacketResponse
from fabnet.core.constants import NT_SUPERIOR, NT_UPPER, \
                        ONE_DIRECT_NEIGHBOURS_COUNT, \
                        NODE_ROLE, CLIENT_ROLE
from fabnet.operations.constants import MNO_APPEND
from fabnet.utils.logger import logger

TOPOLOGY_DB = 'fabnet_topology.db'

class TopologyCognition(OperationBase):
    ROLES = [NODE_ROLE]

    def __init__(self, operator):
        OperationBase.__init__(self, operator)
        self.__last_dt = datetime.now()

    def get_last_processed_dt(self):
        self._lock()
        try:
            return self.__last_dt
        finally:
            self._unlock()

    def get_discovered_nodes(self):
        db = os.path.join(self.operator.home_dir, TOPOLOGY_DB)
        if not os.path.exists(db):
            return {}
        conn = sqlite3.connect(db)

        curs = conn.cursor()
        curs.execute("SELECT node_address, superiors, uppers, old_data FROM fabnet_nodes")
        rows = curs.fetchall()

        curs.close()
        conn.close()

        nodes = {}
        for row in rows:
            nodes[row[0]] = (row[1].split(','), row[2].split(','), int(row[3]))

        return nodes


    def before_resend(self, packet):
        """In this method should be implemented packet transformation
        for resend it to neighbours

        @params packet - object of FabnetPacketRequest class
        @return object of FabnetPacketRequest class
                or None for disabling packet resend to neigbours
        """
        if packet.sender is None:
            self.__balanced = threading.Event()
            conn = sqlite3.connect(os.path.join(self.operator.home_dir, TOPOLOGY_DB))

            curs = conn.cursor()
            curs.execute("CREATE TABLE IF NOT EXISTS fabnet_nodes(node_address TEXT, node_name TEXT, superiors TEXT, uppers TEXT, old_data INT)")
            curs.execute("UPDATE fabnet_nodes SET old_data=1")
            conn.commit()

            curs.close()
            conn.close()

        return packet

    def process(self, packet):
        """In this method should be implemented logic of processing
        reuqest packet from sender node

        @param packet - object of FabnetPacketRequest class
        @return object of FabnetPacketResponse
                or None for disabling packet response to sender
        """
        self._lock()
        try:
            self.__last_dt = datetime.now()
        finally:
            self._unlock()

        ret_params = {}
        upper_neighbours = self.operator.get_neighbours(NT_UPPER)
        superior_neighbours = self.operator.get_neighbours(NT_SUPERIOR)

        ret_params.update(packet.parameters)
        ret_params['node_address'] = self.operator.self_address
        ret_params['node_name'] = self.operator.node_name
        ret_params['upper_neighbours'] = upper_neighbours
        ret_params['superior_neighbours'] = superior_neighbours

        return FabnetPacketResponse(ret_parameters=ret_params)


    def callback(self, packet, sender):
        """In this method should be implemented logic of processing
        response packet from requested node

        @param packet - object of FabnetPacketResponse class
        @param sender - address of sender node.
        If sender == None then current node is operation initiator

        @return object of FabnetPacketResponse
                that should be resended to current node requestor
                or None for disabling packet resending
        """
        if sender:
            return packet

        node_address = packet.ret_parameters.get('node_address', None)
        superior_neighbours = packet.ret_parameters.get('superior_neighbours', None)
        upper_neighbours = packet.ret_parameters.get('upper_neighbours', None)
        node_name = packet.ret_parameters.get('node_name', '')

        if (node_address is None) or (superior_neighbours is None) or (upper_neighbours is None):
            raise Exception('TopologyCognition response packet is invalid! Packet: %s'%str(packet.to_dict()))

        conn = sqlite3.connect(os.path.join(self.operator.home_dir, TOPOLOGY_DB))
        curs = conn.cursor()

        self._lock()
        try:
            curs.execute("SELECT old_data FROM fabnet_nodes WHERE node_address='%s'" % node_address)
            rows = curs.fetchall()
            if rows:
                curs.execute("UPDATE fabnet_nodes SET node_name='%s', superiors='%s', uppers='%s', old_data=0 WHERE node_address='%s'"% \
                    (node_name, ','.join(superior_neighbours), ','.join(upper_neighbours), node_address))
            else:
                curs.execute("INSERT INTO fabnet_nodes VALUES ('%s', '%s', '%s', '%s', 0)"% \
                        (node_address, node_name, ','.join(superior_neighbours), ','.join(upper_neighbours)))
            conn.commit()
        finally:
            self._unlock()
            curs.close()
            conn.close()

        if packet.ret_parameters.get('need_rebalance', False):
            self._lock()
            self.smart_neighbours_rebalance(node_address, superior_neighbours, upper_neighbours)
            self._unlock()


    def smart_neighbours_rebalance(self, node_address, superior_neighbours, upper_neighbours):
        if self.__balanced.is_set():
            return

        if node_address == self.operator.self_address:
            return

        uppers = self.operator.get_neighbours(NT_UPPER)
        superiors = self.operator.get_neighbours(NT_SUPERIOR)
        if (node_address in uppers) or (node_address in superiors):
            return

        if ONE_DIRECT_NEIGHBOURS_COUNT > len(superiors) >= (ONE_DIRECT_NEIGHBOURS_COUNT+1):
            return


        intersec_count = len(set(uppers) & set(superiors))
        if intersec_count == 0:
            #good neighbours connections
            self.__balanced.set()
            return

        intersec_count = len(set(superior_neighbours) & set(upper_neighbours))
        if intersec_count > 0 and (len(upper_neighbours) <= ONE_DIRECT_NEIGHBOURS_COUNT):
            parameters = { 'neighbour_type': NT_UPPER, 'operation': MNO_APPEND,
                            'node_address': self.operator.self_address }
            rcode, rmsg = self._init_operation(node_address, 'ManageNeighbour', parameters)
            if not rcode:
                self.__balanced.set()


