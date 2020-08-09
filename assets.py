from flask import (
    Blueprint, g, flash, request, redirect, render_template, url_for, session
)

from werkzeug.exceptions import abort

from trader.db import get_db
from trader.auth import login_required

bp = Blueprint('assets', __name__, url_prefix='/assets')


@ bp.route('/')
@ login_required
def assets():
    data = None
    sort = None
    db = get_db()

    sort_types = {
        'ticker_asc': 'ticker asc',
        'ticker_desc': 'ticker desc',
        'change_asc': 'change asc',
        'change_desc': 'change desc',
        'total_asc': '(b.last - a.price) * a.count asc',
        'total_desc': '(b.last - a.price) * a.count desc'
    }
    UP = '&#8657;'
    DOWN = '&#8659;'
    sort = request.args.get('sort', None)
    if session.get('user_id', None) is not None and sort is None:
        sort = session.get('assets_sort', None)

    if sort not in sort_types:
        data = db.execute(
            '''select a.*, b.last, (b.last - a.price) * 100 / a.price as change,
            (b.last - a.price) * a.count as total 
            from asset a left join current b on a.ticker = b.ticker where user_id = ?
            ''',
            (g.user['id'],)
        ).fetchall()
    else:
        data = db.execute(
            '''select a.*, b.last, (b.last - a.price) * 100 / a.price as change,
            (b.last - a.price) * a.count as total 
            from asset a left join current b on a.ticker = b.ticker where user_id = ?
            order by 
            ''' + sort_types[sort],
            (g.user['id'],)
        ).fetchall()

        if session.get('user_id', None) is not None:
            session['assets_sort'] = sort
    return render_template('assets/assets.html', data=data, sort=sort, up=UP, down=DOWN)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    db = get_db()
    error = None
    if request.method == 'POST':
        ticker = request.form['ticker']
        count = request.form['count']
        price = request.form['price']

        if not ticker:
            error = 'Ticker required.'
        elif not count:
            error = 'Count required.'
        elif not price:
            error = 'Price required.'

        if error is None:
            db.execute(
                'insert into asset (ticker, price, count, user_id) values(?, ?, ?, ?)',
                (ticker, price, count, g.user['id'])
            )
            db.commit()
            return redirect(url_for('assets.assets'))

        if error is not None:
            flash(error)

    ticker = request.args.get('ticker', None)
    data = db.execute('select distinct ticker from current').fetchall()
    return render_template('assets/asset.html', data=data, ticker=ticker)


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    db = get_db()
    error = None
    asset = db.execute('select * from asset where id = ?', (id,)).fetchone()
    if asset is None:
        abort(404, 'Asset id {} does not exist'.format(id))
    if asset['user_id'] != g.user['id']:
        abort(403)

    if request.method == 'POST':
        ticker = request.form['ticker']
        count = request.form['count']
        price = request.form['price']

        if not ticker:
            error = 'Ticker required.'
        elif not count:
            error = 'Count required.'
        elif not price:
            error = 'Price required.'

        if error is not None:
            flash(error)
        else:
            db.execute(
                'update asset set ticker = ?, price = ?, count = ? where id = ?',
                (ticker, price, count, id)
            )
            db.commit()
            return redirect(url_for('assets.assets'))

    data = db.execute('select distinct ticker from current').fetchall()
    return render_template('assets/asset.html', data=data, asset=asset)


@ bp.route('/<int:id>/delete')
@ login_required
def delete(id):
    db = get_db()
    asset = db.execute('select * from asset where id = ?', (id,)).fetchone()
    if not asset:
        abort(404)
    if asset['user_id'] != g.user['id']:
        abort(403)

    db.execute(
        'delete from asset where id = ? and user_id = ?',
        (id, g.user['id'])
    )
    db.commit()
    return redirect(url_for('assets.assets'))
