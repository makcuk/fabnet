from aws_control import AWSControl
from fabric.api import settings, hosts, env, run, execute, task
import os.path
from os import remove
import pickle

TMPDIR="/tmp" #FIXME: add here mkstemp

class FabnetDeploy(AWSControl):
#    def __init__(self, cluster_name = ""):
#        self.node_set = {u'eu-west-1': [{'moretest000': u'ec2-46-137-135-252.eu-west-1.compute.amazonaws.com'}, {'moretest001': u'ec2-54-246-34-251.eu-west-1.compute.amazonaws.com'}, {'moretest002': u'ec2-176-34-67-244.eu-west-1.compute.amazonaws.com'}]}

    def _get_hostlist(self):
        hostlist = list()
        for region in self.node_set:
            for node in self.node_set[region]:
                for h, n in node.items():
                    hostlist.append(n)
        return hostlist

#    def _get_key_by_hostname(self, hostname):
#        for 
    def deploy(self):
        self.install()
@task
def configure():
    fbn.create('amzn-ami-pv-2012.09.0.x86_64-ebs', 3, only_regions = ['eu-west-1'], wait_running = True, security_groups = ['deptest'])
    env.hosts = fbn._get_hostlist()
    if not os.path.isfile('/tmp/'+fbn.keys['eu-west-1']['name']+'.pem'):
        fbn.keys['eu-west-1']['key'].save("/tmp")


# main
fbn = FabnetDeploy(cluster_name = 'depl')
metaenv = env
metaenv.connection_attempts = 20
metaenv.timeout = 30
metaenv.user = "ec2-user"
metaenv.parallel = True
metaenv.key_filename = TMPDIR+"/"+fbn.cluster_name+".pem"
metaenv.skip_bad_hosts = True

@task
def update_os():
    env = metaenv
    run("uname -a")

@task
def install():
    print env
    env = metaenv
    print env
    update_os()

@task
@hosts('')
def teardown():
    metaenv.hosts = None
    env = metaenv
    fbn.teardown()
    print "preved"
    remove(metaenv.key_filename)

