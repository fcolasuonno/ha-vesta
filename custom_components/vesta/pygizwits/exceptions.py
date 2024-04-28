import json

from aiohttp import ClientResponse


class GizwitsException(Exception):
    """An exception returned via the API."""


class GizwitsOfflineException(GizwitsException):
    """Device is offline."""


class GizwitsDeviceNotBound(GizwitsException):
    """Device is not bound to this user."""


class GizwitsAuthException(GizwitsException):
    """An authentication error."""


class GizwitsTokenInvalidException(GizwitsAuthException):
    """Auth token is invalid or expired."""


class GizwitsUserDoesNotExistException(GizwitsAuthException):
    """User does not exist."""


class GizwitsIncorrectPasswordException(GizwitsAuthException):
    """Password is incorrect."""


class ErrorCodes:
    """An exception returned via the API."""

    ERROR_CODES = {
        9004: GizwitsTokenInvalidException,
        9005: GizwitsUserDoesNotExistException,
        9042: GizwitsOfflineException,
        9020: GizwitsIncorrectPasswordException,
    }

    @classmethod
    def get_exception(cls, error_code):
        """
        Get the exception class corresponding to the given error code.

        Args:
            error_code (error_code): The error code to lookup.
        Returns:
            GizwitsException: The exception class corresponding to the given error code.
        """
        return cls.ERROR_CODES.get(error_code, GizwitsException)


async def raise_for_status(response: ClientResponse) -> None:
    """
    Handles errors in a request.

    Checks if the provided response is OK. If not, tries to decode the error message
    from the response JSON. If successful, raises an exception based on the error
    code. If the error message cannot be decoded or the error code is not recognized,
    raises an HTTPError with the status code of the response. Returns None otherwise.

    Args:
        response (ClientResponse): A ClientResponse object from an aiohttp request.
    Returns:
        None
    """
    if response.ok:
        return

    api_error = None
    try:
        api_error = await response.json()
    except json.JSONDecodeError:
        response.raise_for_status()
    error_code = api_error.get("error_code", 0) if api_error else 0
    if exception_class := ErrorCodes.get_exception(error_code):
        raise exception_class
    response.raise_for_status()
