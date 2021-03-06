#!/usr/bin/python
"""
Copyright (C) 2012 Konstantin Andrusenko
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.

@package fabnet.dht_mgmt.key_utils

@author Konstantin Andrusenko
@date October 06, 2012
"""
import hashlib
from datetime import datetime

FULL_RANGE_LEN = pow(2, 160)

class KeyUtils:
    @classmethod
    def generate_new_keys(cls, node_id, replica_count, prime_key=None):
        if prime_key:
            primary_key = prime_key
        else:
            primary_key = hashlib.sha1(node_id + datetime.utcnow().isoformat()).hexdigest()

        return cls.get_all_keys(primary_key, replica_count)

    @classmethod
    def get_all_keys(cls, key, replica_count):
        keys = [key]
        r_len = FULL_RANGE_LEN / (replica_count + 1)
        key = long(key, 16)
        for i in xrange(replica_count):
            key = (key + r_len) % FULL_RANGE_LEN
            keys.append('%040x'%key)

        return keys
