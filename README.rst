Bot som korrigerer feilformaterte og/eller uoversatte datoer på Wikipedia på bokmål.

En liste over endringer utført av boten finnes her:

https://no.wikipedia.org/wiki/Bruker:DanmicholoBot/Datofikslogg

Install::

    pip install -r requirements.txt
    cp config.dist.json config.json

Add your Wikimedia credentials to `config.json` and run `python run.py`

Run tests::

    py.test
