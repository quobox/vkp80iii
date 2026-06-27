from typing import Self
from _typeshed import Incomplete

import weakref


class AutoFinalizedObject(_AutoFinalizedObjectBase):
    def __new__(cls, *args: Incomplete, **kwargs: Incomplete) -> Self: ...

    def finalize(self) -> None: ...
