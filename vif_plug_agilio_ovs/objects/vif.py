# Derived from os-vif/os_vif/objects/vif.py

# Copyright (c) 2017 Netronome Systems Pty. Ltd.
# Copyright (c) 2013 OpenStack Foundation
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

from oslo_versionedobjects import base

from os_vif.objects.vif import VIFDirect
from os_vif.objects.vif import VIFOpenVSwitch
from os_vif.objects.vif import VIFVHostUser


@base.VersionedObjectRegistry.register
class VIFAgilioOpenVSwitch(VIFOpenVSwitch,
                           VIFDirect,
                           VIFVHostUser):
    # For libvirt drivers, this also maps to type='agilio_ovs'

    VERSION = '1.0'
