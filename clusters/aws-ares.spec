[clusters]
aws-ares =
    10.0.0.250:8091

[clients]
hosts = ec2-54-173-47-70.compute-1.amazonaws.com
credentials = root:couchbase

[storage]
data = /data
index = /data

[credentials]
rest = Administrator:password
ssh = root:couchbase

[parameters]
Platform = Cloud (3.2xlarge)
OS = CentOS 6.5
CPU = Intel Xeon CPU E5-2670 v2 @ 2.50GHz (x8)
Memory = 61 GB
Disk = 160GB SSD (ephemeral)
