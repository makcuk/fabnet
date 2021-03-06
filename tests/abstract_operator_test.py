import unittest
import time
import os
import logging
import json
from fabnet.core import constants
constants.CHECK_NEIGHBOURS_TIMEOUT = 1
from fabnet.core.fri_server import FriServer, FabnetPacketRequest, FabnetPacketResponse
from fabnet.core.key_storage import FileBasedKeyStorage
from fabnet.core.operator import Operator
from fabnet.core.operation_base import OperationBase
from fabnet.utils.logger import logger
from datetime import datetime

from fabnet.core.constants import NODE_ROLE, CLIENT_ROLE

logger.setLevel(logging.DEBUG)

VALID_STORAGE = './tests/cert/test_keystorage.zip'
INVALID_STORAGE = './tests/cert/test_keystorage_invalid.zip'
PASSWD = 'qwerty123'


class EchoOperation(OperationBase):
    ROLES = [NODE_ROLE, CLIENT_ROLE]
    def before_resend(self, packet):
        pass

    def process(self, packet):
        open('/tmp/server1.out', 'w').write(json.dumps(packet.to_dict()))
        return FabnetPacketResponse(ret_code=0, ret_message='ok', ret_parameters={'message': packet.parameters['message']})

    def callback(self, packet, sender):
        open('/tmp/server2.out', 'w').write(json.dumps(packet.to_dict()))


class TestAbstractOperator(unittest.TestCase):
    def test00_echo_operation(self):
        self.__test_server()

    def test01_ssl_echo_operation(self):
        self.__test_server(FileBasedKeyStorage(VALID_STORAGE, PASSWD))

    def __test_server(self, keystorage=None):
        server1 = server2 = None
        try:
            operator = Operator('127.0.0.1:1986', key_storage=keystorage)
            operator.neighbours = ['127.0.0.1:1987']
            operator.register_operation('ECHO', EchoOperation)
            server1 = FriServer('0.0.0.0', 1986, operator, 10, 'node_1', keystorage)
            ret = server1.start()
            self.assertEqual(ret, True)

            operator = Operator('127.0.0.1:1987', key_storage=keystorage)
            operator.neighbours = ['127.0.0.1:1986']
            operator.register_operation('ECHO', EchoOperation)
            server2 = FriServer('0.0.0.0', 1987, operator, 10, 'node_2', keystorage)
            ret = server2.start()
            self.assertEqual(ret, True)

            packet = { 'message_id': 323232,
                        'method': 'ECHO',
                        'sync': False,
                        'sender': '127.0.0.1:1987',
                        'parameters': {'message': 'test message'}}

            if keystorage:
                packet['session_id'] = keystorage.get_node_cert_key()

            packet_obj = FabnetPacketRequest(**packet)
            rcode, rmsg = operator.call_node('127.0.0.1:1986', packet_obj)
            self.assertEqual(rcode, 0, rmsg)

            operator.wait_response(323232, 1)

            self.assertEqual(os.path.exists('/tmp/server1.out'), True)
            self.assertEqual(os.path.exists('/tmp/server2.out'), True)

            request = json.loads(open('/tmp/server1.out').read())
            response = json.loads(open('/tmp/server2.out').read())
            self.assertEqual(request, packet)
            good_resp = {'from_node': '127.0.0.1:1986','message_id': 323232,
                'ret_code': 0,
                'ret_message': 'ok',
                'ret_parameters': {'message': 'test message'}}
            self.assertEqual(response, good_resp)
        finally:
            if server1:
                server1.stop()
            if server2:
                server2.stop()

    def test02_ssl_bad_cert(self):
        keystorage = FileBasedKeyStorage(VALID_STORAGE, PASSWD)
        inv_keystorage = FileBasedKeyStorage(INVALID_STORAGE, PASSWD)
        server1 = server2 = None
        try:
            operator = Operator('127.0.0.1:1986', key_storage=keystorage)
            operator.neighbours = ['127.0.0.1:1987']
            operator.register_operation('ECHO', EchoOperation)
            server1 = FriServer('0.0.0.0', 1986, operator, 10, 'node_1', keystorage)
            ret = server1.start()
            self.assertEqual(ret, True)

            operator = Operator('127.0.0.1:1987', key_storage=inv_keystorage)
            operator.neighbours = ['127.0.0.1:1986']
            operator.register_operation('ECHO', EchoOperation)
            server2 = FriServer('0.0.0.0', 1987, operator, 10, 'node_2', inv_keystorage)
            ret = server2.start()
            self.assertEqual(ret, True)

            packet = { 'message_id': 323232,
                        'method': 'ECHO',
                        'sync': False,
                        'sender': '127.0.0.1:1987',
                        'parameters': {'message': 'test message'}}
            packet_obj = FabnetPacketRequest(**packet)
            rcode, rmsg = operator.call_node('127.0.0.1:1986', packet_obj)
            self.assertEqual(rcode, 1, rmsg)

            time.sleep(.1)
        finally:
            if server1:
                server1.stop()
            if server2:
                server2.stop()

if __name__ == '__main__':
    unittest.main()

