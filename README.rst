Python library to convert between Abook and vCard
=================================================

* Reads and writes `Abook <http://abook.sourceforge.net/>`_ files.
* Saves photo to ~/.abook/photo/NAME.jpeg (if directory is present).

Configuration
-------------

::

  field other = Other
  view CONTACT = name, email
  view ADDRESS = address, address2, city, state, zip, country
  view PHONE = phone, workphone, mobile, other
  view OTHER = nick, url, notes
