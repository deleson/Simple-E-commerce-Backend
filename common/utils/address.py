def build_address_snapshot(address):
    return (
        f"{address.signer_name} "
        f"{address.signer_mobile} "
        f"{address.province}{address.city}{address.district} "
        f"{address.address}"
    )
