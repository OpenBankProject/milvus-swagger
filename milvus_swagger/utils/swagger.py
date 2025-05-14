import os
import requests
import json

from openapi_spec_validator import OpenAPIV2SpecValidator, validate
from prance import ResolvingParser

def get_swagger(url: str): 
    """
    Retrieve a Swagger/OpenAPI specification from a given URL.
    This function makes an HTTP GET request to the specified URL, expecting to
    receive a Swagger/OpenAPI JSON document in response. If the request fails
    or returns a non-200 status code, detailed error information is printed to
    the console.
    Args:
        url (str): The URL from which to retrieve the Swagger specification.
    Returns:
        dict: The parsed Swagger specification as a Python dictionary if successful,
              or None if the request fails or returns a non-200 status code.
    Raises:
        No exceptions are raised as they are caught and printed internally.
    """
    print(f"Fetching swagger from {url}")
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException as e:
        print(e)
        return None
    
    if response.status_code != 200:
        print(f"Failed to get swagger from {url}")
        print(f"Response status code: {response.status_code}")
        print(f"Response text: {response.text}")
        return None
    
    return response.json()

def validate_swagger(url: str):
    """
    This function validates a Swagger specification retrieved from a given URL.

    Parameters:
        url (str): The base URL to retrieve the Swagger specification.

    Returns:
        bool: True if the Swagger specification is valid, False otherwise.

    Raises:
        ValueError: If the Swagger specification cannot be retrieved.
    """
    swagger = get_swagger(url)

    if swagger is None:
        raise ValueError("Failed to get swagger from the specified URL.")

    try:
        validate(swagger, cls=OpenAPIV2SpecValidator)
        return True
    except Exception as e:
        print("Swagger validation failed.")
        print(e)
        return False


def recursion_handler(recursion_limit, parsed_url, refs):
    print(recursion_limit, parsed_url, refs)
    return {'$ref': '#'+parsed_url.fragment}


def resolve_swagger(url: str):

    if validate_swagger(url):
        print("Swagger is valid, resolving...")
        try:
            parser = ResolvingParser(url, recursion_limit_handler=recursion_handler)
        except Exception as e:
            print("Error resolving swagger:", e)
            return None
        swagger_dict = parser.specification
        print("Swagger resolved successfully.")
        return swagger_dict
    
    else:
        print("Swagger is not valid, cannot resolve.")
        return None
    

def cache_swagger(swagger_spec_dict: dict, cache_dir: str = ".cache/"):
    """
    This function caches a Swagger specification to a local file.

    Parameters:
        swagger_dict (dict): The Swagger specification to cache.
        cache_dir (str): The directory where the cached file will be saved.

    Returns:
        str: The path to the cached file.
    """
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    cache_file = os.path.join(cache_dir, "swagger_cache.json")
    
    with open(cache_file, 'w') as f:
        json.dump(swagger_spec_dict, f)

    return cache_file


def check_against_cache(swagger_spec_dict: dict, cached_spec_path: str):
    """
    This function checks if a cached Swagger specification matches the given one.

    Parameters:
        swagger_dict (dict): The Swagger specification to check.
        cached_spec_path (str): The path to the cached Swagger specification.

    Returns:
        bool: True if the cached specification matches the given one, False otherwise.
    """
    if not os.path.exists(cached_spec_path):
        raise ValueError(f"Cached spec file not found at {cached_spec_path}")

    with open(cached_spec_path, 'r') as f:
        cached_spec = json.load(f)

    return swagger_spec_dict == cached_spec


def get_updated_operationIDs_from_cache(swagger_spec_dict: dict, cached_spec_path: str):
    """
    This function compares a Swagger specification with a cached version and returns the operation IDs that need to be updated.
    It checks each path and method in the Swagger specification against the cached specification,

    Parameters:
        swagger_dict (dict): The Swagger specification to compare.
        cached_spec_path (str): The path to the cached Swagger specification.

    Returns:
        List[str]: A list of updated operation IDs.
    """
    if not os.path.exists(cached_spec_path):
        raise ValueError(f"Cached spec file not found at {cached_spec_path}")

    with open(cached_spec_path, 'r') as f:
        cached_spec = json.load(f)

    updated_operationIDs = []
    for path, methods in swagger_spec_dict["paths"].items():

        # If path does not exist, all methods are new
        if path not in cached_spec["paths"]:
            for method, properties in methods.items():
                operationID = properties.get("operationId")
                if operationID:
                    updated_operationIDs.append(operationID)

        else:
            # If path exists, check each method
            for method, properties in methods.items():
                operationID = properties.get("operationId")
                # If method does not exist, it's a new method
                if method not in cached_spec["paths"][path]:
                    if operationID:
                        updated_operationIDs.append(operationID)
                    continue

                if properties != cached_spec["paths"][path][method]:
                    # If properties are different, check operationId
                    if operationID and operationID not in updated_operationIDs:
                        updated_operationIDs.append(operationID)

    print("Updated operation IDs after checking incoming spec:", updated_operationIDs)

    # Check for removed operation IDs
    for path, methods in cached_spec["paths"].items():
        # If path does not exist, all methods are removed
        if path not in swagger_spec_dict["paths"]:
            for method, properties in methods.items():
                operationID = properties.get("operationId")
                if operationID and operationID not in updated_operationIDs:
                    updated_operationIDs.append(operationID)
        else:
            # If path exists, check each method
            for method, properties in methods.items():
                operationID = properties.get("operationId")
                # If method does not exist, it's a removed method
                if method not in swagger_spec_dict["paths"][path]:
                    if operationID and operationID not in updated_operationIDs:
                        updated_operationIDs.append(operationID)
                else:
                    # If properties are different, check operationId
                    if properties != swagger_spec_dict["paths"][path][method]:
                        if operationID and operationID not in updated_operationIDs:
                            updated_operationIDs.append(operationID)
                    

    print("Updated operation IDs after checking deletions:", updated_operationIDs)

    return updated_operationIDs