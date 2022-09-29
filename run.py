from btcbyme import create_app
from btcbyme.utilities import secrets

app = create_app()


@app.template_global()
def get_btcpay_server_domain():
    return secrets.BTCPAY_SERVER_DOMAIN


if __name__ == '__main__':
    app.run(debug=True)
