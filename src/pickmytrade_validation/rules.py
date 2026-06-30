from .enums import OrderType

ORDER_REQUIREMENTS = {
    OrderType.MKT.value: (),
    OrderType.LMT.value: ("price",),
    OrderType.STP.value: ("price",),
    OrderType.STPLMT.value: (
        "price",
        "stp_limit_stp_price",
    ),
}