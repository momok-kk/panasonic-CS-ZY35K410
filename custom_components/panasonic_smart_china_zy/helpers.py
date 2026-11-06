"""Small shared helpers for status-bean parsing."""

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, SUCCESS_ERROR_CODES


def device_info(device, name):
    """Group every entity of one AC under a single HA device."""
    return DeviceInfo(
        identifiers={(DOMAIN, device.device_id)},
        name=name,
        manufacturer="Panasonic",
        model=device.model,
    )


def as_int(value, default=None):
    """Coerce a protocol value (str/int/None) to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def business_error_code(data):
    """Return the business error code from either response shape.

    The cloud uses a top-level ``errorCode`` for some endpoints and a nested
    ``{"error": {"code": 4102, "message": "认证错误"}}`` object for others.
    ``None`` (or one of SUCCESS_ERROR_CODES) means success.
    """
    if not isinstance(data, dict):
        return None
    nested = data.get("error")
    nested = nested if isinstance(nested, dict) else {}
    code = data.get("errorCode", nested.get("code"))
    if code in SUCCESS_ERROR_CODES:
        code = nested.get("code")
    return code


def error_message(data):
    """Best-effort human-readable error message from a response dict."""
    if not isinstance(data, dict):
        return "Panasonic API error"
    nested = data.get("error")
    nested = nested if isinstance(nested, dict) else {}
    return (
        data.get("errorMessage")
        or data.get("msg")
        or nested.get("message")
        or "Panasonic API error"
    )


def capability_ok(params, capability):
    """Official AirconCommon "*Ex" gate; unknown capability means no gate."""
    if not capability:
        return True
    if not params:
        return False
    return as_int(params.get(capability)) == 1


def resolve_key(params, key, aliases=()):
    """Pick the first key actually present in the status bean."""
    for candidate in (key, *aliases):
        if candidate in params:
            return candidate
    return key


def sum_array(value):
    """Sum a numeric list returned by a monthly/yearly graph endpoint."""
    if not isinstance(value, list):
        return None
    total = 0.0
    for item in value:
        try:
            total += float(item)
        except (TypeError, ValueError):
            return None
    return round(total, 3)
