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
import yaml
from lockfile import FileLock

from fabnet.core.operator_base import  OperationBase
from fabnet.core.fri_base import FabnetPacketResponse
from fabnet.core.constants import RC_OK, NT_SUPERIOR, NT_UPPER


TOPOLOGY_FILE = 'fabnet_topology.info'

class TopologyCognition(OperationBase):
    def before_resend(self, packet):
        """In this method should be implemented packet transformation
        for resend it to neighbours

        @params packet - object of FabnetPacketRequest class
        @return object of FabnetPacketRequest class
                or None for disabling packet resend to neigbours
        """
        if packet.sender is None:
            lock = FileLock(os.path.join(self.operator.home_dir, TOPOLOGY_FILE))
            lock.acquire()
            try:
                open(lock.path, 'w').write('')
            finally:
                lock.release()

        return packet

    def process(self, packet):
        """In this method should be implemented logic of processing
        reuqest packet from sender node

        @param packet - object of FabnetPacketRequest class
        @return object of FabnetPacketResponse
                or None for disabling packet response to sender
        """
        ret_params = {}
        upper_neighbours = self.operator.get_neighbours(NT_UPPER)
        superior_neighbours = self.operator.get_neighbours(NT_SUPERIOR)

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

        lock = FileLock(os.path.join(self.operator.home_dir, TOPOLOGY_FILE))
        lock.acquire()
        try:
            obj = yaml.load(open(lock.path))
            if obj is None:
                nodes = []
            else:
                nodes = obj.get('nodes', [])
            nodes.append({'address': node_address,
                            'superiors': superior_neighbours,
                            'uppers': upper_neighbours,
                            'name': node_name})

            yaml.add_representer(unicode, lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:str', value))
            yaml.dump({'nodes': nodes}, open(lock.path, 'w'))
        finally:
            lock.release()

