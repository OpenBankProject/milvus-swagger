import pytest
import json

from ..utils.swagger import check_against_cache

@pytest.fixture
def create_cache_dir(tmp_path):
    """
    Fixture to create a temporary cache directory for testing.
    """
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    yield cache_dir
    # Cleanup is handled by pytest's tmp_path fixture


def test_matching_cache(create_cache_dir):
    """
    Test that the function returns True when the cached spec matches the current spec.
    """

    # Mock the swagger_spec_dict and cached_spec_path
    swagger_spec_dict = {
        "paths": {
            "/api/v1/resource": {
                "get": {
                    "operationId": "getResource"
                }
            }
        }
    }
    
    cached_spec_path = create_cache_dir / "swagger_cache.json"
    
    # Create a mock cached spec file
    with open(cached_spec_path, 'w') as f:
        json.dump(swagger_spec_dict, f)
    
    # Call the function
    result = check_against_cache(swagger_spec_dict, cached_spec_path)
    
    # Assert that the result is True
    assert result == True



def test_non_matching_cache(create_cache_dir):
    """
    Test that the function returns False when the cached spec does not match the current spec.
    """

    # Mock the swagger_spec_dict and cached_spec_path
    swagger_spec_dict = {
        "paths": {
            "/api/v1/resource": {
                "get": {
                    "operationId": "getResource"
                }
            }
        }
    }
    cached_spec_path = create_cache_dir / "swagger_cache.json"
    # Create a mock cached spec file with different content
    with open(cached_spec_path, 'w') as f:
        json.dump({"paths": {}}, f)
    # Call the function
    result = check_against_cache(swagger_spec_dict, cached_spec_path)
    # Assert that the result is False
    assert result == False



def test_cache_file_not_found(create_cache_dir):
    """
    Test that the function raises a ValueError when the cached spec file is not found.
    """

    # Mock the swagger_spec_dict and a non-existent cached_spec_path
    swagger_spec_dict = {
        "paths": {
            "/api/v1/resource": {
                "get": {
                    "operationId": "getResource"
                }
            }
        }
    }
    cached_spec_path = create_cache_dir / "non_existent_cache.json"
    # Call the function and assert that it raises a ValueError
    with pytest.raises(ValueError) as excinfo:
        check_against_cache(swagger_spec_dict, cached_spec_path)
    assert str(excinfo.value) == f"Cached spec file not found at {cached_spec_path}"    