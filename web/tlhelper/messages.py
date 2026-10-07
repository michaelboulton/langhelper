"""A text for the user that the page can show in another language.

Python writes the English sentence, and names the message of the catalogs
(languages/*/ui.ftl) with its parameters. The page formats that message in the
language of the user, and shows the English sentence if the catalog has no
such message. A parameter is a raw value ("Loc", and not "locative"): the
catalog has the words.
"""

from fastapi import HTTPException

Params = dict[str, str | int | list[str]]


class Problem(str):
    """The English sentence of a failed check: a str, so the checks and their
    tests read it as before. `key` and `params` are the message
    ("problem-repeat", {"words": "je je"}). schemas.Word gives them to the
    page as problem_messages."""

    key: str
    params: Params

    def __new__(cls, key: str, text: str, **params: str | int | list[str]):
        problem = super().__new__(cls, text)
        problem.key = key
        problem.params = params
        return problem


class CodedError(Exception):
    """An error for the page. str() is the English sentence. With a code, the
    catalogs have the message "error-{code}"."""

    def __init__(self, text: str, code: str = "", **params: str | int):
        super().__init__(text)
        self.code = code
        self.params = params


class CodedHTTPException(HTTPException):
    """An HTTPException with `code` and `params` next to `detail` in its JSON
    (the handler is in app.py)."""

    def __init__(self, status_code: int, code: str, detail: str, **params: str | int):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code
        self.params = params


def coded_http(status_code: int, error: Exception) -> HTTPException:
    """The HTTP error for an exception: with the code of a CodedError."""
    code = getattr(error, "code", "")
    if not code:
        return HTTPException(status_code=status_code, detail=str(error))
    return CodedHTTPException(status_code, code, str(error), **error.params)
