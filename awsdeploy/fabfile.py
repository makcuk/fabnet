from aws_control import AWSControl
from fabric.api import settings, hosts, env, run, execute, task, sudo, prefix, cd
import os.path
from os import remove
import pickle
import time

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
    fake_hosts = env.hosts
    if not os.path.isfile('/tmp/'+fbn.keys['eu-west-1']['name']+'.pem'):
        fbn.keys['eu-west-1']['key'].save("/tmp")


# main
fbn = FabnetDeploy(cluster_name = 'depl')
metaenv = env
metaenv.connection_attempts = 20
metaenv.timeout = 30
metaenv.user = "ec2-user"
metaenv.parallel = False
metaenv.key_filename = TMPDIR+"/"+fbn.cluster_name+".pem"
metaenv.skip_bad_hosts = True
#fake_hosts = ['ec2-54-247-56-243.eu-west-1.compute.amazonaws.com','ec2-176-34-76-236.eu-west-1.compute.amazonaws.com','ec2-54-246-6-59.eu-west-1.compute.amazonaws.com']
fake_hosts = []
first_node = ''

@task
def install():
    print env.hosts
    if sudo('yum --assumeyes install git'):
        run("rm -rf ~/fabnet_node ~/fabnet_node_home")
        run('wget http://repo.idepositbox.com:8080/repos/install_fabnet_node.sh')
        run('chmod +x ./install_fabnet_node.sh')
        run('./install_fabnet_node.sh')
@task
@hosts('')
def start():
    execute(restore('normal'))
    execute(install())
    execute(restore('first'))
    execute(run_first_node)
    execute(restore('next'))
    execute(run_next_nodes(env.first_node))
    for _ in xrange(50): print "=",
    print
    for node in metaenv.hosts:
        print node
    print "First node" + env.first_node

@task
def run_first_node():
    print "ENVTASK", env.hosts
    env.first_node = env.hosts[0]
    with prefix('export FABNET_NODE_HOST='+str(env.host)):
        run('cd ~/fabnet_node;nohup ./fabnet/bin/node-daemon start init-fabnet depl000 DHT')

@task
def run_next_nodes(first_node):
    print "ENVTASK", env.hosts
    env.hosts = metaenv.hosts[1:]
    with prefix('export FABNET_NODE_HOST='+str(env.host)):
        run('cd ~/fabnet_node; nohup ./fabnet/bin/node-daemon start '+first_node+' depl001 DHT')

@task
@hosts('')
def restore(mode):
    fbn.restore()
    hosts = fbn._get_hostlist()
    if mode == 'first':
        hosts = [hosts[0]]
    elif mode == 'next':
        hosts = hosts[1:]
    env.hosts = hosts

    print "ENV", env.hosts

@task
def kill_after_fail():
    fbn.restore()
    metaenv.hosts = fbn._get_hostlist()
    env = metaenv
    print "ENV", env.hosts
    execute(teardown)

@task
@hosts('')
def teardown():
    metaenv.hosts = None
    env = metaenv
    fbn.teardown()
    if os.path.isfile(metaenv.key_filename):
        remove(metaenv.key_filename)

