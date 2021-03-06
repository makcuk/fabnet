import unittest
import time
import os
import logging
import shutil
import threading
import json
import random
import subprocess
import signal
import string
import hashlib


from client.security_manager import init_security_manager

CLIENT_KS_PATH = './tests/cert/test_client_ks.zip'
PASSWD = 'qwerty123'

class TestSecManager(unittest.TestCase):
    def test_enc_dec(self):
        for i in xrange(10):
            self.iter_encr()

    def iter_encr(self):
        data = ''.join(random.choice(string.letters) for i in xrange(1024))
        ks = init_security_manager(CLIENT_KS_PATH, PASSWD)

        print 'Data block len: %s'%len(data)

        encrypted = ks.encrypt(data)
        print 'Encrypted data block len: %s'%len(encrypted)

        decrypted = ks.decrypt(encrypted)
        print 'Decrypted data block len: %s'%len(decrypted)

        self.assertEqual(decrypted, data)


if __name__ == '__main__':
    unittest.main()

