.. image:: https://travis-ci.org/danmichaelo/wikipedia-datofeil.svg?branch=master
    :target: https://travis-ci.org/danmichaelo/wikipedia-datofeil

Bot that tries to fix `wrongly formatted dates <https://no.wikipedia.org/wiki/Kategori:Sider_med_kildemaler_som_inneholder_datofeil>`_ in citation templates at Norwegian Bokmål Wikipedia. It uses
`mwclient <https://github.com/mwclient/mwclient/>`_ with
`mwtemplates <https://github.com/danmichaelo/mwtemplates>`_ for parsing and editing the templates.

A list of changes done by the bot can be found here:

https://no.wikipedia.org/wiki/Bruker:DanmicholoBot/Datofikslogg

Install::

    virtualenv --python=/usr/bin/python3 ENV
    . ENV/bin/activate
    pip install -e .
    cp config.dist.json config.json

Crontab::

    crontab tool-labs.crontab

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
    * ``July–September 1986`` → ``juli–september 1986``
    * ``23-29. februar 2008`` → ``23.–29. februar 2008`` (manglende punktum, og bindestrek — tankestrek)
    * ``6AUG2012`` → ``6. august 2012``

