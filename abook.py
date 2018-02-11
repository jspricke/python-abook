# Python library to convert between Abook and vCard
#
# Copyright (C) 2013-2017  Jochen Sprickerhof
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Python library to convert between Abook and vCard"""

from configparser import ConfigParser
from os.path import getmtime, dirname, expanduser, join
from socket import getfqdn
from threading import Lock
from vobject import readOne, readComponents, vCard
from vobject.vcard import Name, Address


class Abook(object):
    """Represents a Abook addressbook"""

    def __init__(self, filename=expanduser('~/.abook/addressbook')):
        """Constructor

        filename -- the filename to load (default: ~/.abook/addressbook)
        """
        self._filename = filename
        self._last_modified = 0
        self._book = []
        self._lock = Lock()
        self._update()

    def _update(self):
        """ Update internal state."""
        with self._lock:
            if getmtime(self._filename) > self._last_modified:
                self._last_modified = getmtime(self._filename)
                self._book = ConfigParser(default_section='format')
                self._book.read(self._filename)

    def to_vcf(self):
        """ Converts to vCard string"""
        return '\r\n'.join([v.serialize() for v in self.to_vcards()])

    def append(self, text):
        """Appends an address to the Abook addressbook"""
        return self.append_vobject(readOne(text))

    def append_vobject(self, vcard, filename=None):
        """Appends an address to the Abook addressbook
        vcard -- vObject to append
        filename -- unused
        returns the new UID of the appended vcard
        """
        book = ConfigParser(default_section='format')
        with self._lock:
            book.read(self._filename)
            section = max([int(k) for k in book.sections()]) + 1
            Abook.to_abook(vcard, str(section), book, self._filename)
            with open(self._filename, 'w') as fp:
                book.write(fp, False)

        return Abook._gen_uid(self._book[section])

    def remove(self, uid, filename=None):
        """Removes an address to the Abook addressbook
        uid -- UID of the entry to remove
        """
        book = ConfigParser(default_section='format')
        with self._lock:
            book.read(self._filename)
            del book[uid.split('@')[0]]
            with open(self._filename, 'w') as fp:
                book.write(fp, False)

    def replace(self, uid, text):
        """Updates an address to the Abook addressbook"""
        return self.replace_vobject(uid, readOne(text))

    def replace_vobject(self, uid, vcard, filename=None):
        """Updates an address to the Abook addressbook
        uid -- uid of the entry to replace
        vcard -- vObject of the new content
        filename -- unused
        """
        entry = uid.split('@')[0]

        book = ConfigParser(default_section='format')
        with self._lock:
            book.read(self._filename)
            Abook.to_abook(vcard, entry, book, self._filename)
            with open(self._filename, 'w') as fp:
                book.write(fp, False)

        return Abook._gen_uid(self._book[entry])

    @staticmethod
    def _gen_uid(entry):
        """Generates a UID based on the index in the Abook file
        Not that the index is just a number and abook tends to regenerate it upon sorting.
        """
        return '%s@%s' % (entry.name, getfqdn())

    @staticmethod
    def _gen_name(name):
        """Splits the name into family and given name"""
        return Name(family=name.split(' ')[-1], given=name.split(' ')[:-1])

    @staticmethod
    def _gen_addr(entry):
        """Generates a vobject Address objects"""
        return Address(street=entry.get('address', ''),
                       extended=entry.get('address2', ''),
                       city=entry.get('city', ''),
                       region=entry.get('state', ''),
                       code=entry.get('zip', ''),
                       country=entry.get('country', ''))

    def _add_photo(self, card, name):
        """Tries to load a photo and add it to the vCard"""
        try:
            photo_file = join(dirname(self._filename), 'photo/%s.jpeg' % name)
            jpeg = open(photo_file, 'rb').read()
            photo = card.add('photo')
            photo.type_param = 'jpeg'
            photo.encoding_param = 'b'
            photo.value = jpeg
        except IOError:
            pass

    def _to_vcard(self, entry):
        """Returns a vobject vCard of the Abook entry"""
        card = vCard()

        card.add('uid').value = Abook._gen_uid(entry)
        card.add('fn').value = entry['name']
        card.add('n').value = Abook._gen_name(entry['name'])

        if 'email' in entry:
            for email in entry['email'].split(','):
                card.add('email').value = email

        addr_comps = ['address', 'address2', 'city', 'country', 'zip', 'country']
        if any(comp in entry for comp in addr_comps):
            card.add('adr').value = Abook._gen_addr(entry)

        if 'other' in entry:
            tel = card.add('tel')
            tel.value = entry['other']

        if 'phone' in entry:
            tel = card.add('tel')
            tel.type_param = 'home'
            tel.value = entry['phone']

        if 'workphone' in entry:
            tel = card.add('tel')
            tel.type_param = 'work'
            tel.value = entry['workphone']

        if 'mobile' in entry:
            tel = card.add('tel')
            tel.type_param = 'cell'
            tel.value = entry['mobile']

        if 'nick' in entry:
            card.add('nickname').value = entry['nick']

        if 'url' in entry:
            card.add('url').value = entry['url']

        if 'notes' in entry:
            card.add('note').value = entry['notes']

        self._add_photo(card, entry['name'])

        return card

    def get_uids(self, filename=None):
        """Return a list of UIDs
        filename  -- unused, for API compatibility only
        """
        self._update()
        return [Abook._gen_uid(self._book[entry]) for entry in self._book.sections()]

    def get_filesnames(self):
        """All filenames"""
        return [self._filename]

    def get_meta(self):
        """Meta tags of the vObject collection"""
        return {'tag': 'VADDRESSBOOK'}

    def last_modified(self):
        """Last time the Abook file was parsed"""
        self._update()
        return self._last_modified

    def to_vcards(self):
        """Returns a list of vobject vCards"""
        self._update()
        return [self._to_vcard(self._book[entry]) for entry in self._book.sections()]

    def to_vobject(self, filename=None, uid=None):
        """Returns the vobject corresponding to the uid
        filename  -- unused, for API compatibility only
        uid -- the UID to get (required)
        """
        self._update()
        return self._to_vcard(self._book[uid.split('@')[0]])

    @staticmethod
    def _conv_adr(adr, entry):
        """Converts to Abook address format"""
        if adr.value.street:
            entry['address'] = adr.value.street
        if adr.value.extended:
            entry['address2'] = adr.value.extended
        if adr.value.city:
            entry['city'] = adr.value.city
        if adr.value.region:
            entry['state'] = adr.value.region
        if adr.value.code and adr.value.code != '0':
            entry['zip'] = adr.value.code
        if adr.value.country:
            entry['country'] = adr.value.country

    @staticmethod
    def _conv_tel_list(tel_list, entry):
        """Converts to Abook phone types"""
        for tel in tel_list:
            if not hasattr(tel, 'TYPE_param'):
                entry['other'] = tel.value
            elif tel.TYPE_param.lower() == 'home':
                entry['phone'] = tel.value
            elif tel.TYPE_param.lower() == 'work':
                entry['workphone'] = tel.value
            elif tel.TYPE_param.lower() == 'cell':
                entry['mobile'] = tel.value

    @staticmethod
    def to_abook(card, section, book, bookfile=None):
        """Converts a vCard to Abook"""
        book[section] = {}
        book[section]['name'] = card.fn.value

        if hasattr(card, 'email'):
            book[section]['email'] = ','.join([e.value for e in card.email_list])

        if hasattr(card, 'adr'):
            Abook._conv_adr(card.adr, book[section])

        if hasattr(card, 'tel_list'):
            Abook._conv_tel_list(card.tel_list, book[section])

        if hasattr(card, 'nickname') and card.nickname.value:
            book[section]['nick'] = card.nickname.value

        if hasattr(card, 'url') and card.url.value:
            book[section]['url'] = card.url.value

        if hasattr(card, 'note') and card.note.value:
            book[section]['notes'] = card.note.value

        if hasattr(card, 'photo') and bookfile:
            try:
                photo_file = join(dirname(bookfile), 'photo/%s.%s' % (card.fn.value, card.photo.TYPE_param))
                open(photo_file, 'wb').write(card.photo.value)
            except IOError:
                pass

    @staticmethod
    def abook_file(vcard, bookfile):
        """Write a new Abook file with the given vcards"""
        book = ConfigParser(default_section='format')

        book['format'] = {}
        book['format']['program'] = 'abook'
        book['format']['version'] = '0.6.1'

        for (i, card) in enumerate(readComponents(vcard.read())):
            Abook.to_abook(card, str(i), book, bookfile)
        with open(bookfile, 'w') as fp:
            book.write(fp, False)


def abook2vcf():
    """Command line tool to convert from Abook to vCard"""
    from argparse import ArgumentParser, FileType
    from os.path import expanduser
    from sys import stdout

    parser = ArgumentParser(description='Converter from Abook to vCard syntax.')
    parser.add_argument('infile', nargs='?', default=expanduser('~/.abook/addressbook'),
                        help='The Abook file to process (default: ~/.abook/addressbook)')
    parser.add_argument('outfile', nargs='?', type=FileType('w'), default=stdout,
                        help='Output vCard file (default: stdout)')
    args = parser.parse_args()

    args.outfile.write(Abook(args.infile).to_vcf())


def vcf2abook():
    """Command line tool to convert from vCard to Abook"""
    from argparse import ArgumentParser, FileType
    from sys import stdin

    parser = ArgumentParser(description='Converter from vCard to Abook syntax.')
    parser.add_argument('infile', nargs='?', type=FileType('r'), default=stdin,
                        help='Input vCard file (default: stdin)')
    parser.add_argument('outfile', nargs='?', default=expanduser('~/.abook/addressbook'),
                        help='Output Abook file (default: ~/.abook/addressbook)')
    args = parser.parse_args()

    Abook.abook_file(args.infile, args.outfile)
