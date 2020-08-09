import sys
import requests
from datetime import datetime, timedelta
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, session
)

from trader.auth import login_required
from trader.db import get_db

bp = Blueprint('tickers', __name__)


@bp.route('/')
def tickers():
    db = get_db()
    dt = db.execute('select distinct dtime from current limit 1').fetchone()
    dt = datetime.fromisoformat(dt[0])
    now = datetime.utcnow()
    delta = timedelta(minutes=60)

    if now - dt > delta:
        db.execute('DELETE FROM current')
        url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json'
        r = requests.get(url)
        data = r.json()['marketdata']['data']
        arr = []

        for d in data:
            arr.append((d[0], d[9], d[10], d[11], d[12], d[25], d[27]))

        db.executemany('''
        INSERT INTO current (dtime, ticker, open, low, high, last, change, vol)
        VALUES (datetime('now'),?,?,?,?,?,?,?)
        ''', arr)
        db.commit()

    data = None
    sort = None

    sort_types = {
        'ticker_asc': 'ticker asc',
        'ticker_desc': 'ticker desc',
        'change_asc': 'change asc',
        'change_desc': 'change desc',
        'volume_asc': 'vol asc',
        'volume_desc': 'vol desc'
    }
    UP = '&#8657;'
    DOWN = '&#8659;'
    sort = request.args.get('sort', None)
    if session.get('user_id', None) is not None and sort is None:
        sort = session.get('tickers_sort', None)

    if sort not in sort_types:
        data = db.execute('SELECT * FROM current').fetchall()
    else:
        data = db.execute('SELECT * FROM current order by ' +
                          sort_types[sort]).fetchall()
        if session.get('user_id', None) is not None:
            session['tickers_sort'] = sort

    return render_template('tickers/index.html', data=data, sort=sort, up=UP, down=DOWN)
