import utils.router_constants as c


def get_page_header(page):
    payload = {
        "erectDate": "",
        "nothing": "",
        "pjname": "美元",
        "page": page,
        "head": "head_620.js",
        "bottom": "bottom_591.js"
    }

    if page == 0:
        return c.currency_usd_payload_data
    else:
        return payload


if __name__ == '__main__':
    pass
