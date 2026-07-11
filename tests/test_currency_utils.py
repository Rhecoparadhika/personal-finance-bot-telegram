from app.utils.currency import format_currency, normalize_amount_text


def test_normalize_ribu_shorthand():
    assert normalize_amount_text("Makan bakso 25rb") == "Makan bakso 25000"


def test_normalize_ribu_word():
    assert normalize_amount_text("Isi bensin 100 ribu") == "Isi bensin 100000"


def test_normalize_juta_word():
    assert normalize_amount_text("Gajian 15 juta") == "Gajian 15000000"


def test_normalize_juta_shorthand():
    assert normalize_amount_text("Transfer 5jt") == "Transfer 5000000"


def test_normalize_leaves_plain_numbers_alone():
    assert normalize_amount_text("Beli saham BBCA 5 lot") == "Beli saham BBCA 5 lot"


def test_format_currency_idr():
    assert format_currency(25000) == "Rp25.000"


def test_format_currency_other():
    assert format_currency(19.99, "USD") == "19.99 USD"
