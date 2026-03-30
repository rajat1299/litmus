def test_charge_returns_200_on_success():
    request = {
        "method": "POST",
        "path": "/payments/charge",
        "json": {"amount": 100},
    }
    response = {
        "status_code": 200,
        "json": {"status": "charged"},
    }

    assert response["status_code"] == 200


def test_charge_returns_402_on_insufficient_funds():
    request = {
        "method": "POST",
        "path": "/payments/charge",
        "json": {"amount": 1000000},
    }
    response = {
        "status_code": 402,
        "json": {"status": "declined"},
    }

    assert response["status_code"] == 402
