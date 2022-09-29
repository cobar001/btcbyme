from datetime import datetime

from flask import render_template, Blueprint, flash, redirect, url_for, abort, session
from flask_login import login_required, current_user
from btcbyme.posts.forms import NewPostForm, NewPostConfirmationForm, SearchPostForm
from btcbyme import db, limiter
from btcbyme.models import Post, Persistent
from btcbyme.utilities import utilities
from btcpay import BTCPayClient


posts = Blueprint('posts', __name__)


@posts.route('/posts')
@login_required
@limiter.limit('500/day; 100/hour;', override_defaults=True)
def index_posts():
    user_posts = Post.query.filter_by(
        user_id=current_user.get_id()).order_by(Post.date_posted.desc())
    user_posts_view_data = utilities.get_posts_view_data(user_posts)
    return render_template(
        'user_posts.html', title='Posts', posts=user_posts_view_data)


@posts.route('/posts/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = NewPostForm()
    if form.validate_on_submit():
        geocoded_post_data = utilities.get_geocoded_post_info(
            ','.join(filter(None, [form.city.data, form.region.data, form.country.data])))
        if geocoded_post_data is None:
            flash(f'Unable to create post.', 'danger')
            return redirect(url_for('posts.index_posts'))
        post = Post(
            id=utilities.create_uuid(),
            markup=form.markup.data, min_tx=form.min_tx.data,
            max_tx=form.max_tx.data, latitude=geocoded_post_data.lat, longitude=geocoded_post_data.lon,
            city=geocoded_post_data.place_name, user_id=current_user.get_id(), currency=form.currency.data)
        encoded_post_data = utilities.encode_post_data(post)
        if encoded_post_data is None:
            flash(f'Unable to create post.', 'danger')
            return redirect(url_for('posts.index_posts'))
        return redirect(url_for('posts.new_post_confirmation', encoded_candidate_post=encoded_post_data))
    return render_template('new_post.html', title='New Post', form=form)


@posts.route('/posts/new/confirm/<string:encoded_candidate_post>', methods=['GET', 'POST'])
@login_required
def new_post_confirmation(encoded_candidate_post):
    candidate_post = utilities.decode_post_data(encoded_candidate_post)
    if candidate_post is None:
        flash(f'Unable to create post.', 'danger')
        return redirect(url_for('posts.index_posts'))
    if candidate_post.user_id != current_user.get_id():
        return abort(403)
    form = NewPostConfirmationForm()
    # Format view data.
    candidate_post.date_posted = datetime.utcnow()
    post_view_data = utilities.get_posts_view_data([candidate_post])[0]
    formatted_post_price = (utilities.SUPPORTED_CURRENCIES_SYMBOLS['USD'] +
                            utilities.format_price(utilities.POST_PRICE_USD))
    # Create invoice.
    persistent_client = Persistent.query.all()
    if len(persistent_client) != 1:
        flash(f'Unable to create post. Failed to retrieve BTCPay client.', 'danger')
        return redirect(url_for('posts.index_posts'))
    client = persistent_client[0].btcpay_server_client
    # If we are experiencing a new candidate post, create a new invoice and update session values.
    if session.get('new_post_id') is None or session.get('new_post_id') != candidate_post.id:
        new_invoice = client.create_invoice({"price": utilities.POST_PRICE_USD, "currency": "USD"})
        session['new_invoice_id'] = new_invoice['id']
        session['new_post_id'] = candidate_post.id
    if form.validate_on_submit():
        # Check post/invoice assumptions.
        new_invoice_id = session.get('new_invoice_id')
        new_post_id = session.get('new_post_id')
        if new_invoice_id is None or candidate_post.id != new_post_id:
            flash(f'Unable to create post. Invalid invoice ID.', 'danger')
            return redirect(url_for('posts.new_post'))
        # Verify required invoice status.
        fetch_invoice = client.get_invoice(new_invoice_id)
        if not (fetch_invoice['status'] in utilities.ACCEPTED_BTCPAY_SERVER_TX_STATUS):
            flash(f'Unable to create post. Transaction was not completed successfully.', 'danger')
            return redirect(url_for('posts.new_post'))
        if len(Post.query.filter_by(user_id=current_user.get_id()).all()) == utilities.MAX_POST_COUNT_PER_USER:
            flash(f'Unable to create post. Maximum post count reached.', 'danger')
            return redirect(url_for('posts.index_posts'))
        db.session.add(candidate_post)
        db.session.commit()
        flash(f'Your post has been created in {candidate_post.city}.', 'success')
        return redirect(url_for('posts.index_posts'))
    return render_template(
        'new_post_confirmation.html', title='Confirm Post', post=post_view_data, form=form,
        invoice_id=session['new_invoice_id'], post_price=formatted_post_price)


@posts.route('/posts/<string:post_id>', methods=['GET'])
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    post_view_data = utilities.get_posts_view_data([post])[0]
    return render_template(
        'post.html', title=f'Post {post_view_data.id}', post=post_view_data)


@posts.route('/posts/search', methods=['GET', 'POST'])
def search_posts():
    form = SearchPostForm()
    if form.validate_on_submit():
        search_filters = [set(Post.query.filter(Post.currency == form.currency.data).all())]
        # Access location data input, add to search filters if valid.
        location_data = list(filter(None, [form.city.data, form.region.data, form.country.data]))
        geocoded_post_data = None
        if len(location_data):
            geocoded_post_data = utilities.get_geocoded_post_info(','.join(location_data))
            search_bounding_box = utilities.get_lat_lon_bounding_box(
                geocoded_post_data.lat, geocoded_post_data.lon, form.search_distance.data)
            search_filters.append(set(Post.query.filter((Post.latitude >= search_bounding_box.min_lat) &
                                                        (Post.latitude <= search_bounding_box.max_lat) &
                                                        (Post.longitude >= search_bounding_box.min_lon) &
                                                        (Post.longitude <= search_bounding_box.max_lon))))
        # Access other data fields and add to search filters.
        if form.max_markup.data is not None:
            search_filters.append(set(Post.query.filter(Post.markup <= form.max_markup.data).all()))
        desired_tx_amount_data = form.desired_tx_amount.data
        if desired_tx_amount_data is not None:
            search_filters.append(set(
                Post.query.filter((Post.min_tx <= desired_tx_amount_data) &
                                  (Post.max_tx >= desired_tx_amount_data)).all()))
        # Perform an intersection on the search criteria. Limit the results to only the first 50 (for now).
        search_filters_results = list(set.intersection(*search_filters)) if len(search_filters) else []
        if len(search_filters_results) > 50:
            search_filters_results = search_filters_results[:50]
        # Apply sorting criteria.
        sorting_parameter = form.sort_by.data
        if sorting_parameter == utilities.SEARCH_SORTING_OPTIONS[0]:
            utilities.sort_posts(utilities.SearchSortingOptions.MARKUP_LOW_HIGH, search_filters_results)
        elif sorting_parameter == utilities.SEARCH_SORTING_OPTIONS[1]:
            utilities.sort_posts(utilities.SearchSortingOptions.MARKUP_HIGH_LOW, search_filters_results)
        elif sorting_parameter == utilities.SEARCH_SORTING_OPTIONS[2]:
            utilities.sort_posts(utilities.SearchSortingOptions.DATE_NEW_OLD, search_filters_results)
        elif sorting_parameter == utilities.SEARCH_SORTING_OPTIONS[3]:
            if geocoded_post_data is not None:
                utilities.sort_posts(
                    utilities.SearchSortingOptions.DISTANCE_LOW_HIGH, search_filters_results, geocoded_post_data)
            else:
                flash('Sorting by distance is not allowed if no location information ' +
                      '(city, state/region, or country) is provided.', 'danger')
                return render_template(
                    'search_posts.html', title=f'Search Posts', form=form, posts=None,
                    geocoded_post_data=geocoded_post_data)
        currency_symbol = utilities.SUPPORTED_CURRENCIES_SYMBOLS[form.currency.data]
        btc_price_data = utilities.get_btc_price_per_currency()
        original_btc_price_formatted = (currency_symbol +
                                        utilities.format_price(utilities.get_btc_price_from_data(
                                            btc_price_data, currency_symbol)))
        posts_view_data = utilities.get_posts_view_data(search_filters_results, btc_price_data=btc_price_data)
        return render_template(
            'search_posts.html', title=f'Search Posts', form=form, posts=posts_view_data,
            geocoded_post_data=geocoded_post_data, original_btc_price=original_btc_price_formatted)
    return render_template(
        'search_posts.html', title=f'Search Posts', form=form, posts=None, geocoded_post_data=None)


@posts.route('/post/<string:post_id>/delete', methods=['POST', 'GET'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('posts.index_posts'))
