import json
import random
import sys
import unittest
from uuid import uuid4
import yaml

sys.path.append('lib')
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)

sys.path.append('src')
import domain
from adapters.k8s import (
    PodStatus
)
from adapters.framework import (
    ImageMeta,
)


class BuildJujuPodSpecTest(unittest.TestCase):

    def test__pod_spec_is_generated(self):
        # Set up
        mock_app_name = f'{uuid4()}'

        mock_advertised_port = random.randint(1, 65535)
        mock_external_labels = {
            f"{uuid4()}": f"{uuid4()}",
            f"{uuid4()}": f"{uuid4()}",
            f"{uuid4()}": f"{uuid4()}",
        }

        mock_config = {
            'advertised-port': mock_advertised_port,
            'external-labels': json.dumps(mock_external_labels)
        }

        mock_image_meta = ImageMeta({
            'registrypath': str(uuid4()),
            'username': str(uuid4()),
            'password': str(uuid4()),
        })

        # Exercise
        juju_pod_spec = domain.build_juju_pod_spec(
            app_name=mock_app_name,
            charm_config=mock_config,
            image_meta=mock_image_meta)

        # Assertions
        assert type(juju_pod_spec) == dict
        assert juju_pod_spec == {'containers': [{
            'name': mock_app_name,
            'imageDetails': {
                'imagePath': mock_image_meta.image_path,
                'username': mock_image_meta.repo_username,
                'password': mock_image_meta.repo_password
            },
            'ports': [{
                'containerPort': mock_config['advertised-port'],
                'protocol': 'TCP'
            }],
            'readinessProbe': {
                'httpGet': {
                    'path': '/-/ready',
                    'port': mock_config['advertised-port']
                },
                'initialDelaySeconds': 10,
                'timeoutSeconds': 30
            },
            'livenessProbe': {
                'httpGet': {
                    'path': '/-/healthy',
                    'port': mock_config['advertised-port']
                },
                'initialDelaySeconds': 30,
                'timeoutSeconds': 30
            },
            'files': [{
                'name': 'config',
                'mountPath': '/etc/prometheus',
                'files': {
                    'prometheus.yml': yaml.dump({
                        'global': {
                            'scrape_interval': '15s',
                            'external_labels': mock_external_labels
                        },
                        'scrape_configs': [
                            {
                                'job_name': 'prometheus',
                                'scrape_interval': '5s',
                                'static_configs': [
                                    {
                                        'targets': [
                                            f'localhost:{mock_advertised_port}'
                                        ]
                                    }
                                ]
                            }
                        ]
                    })
                }
            }]
        }]}


class BuildJujuUnitStatusTest(unittest.TestCase):

    def test_returns_maintenance_status_if_pod_status_cannot_be_fetched(self):
        # Setup
        pod_status = PodStatus(status_dict=None)

        # Exercise
        juju_unit_status = domain.build_juju_unit_status(pod_status)

        # Assertions
        assert type(juju_unit_status) == MaintenanceStatus
        assert juju_unit_status.message == "Waiting for pod to appear"

    def test_returns_maintenance_status_if_pod_is_not_running(self):
        # Setup
        status_dict = {
            'metadata': {
                'annotations': {
                    'juju.io/unit': uuid4()
                }
            },
            'status': {
                'phase': 'Pending',
                'conditions': [{
                    'type': 'ContainersReady',
                    'status': 'False'
                }]
            }
        }
        pod_status = PodStatus(status_dict=status_dict)

        # Exercise
        juju_unit_status = domain.build_juju_unit_status(pod_status)

        # Assertions
        assert type(juju_unit_status) == MaintenanceStatus
        assert juju_unit_status.message == "Pod is starting"

    def test_returns_maintenance_status_if_pod_is_not_ready(self):
        # Setup
        status_dict = {
            'metadata': {
                'annotations': {
                    'juju.io/unit': uuid4()
                }
            },
            'status': {
                'phase': 'Running',
                'conditions': [{
                    'type': 'ContainersReady',
                    'status': 'False'
                }]
            }
        }
        pod_status = PodStatus(status_dict=status_dict)

        # Exercise
        juju_unit_status = domain.build_juju_unit_status(pod_status)

        # Assertions
        assert type(juju_unit_status) == MaintenanceStatus
        assert juju_unit_status.message == "Pod is getting ready"

    def test_returns_active_status_if_pod_is_ready(self):
        # Setup
        status_dict = {
            'metadata': {
                'annotations': {
                    'juju.io/unit': uuid4()
                }
            },
            'status': {
                'phase': 'Running',
                'conditions': [{
                    'type': 'ContainersReady',
                    'status': 'True'
                }]
            }
        }
        pod_status = PodStatus(status_dict=status_dict)

        # Exercise
        juju_unit_status = domain.build_juju_unit_status(pod_status)

        # Assertions
        assert type(juju_unit_status) == ActiveStatus