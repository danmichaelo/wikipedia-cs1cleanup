Bot som korrigerer feilformaterte og/eller uoversatte datoer på Wikipedia på bokmål.

En liste over endringer utført av boten finnes her:

https://no.wikipedia.org/wiki/Bruker:DanmicholoBot/Datofikslogg

Install::

    pip install -r requirements.txt
    cp config.dist.json config.json

Add your Wikimedia credentials to ``config.json`` and run ``python run.py``

Run tests::

    py.test

Examples:

    * ``[[30.8.09]]`` → ``30.8.2009``
    * ``dato=28.mai``, ``år=2009`` → ``dato=28. mai 2009``
    * ``Januari 2, 2009`` → ``dato=2. januar 2009``
    * ``2. sep 2009]`` → ``dato=2. september 2009``
    * ``7-2-2008`` → ``7.2.2008``
    * ``15, marts 2010`` → ``15. mars 2010``
