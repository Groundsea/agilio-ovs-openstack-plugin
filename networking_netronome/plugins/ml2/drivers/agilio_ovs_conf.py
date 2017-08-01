# Copyright (c) 2017 Netronome Systems Pty. Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from neutron_lib.api.definitions import portbindings
from oslo_config import cfg

CONF = cfg.CONF

agilio_ovs_opts = [
    cfg.StrOpt('virtio_forwarder_mode',
               default=portbindings.VHOST_USER_MODE_SERVER,
               choices=[portbindings.VHOST_USER_MODE_SERVER,
                        portbindings.VHOST_USER_MODE_CLIENT],
               help="vhost-user mode that the virtio-forwarder has been "
                    "configured with. Valid values are 'client' and "
                    "'server' with 'server' being the default."),
]


def register_agilio_ovs_opts(conf=CONF):
    conf.register_opts(agilio_ovs_opts, "AGILIO_OVS")


def list_agilio_ovs_opts():
    return [
        ('agilio_ovs', agilio_ovs_opts),
    ]
