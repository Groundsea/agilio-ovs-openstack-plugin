# Derived from ml2/drivers/openvswitch/mech_driver/mech_openvswitch.py

# Copyright (c) 2017 Netronome Systems Pty. Ltd.
# Copyright (c) 2013 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from neutron.plugins.ml2.drivers.openvswitch.mech_driver \
    import mech_openvswitch
from neutron_lib.api.definitions import portbindings
from neutron_lib.api.definitions.portbindings import VNIC_TYPE
from neutron_lib.api.definitions.portbindings import VNIC_VIRTIO_FORWARDER
from oslo_config import cfg

from networking_netronome.plugins.ml2.drivers import agilio_ovs_conf


CONF = cfg.CONF

agilio_ovs_conf.register_agilio_ovs_opts()
CONF.import_group('AGILIO_OVS',
                  'networking_netronome.plugins.ml2.drivers.agilio_ovs_conf')


class AgilioOvsMechanismDriver(mech_openvswitch.OpenvswitchMechanismDriver):
    """Extend the Openvswitch Mechanism Driver to support Agilio OVS NICs

    This mechanism driver introduces extended functionality into the
    Openvswitch driver in order to support accelerated SR-IOV and
    vhost-user VNIC types.
    """

    def __init__(self):
        super(AgilioOvsMechanismDriver, self).__init__()
        self.supported_vnic_types += [portbindings.VNIC_DIRECT,
                                      portbindings.VNIC_VIRTIO_FORWARDER]
        self.vif_type = 'agilio_ovs'

    def _get_vhost_mode_for_hypervisor(self):
        # This function returns the vhost mode for the hypervisor.
        # If virtio-forwarder is set to client, the hypervisor must be
        # server, and vice versa.
        if cfg.CONF.AGILIO_OVS.virtio_forwarder_mode == \
           portbindings.VHOST_USER_MODE_CLIENT:
            return portbindings.VHOST_USER_MODE_SERVER
        return portbindings.VHOST_USER_MODE_CLIENT

    def _pre_get_vif_details(self, agent, context):
        vif_details = super(
            AgilioOvsMechanismDriver,
            self)._pre_get_vif_details(agent, context)
        if context.current[VNIC_TYPE] == VNIC_VIRTIO_FORWARDER:
            sock_path = self.agent_vhu_sockpath(agent, context.current['id'])
            vif_details[portbindings.VHOST_USER_SOCKET] = sock_path
            vif_details[portbindings.VHOST_USER_MODE] = \
                self._get_vhost_mode_for_hypervisor()
            vif_details[portbindings.VHOST_USER_OVS_PLUG] = True
        return vif_details
