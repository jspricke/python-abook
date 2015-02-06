# Python library to convert between Abook and vCard
#
# Copyright (C) 2013-2015  Jochen Sprickerhof
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
"""Python libraryto convert between Abook and vCard"""

from configobj import ConfigObj
from hashlib import sha1
from os.path import getmtime, dirname, join
from socket import getfqdn
from threading import Lock
from vobject import readOne, readComponents, vCard
from vobject.vcard import Name, Address


class Abook(object):
    """Represents a Abook addressbook"""

    def __init__(self, filename=None):
        """Constructor

        filename -- the filename to load
        """
        self.filename = filename
        self._last_modified = 0
        self._events = []
        self._lock = Lock()

    def to_vcf(self):
        """ Converts to vCard string"""
        self._lock.acquire()

        if getmtime(self.filename) > self._last_modified:
            self._events = self.to_vcards()
            self._last_modified = getmtime(self.filename)

        self._lock.release()

        return '\r\n'.join([v.serialize() for v in self._events])

    def append(self, text):
        """Appends an address to the Abook addressbook"""
        self._lock.acquire()

        book = ConfigObj(self.filename, encoding='utf-8', list_values=False)

        section = max([int(k) for k in book.keys()[1:]])
        Abook.to_abook(readOne(text), str(section+1), book)
        Abook._write(book)

        self._lock.release()

    def remove(self, name):
        """Removes an address to the Abook addressbook"""
        uid = name.split('@')[0].split('-')
        if len(uid) != 2:
            return

        self._lock.acquire()

        book = ConfigObj(self.filename, encoding='utf-8', list_values=False)
        linehash = sha1(book[uid[0]]['name'].encode('utf-8')).hexdigest()

        if linehash == uid[1]:
            del book[uid[0]]
            Abook._write(book)

        self._lock.release()

    def replace(self, name, text):
        """Updates an address to the Abook addressbook"""
        uid = name.split('@')[0].split('-')
        if len(uid) != 2:
            return

        self._lock.acquire()

        book = ConfigObj(self.filename, encoding='utf-8', list_values=False)
        linehash = sha1(book[uid[0]]['name'].encode('utf-8')).hexdigest()

        if linehash == uid[1]:
            Abook.to_abook(readOne(text), uid[0], book)
            Abook._write(book)

        self._lock.release()

    @staticmethod
    def _gen_uid(index, name):
        """Generates a UID based on the index in the Abook file and the hash of the name"""
        return '%s-%s@%s' % (index, sha1(name.encode('utf-8')).hexdigest(), getfqdn())

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
        """Tries to load a foto and add it to the vCard"""
        try:
            photo_file = join(dirname(self.filename), 'photo/%s.jpeg' % name)
            jpeg = open(photo_file, 'rb').read()
            photo = card.add('photo')
            photo.type_param = 'jpeg'
            photo.encoding_param = 'b'
            photo.value = jpeg
        except IOError:
            pass

    def _to_vcard(self, index, entry):
        """Returns a vobject vCard of the Abook entry"""
        card = vCard()

        card.add('uid').value = Abook._gen_uid(index, entry['name'])
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

    def to_vcards(self):
        """Returns a list of vobject vCards"""
        book = ConfigObj(self.filename, encoding='utf-8', list_values=False)
        cards = []

        for (index, entry) in book.items()[1:]:
            cards.append(self._to_vcard(index, entry))

        return cards

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
    def to_abook(card, section, book):
        """Converts a vCard to Abook"""
        book[section] = {}
        book[section]['name'] = card.fn.value

        if hasattr(card, 'email'):
            book[section]['email'] = ','.join([e.value for e in card.email_list])

        if hasattr(card, 'adr'):
            Abook._conv_adr(card.adr, book[section])

        if hasattr(card, 'tel_list'):
            Abook._conv_tel_list(card.tel_list, book[section])

        if hasattr(card, 'nickname'):
            book[section]['nick'] = card.nickname.value

        if hasattr(card, 'url'):
            book[section]['url'] = card.url.value

        if hasattr(card, 'note'):
            book[section]['notes'] = card.note.value

        if hasattr(card, 'photo') and book.filename:
            try:
                photo_file = join(dirname(book.filename), 'photo/%s.%s' % (card.fn.value, card.photo.TYPE_param))
                open(photo_file, 'w').write(card.photo.value)
            except IOError:
                pass

    @staticmethod
    def _write(book):
        """Convert from ConfigObj to Abook formating"""
        filename = book.filename
        book.filename = None
        entries = book.write()
        entries = [e.replace(' = ', '=', 1) for e in entries]

        if filename:
            open(filename, 'w').write('\n'.join(entries))
        else:
            return '\n'.join(entries)

    @staticmethod
    def abook_file(vcard, bookfile):
        """Write a new Abook file with the given vcards"""
        book = ConfigObj(encoding='utf-8', list_values=False)
        book.filename = bookfile.name
        book.initial_comment = ['abook addressbook file']

        book['format'] = {}
        book['format']['program'] = 'abook'
        book['format']['version'] = '0.6.0pre2'

        for (i, card) in enumerate(readComponents(vcard.read())):
            Abook.to_abook(card, str(i), book)
        Abook._write(book)


def abook2vcf():
    """Command line tool to convert from Abook to vCard"""
    from argparse import ArgumentParser, FileType
    from os.path import expanduser
    from sys import stdout

    parser = ArgumentParser(description='Converter from Abook to vCard syntax.')
    parser.add_argument('infile', nargs='?', default=join(expanduser('~'), '.abook/addressbook'),
                        help='The Abook file to process (default: ~/.abook/addressbook)')
    parser.add_argument('outfile', nargs='?', type=FileType('w'), default=stdout,
                        help='Output vCard file (default: stdout)')
    args = parser.parse_args()

    args.outfile.write(Abook(args.infile).to_vcf())


def vcf2abook():
    """Command line tool to convert from vCard to Abook"""
    from argparse import ArgumentParser, FileType
    from sys import stdin, stdout

    parser = ArgumentParser(description='Converter from vCard to Abook syntax.')
    parser.add_argument('infile', nargs='?', type=FileType('r'), default=stdin,
                        help='Input iCalendar file (default: stdin)')
    parser.add_argument('outfile', nargs='?', type=FileType('w'), default=stdout,
                        help='Output iCalendar file (default: stdout)')
    args = parser.parse_args()

    Abook.abook_file(args.infile, args.outfile)
