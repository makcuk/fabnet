from aws_control import AWSControl
from fabric.api import settings, hosts, env, run, execute

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

fbn = FabnetDeploy(cluster_name = 'depl')
fbn.create('amzn-ami-pv-2012.09.0.x86_64-ebs', 1, only_regions = ['eu-     west-1'], wait_running = True, security_groups = ['deptest'])
env.hosts = fbn._get_hostlist()

def install():
    print env.hosts

#    fbn.create('amzn-ami-pv-2012.09.0.x86_64-ebs', 1, only_regions = ['eu-west-1'], wait_running = True, security_groups = ['deptest'])
    fbn.keys['eu-west-1']['key'].save("/tmp")
    with settings(remote_hosts = fbn._get_hostlist(), user = "ec2_user", key_filename = "/tmp/depl.pem"):
        run("sudo yum update")
#    fbn.teardown()

