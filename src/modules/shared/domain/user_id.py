from typing import Annotated

from pydantic import StringConstraints

UserId = Annotated[str, StringConstraints(min_length=1, max_length=128)]
