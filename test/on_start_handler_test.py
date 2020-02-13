import json
import random
import sys
import unittest
from unittest.mock import (
    call,
    create_autospec,
)
from uuid import uuid4
import yaml

sys.path.append('lib')
from ops.framework import (
    EventBase,
)
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)

sys.path.append('src')
import handlers
from resources import OCIImageResource


class GenerateSpecHandlerTest(unittest.TestCase):

    def test_pod_spec_is_generated(self):
        # Set up
        mock_event = create_autospec(EventBase)

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

        mock_image_resource = create_autospec(OCIImageResource, spec_set=True)
        mock_image_resource.fetch.return_value = True

        # Exercise
        output = handlers.on_start(
            event=mock_event,
            app_name=mock_app_name,
            config=mock_config,
            image_resource=mock_image_resource,
            spec_is_set=False)

        # Assertions
        assert mock_image_resource.fetch.call_count == 1
        assert mock_image_resource.fetch.call_args == call()

        assert type(output.unit_status) == MaintenanceStatus
        assert output.unit_status.message == "Configuring pod"

        assert type(output.spec) == dict
        assert output.spec == {'containers': [{
            'name': mock_app_name,
            'imageDetails': {
                'imagePath': mock_image_resource.image_path,
                'username': mock_image_resource.username,
                'password': mock_image_resource.password
            },
            'ports': [{
                'containerPort': mock_config['advertised-port'],
                'protocol': 'TCP'
            }],
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

    def test_pod_spec_is_not_generated(self):
        # Set up
        mock_event = create_autospec(EventBase)

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

        mock_image_resource = create_autospec(OCIImageResource, spec_set=True)

        # Exercise
        output = handlers.on_start(
            event=mock_event,
            app_name=mock_app_name,
            config=mock_config,
            image_resource=mock_image_resource,
            spec_is_set=True)

        # Assertions
        assert mock_image_resource.fetch.call_count == 0

        assert type(output.unit_status) == ActiveStatus

        assert output.spec is None
