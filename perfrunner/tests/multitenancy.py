import time

import numpy as np
from logger import logger

from couchbase import Couchbase, FMT_BYTES

from perfrunner.helpers.misc import pretty_dict
from perfrunner.tests import PerfTest


class MultiTenancyTest(PerfTest):

    def report_stats(self):
        cpu = lambda data: round(np.mean(data), 1)
        rss = lambda data: int(np.mean(data) / 1024 ** 2)
        conn = lambda data: int(np.mean(data))

        for hostname, s in self.rest.get_node_stats(self.master_node,
                                                    'bucket-1'):
            summary = {
                'memcached, MBytes': rss(s['proc/memcached/mem_resident']),
                'beam.smp, MBytes': rss(s['proc/(main)beam.smp/mem_resident']),
                'Total CPU, %': cpu(s['cpu_utilization_rate']),
                'Curr. connections': conn(s['curr_connections']),
            }
            logger.info(pretty_dict({hostname: summary}))


class EmptyBucketsTest(MultiTenancyTest):

    ITERATION_DELAY = 300

    def create_buckets(self, num_buckets):
        ram_quota = self.test_config.cluster.mem_quota / num_buckets
        replica_number = self.test_config.bucket.replica_number
        replica_index = self.test_config.bucket.replica_index
        eviction_policy = self.test_config.bucket.eviction_policy
        threads_number = self.test_config.bucket.threads_number
        password = self.test_config.bucket.password

        for i in range(num_buckets):
            bucket_name = 'bucket-{}'.format(i + 1)
            self.rest.create_bucket(host_port=self.master_node,
                                    name=bucket_name,
                                    ram_quota=ram_quota,
                                    replica_number=replica_number,
                                    replica_index=replica_index,
                                    eviction_policy=eviction_policy,
                                    threads_number=threads_number,
                                    password=password)

    def delete_buckets(self, num_buckets):
        for i in range(num_buckets):
            bucket_name = 'bucket-{}'.format(i + 1)
            self.rest.delete_bucket(host_port=self.master_node,
                                    name=bucket_name)

    def run(self):
        for num_buckets in range(self.test_config.cluster.min_num_buckets,
                                 self.test_config.cluster.max_num_buckets + 1,
                                 self.test_config.cluster.incr_num_buckets):
            # Create
            self.create_buckets(num_buckets)
            self.monitor.monitor_node_health(self.master_node)
            logger.info('Sleeping {} seconds'.format(self.ITERATION_DELAY))
            time.sleep(self.ITERATION_DELAY)

            # Monitor
            self.report_stats()

            # Clean up
            self.delete_buckets(num_buckets)
            self.monitor.monitor_node_health(self.master_node)
            logger.info('Sleeping {} seconds'.format(self.ITERATION_DELAY / 2))
            time.sleep(self.ITERATION_DELAY / 2)


class MultiClientInfrequentTest(MultiTenancyTest):
    """Tests a large number of clents connecting and accessing the cluster.

    Each client only makes a small number of requests, but there is a
    large number of clients."""

    def run(self):
        # Create the bucket
        bucket_name = self.test_config.buckets[0]
        ram_quota = self.test_config.cluster.mem_quota
        replica_number = self.test_config.bucket.replica_number
        replica_index = self.test_config.bucket.replica_index
        eviction_policy = self.test_config.bucket.eviction_policy
        threads_number = self.test_config.bucket.threads_number
        password = self.test_config.bucket.password

        self.rest.delete_bucket(host_port=self.master_node,
                                name=bucket_name)

        self.rest.create_bucket(host_port=self.master_node,
                                name=bucket_name,
                                ram_quota=ram_quota,
                                replica_number=replica_number,
                                replica_index=replica_index,
                                eviction_policy=eviction_policy,
                                threads_number=threads_number,
                                password=password)
        self.wait_for_persistence()
        self.monitor.monitor_node_health(self.master_node)

        # Set document from each of the worker connections.
        conns = list()

        # Create all the connections
        for i in range(self.test_config.access_settings.workers):
            logger.info('DJR host ' + self.master_node + ' iter:' + str(i))
            conns.append(Couchbase.connect(host=self.master_node.split(':')[0],
                                           port=8091, bucket=bucket_name,
                                           password=password,
                                           timeout=30.0))

        # Perform operations on each client. Note this is serial, but given we only
        # perform a hangful of ops from each client it's probalby ok.

        # 10 MB test document.
        test_doc = bytearray(10 * 1024 * 1024)
        for c in conns:
            # set then get 10MB document.
            key = 'key-' + str(i)
            c.set(key, test_doc, format=FMT_BYTES)
            c.get(key)
            logger.info("X")

        logger.info("Completed all operations")

        # Monitor
        self.report_stats()

        # Clean up
        self.rest.delete_bucket(host_port=self.master_node,
                                name=bucket_name)
