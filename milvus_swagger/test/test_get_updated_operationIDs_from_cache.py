import pytest
import json
from ..utils.swagger import get_updated_operationIDs_from_cache


# Test cases for identifying updated operations between swagger specs and cached specs
swagger_spec_test_data = [
    # Test case 1: Operation with changed description but same operationId
    ({
        "swagger": "2.0",
        "info": {
            "title": "Test API",
            "version": "1.0"
        },
        "paths": {
            "/test": {
                "get": {
                    "operationId": "getTest",
                    "description": "Test description"
                }
            }
        }
    }, {
        "swagger": "2.0",
        "info": {
            "title": "Test API",
            "version": "1.0"
        },
        "paths": {
            "/test": {
                "get": {
                    "operationId": "getTest",
                    "description": "Cached description"
                }
            }
        }
    }, ["getTest"]),

    # Test case 2: New operation added that wasn't in the cached spec
    ({
        "swagger": "2.0",
        "info": {
            "title": "Test API",
            "version": "1.0"
        },
        "paths": {
            "/test": {
                "get": {
                    "operationId": "getTest",
                    "description": "Get method"
                },
                "post": {
                    "operationId": "createTest",
                    "description": "Create method"
                }
            }
        }
    }, {
        "swagger": "2.0",
        "info": {
            "title": "Test API",
            "version": "1.0"
        },
        "paths": {
            "/test": {
                "get": {
                    "operationId": "getTest",
                    "description": "Get method"
                }
            }
        }
    }, ["createTest"]),

    # Test case 3: Empty paths in both specs, expecting no updates
    ({
        "swagger": "2.0",
        "info": {
            "title": "Test API",
            "version": "1.0"
        },
        "paths": {}
    }, {}, []),

]

@pytest.mark.parametrize("swagger_spec_dict, cached_spec_dict, expected_operation_ids", swagger_spec_test_data)
def test_get_updated_operationIDs_from_cache(swagger_spec_dict, cached_spec_dict, expected_operation_ids, tmp_path):
    """
    Test that the function correctly identifies updated operation IDs from the cache.
    """
    

    cached_spec_path = tmp_path / "cached_spec.json"
    with open(cached_spec_path, 'w') as f:
        json.dump(cached_spec_dict, f)

    # Act
    updated_operation_ids = get_updated_operationIDs_from_cache(swagger_spec_dict, cached_spec_path)

    # Assert
    assert updated_operation_ids == expected_operation_ids
