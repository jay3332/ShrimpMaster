import platform


def route(*destinations):
    base = "/".join(destinations)

    _sys = platform.system()
    if _sys == "Windows":
        # It's in PyCharm
        return './'+base
    return './ShrimpMaster/'+base
