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

Install
------------------

:: 

  git clone https://github.com/jspricke/python-abook.git
  cd python-abook

  # builds the library (for use in your own scripts)
  python3 setup.py build

  # installs executables `abook2vcf` `vcf2abook` to $PATH 
  # mac (/opt/homebrew/bin)
  python3 setup.py install

Usage
-----

python-abook converts vcards (.vcf files) and writes them to your abook addressbook. 
It can also handle .vcf files containing multiple contacts. 
Additionally python-abook can convert your abook addressbook to .vcf format:

:: 

  # convert your address book to vcf (one vcf file contatining all contacts)

  $ abook2vcf --help
  $ abook2vcf ~/path/to/abook/addressbook ~/path/to/write/contacts.vcf

  # ommit the output file to print results to stdout

  $ abook2vcf ~/path/to/abook/addressbook


  # convert vcf contact/s and write them to your addressbook

  $ vcf2abook --help
  $ vcf2abook ~/path/to/contact.vcf ~/path/to/abook/addressbook


