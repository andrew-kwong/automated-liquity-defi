from decimal import Decimal


class BaseError(Exception):
    """Base class for other errors thrown by this library.

    Allows catching only errors of this library.
    """

    pass


class TooManyDecimalsError(ValueError, BaseError):
    """Raised when a function input value has more decimals than the contract allows.

    Usually this means we are deserializing a monetary value with the wrong contract."""

    def __init__(
        self, decimal: Decimal, expected_max_decimals: int, *args: object
    ) -> None:
        super().__init__(*args)
        self.decimal = decimal
        self.expected_max_decimals = expected_max_decimals

    def __str__(self):
        return f"{self.decimal!r} has more than the expected {self.expected_max_decimals} decimals"


class PipelineDefinitionError(ValueError, BaseError):
    pass


class InvalidReferenceError(PipelineDefinitionError):
    """Raised when a step reference state value that does not exist."""

    def __init__(self, step_slug: str, key: str, *args: object) -> None:
        super().__init__(*args)
        self.step_slug = step_slug
        self.key = key

    def __str__(self):
        return (
            f"Step '{self.step_slug}' requires value under key '{self.key}' from state."
        )


class InvalidFormalParamTypeError(PipelineDefinitionError):
    """Raised when a fixed step parameter has an invalid type."""

    def __init__(self, step_slug: str, name: str, value, *args: object) -> None:
        super().__init__(*args)
        self.step_slug = step_slug
        self.name = name
        self.value = type(value)

    def __str__(self):
        return f"Step '{self.step_slug}' received parameter '{self.name}' set to unexpected type '{self.value!r}'"


class InvalidFormalParamError(PipelineDefinitionError):
    """Raised when a fixed step parameter has an invalid value."""

    def __init__(self, step_slug: str, name: str, value, *args: object) -> None:
        super().__init__(*args)
        self.step_slug = step_slug
        self.name = name
        self.value = value

    def __str__(self):
        return f"Step '{self.step_slug}' received parameter '{self.name}' set to invalid value '{self.value!r}'"


class InvalidChainEffectError(PipelineDefinitionError):
    """Raised when a step has a side effect on the chain in a place of the pipeline where it shouldn't, like a `given` clause."""

    def __init__(self, step_slug: str, *args: object, caller: str = None) -> None:
        super().__init__(*args)
        self.step_slug = step_slug
        self.caller = caller

    def __str__(self):
        return f"Step '{self.step_slug}' has a reported to have a side effect on the chain but it shouldn't produce side effects from {self.caller or 'where it was called'}."


class PipelineExecutionError(ValueError, BaseError):
    pass


class UnmetPreconditionError(PipelineExecutionError):
    """Raised when a precondition for a step's successful execution is not met."""

    def __init__(self, step_slug: str, msg: str, *args: object) -> None:
        super().__init__(*args)
        self.step_slug = step_slug
        self.msg = msg

    def __str__(self):
        return f"Step '{self.step_slug}' has an unmet precondition: {self.msg}"


class MissingParamError(PipelineExecutionError):
    """Raised when a step does not get all required parameters that have no default as fallback."""

    def __init__(self, step_slug: str, param_key: str, *args: object) -> None:
        super().__init__(*args)
        self.step_slug = step_slug
        self.param_key = param_key

    def __str__(self):
        return f"Step '{self.step_slug}' did not receive the required user parameter with key '{self.param_key}' and it has no default as fallback."


class InvalidParamTypeError(PipelineExecutionError):
    """Raised when a step gets an actual parameter of an invalid type."""

    def __init__(self, step_slug: str, name: str, value, *args: object) -> None:
        super().__init__(*args)
        self.step_slug = step_slug
        self.name = name
        self.value = type(value)

    def __str__(self):
        return f"Step '{self.step_slug}' received parameter '{self.name}' set to unexpected type '{self.value!r}'"


class APIError(PipelineExecutionError):
    """Raised when an helper API returns an error."""

    def __init__(self, status: int, msg: str, *args: object) -> None:
        super().__init__(*args)
        self.status = status
        self.msg = msg

    def __str__(self):
        return f"Got status {self.status}: {self.msg}"
