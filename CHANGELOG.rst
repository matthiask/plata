.. _changelog:

Change log
==========

`Next version`_
~~~~~~~~~~~~~~~

.. note::

   Because of the long time between the two releases these release notes
   will probably not mention all differences and steps that are required
   to upgrade a project from 1.1 to the current version. It is assumed
   that you're running a checkout of Plata, or that you're mostly
   rewriting the project anyway. Just as a reference point, the current
   release of Django at the time of the Plata 1.1 release was Django
   1.4.0!

- Removed product models and migrations from the repository. Plata
  expects you to provide your own product model, therefore providing
  either of those would be against what Plata is all about.
- Removed mentions of South in the code base and raised the Django
  version requirement to 1.8 LTS.
- Added support for Django 1.11 LTS and Django 2.1.
- Reformatted the code using black and added enforcement of black/flake8
  cleanliness on Travis CI .
- Made the test suite pass again.
- Products do not have to be unique in a cart anymore. This is
  especially useful for configurable products.
- The shop view now comes with two additional methods, ``redirect`` and
  ``reverse_url`` which can be used to customize the URL reversal process which
  is especially useful with namespaced URLs.
- The Django model used for stock tracking can be changed using the new
  ``PLATA_STOCK_TRACKING_MODEL`` setting.
- If the method ``Product.handle_stock_transaction`` exists, it is called
  when saving stock transactions providing the opportunity for filling in
  additional fields.
- Tax classes no longer have reverse foreign keys to prices. That means that
  having more than one price model in a project is now fully supported.
- Whether prices should be shown with tax included or not can be decided
  per-order.
- Bugs and crashes have been fixed.
- Added additional payment providers, among them Stripe, PagSeguro,
  Billogram, prepaying by bank transfer, etc.
- Event handlers for server-side Google Analytics tracking of orders
  has been added, see ``plata/shop/ga_tracking.py``.


`v1.1.0`_ (2012-04-04)
~~~~~~~~~~~~~~~~~~~~~~

- Historical release notes are available in the Git history.


`v1.0.0`_ (2012-02-22)
~~~~~~~~~~~~~~~~~~~~~~

The 1.0 release.


.. _v1.0.0: https://github.com/matthiask/plata/commit/e326169e534b0
.. _v1.1.0: https://github.com/matthiask/plata/compare/v1.0.0...v1.1.0
.. _Next version: https://github.com/matthiask/plata/compare/v1.1.0...master
