TYPE_CHECKING: Literal[False] = False

from typing import Tuple, Union

VERSION_TUPLE = Tuple[Union[int, str], ...]

version: str
__version__: str
__version_tuple__: VERSION_TUPLE
version_tuple: VERSION_TUPLE
__version__: Literal['1.3.1'] = '1.3.1'
version: Literal['1.3.1'] = '1.3.1'
__version_tuple__: tuple[Literal[1], Literal[3], Literal[1]]
version_tuple: tuple[Literal[1], Literal[3], Literal[1]]
