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

from neutron_lib.api.definitions import portbindings

from neutron.plugins.ml2.drivers.openvswitch.mech_driver \
    import mech_openvswitch


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
        # (jangutter): Something like the following could possibly be used
        # to allow Nova to set the bridge_name without extending the
        # the neutron api code:
        # self.vif_details[portbindings.VHOST_USER_OVS_PLUG] = True
        self.vif_type = 'agilio_ovs'
