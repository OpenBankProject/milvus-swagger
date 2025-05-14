import pytest
import os
import json
import shutil

from ..utils.swagger import cache_swagger

def test_creates_custom_cache_dir_if_does_not_exist():
    """
    Test that the cache directory is created if it does not exist.
    """
    # Arrange
    swagger_spec_dict = {
        "swagger": "2.0",
        "info": {
            "title": "Test API",
            "version": "1.0"
        },
        "paths": {}
    }

    cache_dir = ".custom-cache/"

    # Act
    cache_file = cache_swagger(swagger_spec_dict, cache_dir)

    # Assert
    assert os.path.exists(cache_dir)
    assert os.path.exists(cache_file)

    # Cleanup
    shutil.rmtree(cache_dir)


def test_creates_default_cache_dir_if_does_not_exist():
    """
    Test that the cache directory is created if it does not exist.
    """
    # Arrange
    swagger_spec_dict = {
        "swagger": "2.0",
        "info": {
            "title": "Test API",
            "version": "1.0"
        },
        "paths": {}
    }

    default_cache_dir = ".cache/"
    # Act
    cache_file = cache_swagger(swagger_spec_dict)

    # Assert
    assert os.path.exists(default_cache_dir)
    assert os.path.exists(cache_file)

    # Cleanup
    shutil.rmtree(default_cache_dir)


def test_creates_cache_file(tmp_path):
    """
    Test that the cache file is created.
    """
    # Arrange
    swagger_spec_dict = {
        "swagger": "2.0",
        "info": {
            "title": "Test API",
            "version": "1.0"
        },
        "paths": {}
    }

    # Act
    cache_file = cache_swagger(swagger_spec_dict, tmp_path)

    # Assert
    assert os.path.exists(cache_file)

    # Cleanup
    shutil.rmtree(tmp_path)


def test_cache_file_contains_swagger_spec(tmp_path):
    """
    Test that the cache file contains the correct swagger spec.
    """
    # Arrange
    swagger_spec_dict = {
        "swagger": "2.0",
        "info": {
            "title": "Test API",
            "version": "1.0"
        },
        "paths": {}
    }

    # Act
    cache_file = cache_swagger(swagger_spec_dict, tmp_path)

    # Assert
    with open(cache_file, 'r') as f:
        cached_spec = json.load(f)
    
    assert cached_spec == swagger_spec_dict

    # Cleanup
    shutil.rmtree(tmp_path)