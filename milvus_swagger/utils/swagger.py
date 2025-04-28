import os
import requests
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