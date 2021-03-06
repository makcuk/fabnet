#!/usr/bin/python
"""
Copyright (C) 2012 Konstantin Andrusenko
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.

@package fabnet.dht_mgmt.operations.get_ranges_table

@author Konstantin Andrusenko
@date September 21, 2012
"""
from fabnet.core.operation_base import  OperationBase
from fabnet.core.fri_base import FabnetPacketResponse
from fabnet.dht_mgmt.constants import DS_INITIALIZE
from fabnet.core.constants import RC_ERROR, RC_OK, NODE_ROLE
from fabnet.utils.logger import logger

class GetRangesTableOperation(OperationBase):
    ROLES = [NODE_ROLE]
    def process(self, packet):
        """In this method should be implemented logic of processing
        reuqest packet from sender node

        @param packet - object of FabnetPacketRequest class
        @return object of FabnetPacketResponse
                or None for disabling packet response to sender
        """
        if self.operator.status == DS_INITIALIZE:
            return FabnetPacketResponse(ret_code=RC_ERROR, ret_message='Node is not initialized yet!')

        ranges_table = self.operator.ranges_table.dump()

        logger.info('Sending ranges table to %s'%packet.sender)

        return FabnetPacketResponse(ret_parameters={'ranges_table': ranges_table})

    def callback(self, packet, sender=None):
        """In this method should be implemented logic of processing
        response packet from requested node

        @param packet - object of FabnetPacketResponse class
        @param sender - address of sender node.
        If sender == None then current node is operation initiator
        @return object of FabnetPacketResponse
                that should be resended to current node requestor
                or None for disabling packet resending
        """
        if packet.ret_code != RC_OK:
            logger.info('[GetRangesTableCallback] Node %s does not initialized yet...'%packet.from_node)
            return

        logger.info('Recevied ranges table')

        self.operator.ranges_table.load(str(packet.ret_parameters['ranges_table']))
        logger.info('Ranges table is loaded to fabnet node')

        if self.operator.status == DS_INITIALIZE:
            logger.info('Starting node as DHT member')
            self.operator.start_as_dht_member()
        else:
            self.operator.check_dht_range()


