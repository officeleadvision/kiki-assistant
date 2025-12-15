from urllib.parse import quote


def include_user_info_headers(headers, user):
    return {
        **headers,
        "X-Lead Me-User-Name": quote(user.name, safe=" "),
        "X-Lead Me-User-Id": user.id,
        "X-Lead Me-User-Email": user.email,
        "X-Lead Me-User-Role": user.role,
    }
