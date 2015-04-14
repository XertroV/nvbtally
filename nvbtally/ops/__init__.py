from .create import op_create
from .empower import op_empower
from .mod_res import op_mod_res
from .cast import op_cast
from .delegate import op_delegate


op_map = {
    b'\x01': op_create,
    b'\x02': op_mod_res,
    b'\x03': op_empower,

    b'\x10': op_cast,
    b'\x11': op_delegate,
}