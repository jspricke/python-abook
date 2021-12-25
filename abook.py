# Python library to convert between Abook and vCard
#
# Copyright (C) 2013-2021  Jochen Sprickerhof
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
"""Python library to convert between Abook and vCard."""

from configparser import ConfigParser, SectionProxy
from hashlib import sha1
from os import makedirs
from os.path import dirname, expanduser, getmtime, isfile, join
from socket import getfqdn
from threading import Lock
from typing import Iterable

from vobject import vCard
from vobject.base import Component, readComponents
from vobject.vcard import Address, Name


class Abook:
    """Represents a Abook addressbook."""

    def __init__(self, filename: str = None) -> None:
        """Abook Constructor.

        filename -- the filename to load (default: ~/.abook/addressbook)
        """
        self._filename = filename if filename else expanduser("~/.abook/addressbook")
        self._last_modified = 0.0
        self._book = ConfigParser()
        self._lock = Lock()
        self._update()

    def _update(self) -> None:
        """Update internal state."""
        with self._lock:
            if (
                not isfile(self._filename)
                or getmtime(self._filename) > self._last_modified
            ):
                if isfile(self._filename):
                    self._last_modified = getmtime(self._filename)
                self._book = ConfigParser(default_section="format")
                self._book.read(self._filename)

    def to_vcf(self) -> str:
        """Convert to vCard string."""
        return "\r\n".join([v.serialize() for v in self.to_vcards()])

    def append_vobject(self, vcard: Component, filename: str = "") -> str:
        """Append address to Abook addressbook.

        vcard -- vCard to append
        filename -- unused
        return the new UID of the appended vcard
        """
        book = ConfigParser(default_section="format")
        with self._lock:
            book.read(self._filename)
            section = str(max([-1] + [int(k) for k in book.sections()]) + 1)
            Abook.to_abook(vcard, section, book, self._filename)
            with open(self._filename, "w", encoding="utf-8") as outfile:
                book.write(outfile, False)

        return Abook._gen_uid(book[section])

    def remove(self, uid: str, filename: str = "") -> None:
        """Remove address from Abook addressbook.

        uid -- UID of the entry to remove
        """
        book = ConfigParser(default_section="format")
        with self._lock:
            book.read(self._filename)
            del book[uid.split("@")[0]]
            with open(self._filename, "w", encoding="utf-8") as outfile:
                book.write(outfile, False)

    def replace_vobject(self, uid: str, vcard: Component, filename: str = "") -> str:
        """Update address in Abook addressbook.

        uid -- uid of the entry to replace
        vcard -- vCard of the new content
        filename -- unused
        """
        entry = uid.split("@")[0]

        book = ConfigParser(default_section="format")
        with self._lock:
            book.read(self._filename)
            Abook.to_abook(vcard, entry, book, self._filename)
            with open(self._filename, "w", encoding="utf-8") as outfile:
                book.write(outfile, False)

        return Abook._gen_uid(self._book[entry])

    def move_vobject(self, uuid: str, from_filename: str, to_filename: str) -> None:
        """Update addressbook of an address.

        Not implemented
        """
        pass

    @staticmethod
    def _gen_uid(entry: SectionProxy) -> str:
        """Generate UID based on the index in the Abook file.

        Not that the index is just a number and abook tends to regenerate it upon sorting.
        """
        return f"{entry.name}@{getfqdn()}"

    @staticmethod
    def _gen_name(name: str) -> Name:
        """Split the name into family and given name."""
        return Name(family=name.rsplit(" ")[-1], given=name.rsplit(" ", 1)[0])

    @staticmethod
    def _gen_addr(entry: SectionProxy) -> Address:
        """Generate a vCard Address object."""
        return Address(
            street=entry.get("address", ""),
            extended=entry.get("address2", ""),
            city=entry.get("city", ""),
            region=entry.get("state", ""),
            code=entry.get("zip", ""),
            country=entry.get("country", ""),
        )

    def _add_photo(self, card: Component, name: str) -> None:
        """Load a photo and add it to the vCard (if exists)."""
        try:
            photo_file = join(dirname(self._filename), f"photo/{name}.jpeg")
            with open(photo_file, "rb") as infile:
                jpeg = infile.read()
            photo = card.add("photo")
            photo.type_param = "jpeg"
            photo.encoding_param = "b"
            photo.value = jpeg
        except IOError:
            pass

    def _to_vcard(self, entry: SectionProxy) -> Component:
        """Return a vCard of the Abook entry."""
        card = vCard()

        card.add("uid").value = Abook._gen_uid(entry)
        card.add("fn").value = entry["name"]
        card.add("n").value = Abook._gen_name(entry["name"])

        if "email" in entry:
            for email in entry["email"].split(","):
                card.add("email").value = email

        addr_comps = ["address", "address2", "city", "country", "zip", "country"]
        if any(comp in entry for comp in addr_comps):
            card.add("adr").value = Abook._gen_addr(entry)

        if "other" in entry:
            tel = card.add("tel")
            tel.value = entry["other"]

        if "phone" in entry:
            tel = card.add("tel")
            tel.type_param = "home"
            tel.value = entry["phone"]

        if "workphone" in entry:
            tel = card.add("tel")
            tel.type_param = "work"
            tel.value = entry["workphone"]

        if "mobile" in entry:
            tel = card.add("tel")
            tel.type_param = "cell"
            tel.value = entry["mobile"]

        if "nick" in entry:
            card.add("nickname").value = entry["nick"]

        if "url" in entry:
            card.add("url").value = entry["url"]

        if "notes" in entry:
            card.add("note").value = entry["notes"]

        self._add_photo(card, entry["name"])

        return card

    def get_uids(self, filename: str = "") -> list[str]:
        """Return a list of UIDs.

        filename  -- unused, for API compatibility only
        """
        self._update()
        return [Abook._gen_uid(self._book[entry]) for entry in self._book.sections()]

    def get_filesnames(self) -> list[str]:
        """All filenames."""
        return [self._filename]

    @staticmethod
    def get_meta() -> dict[str, str]:
        """Meta tags of the vCard collection."""
        return {"tag": "VADDRESSBOOK"}

    def last_modified(self) -> float:
        """Last time the Abook file was parsed."""
        self._update()
        return self._last_modified

    def to_vcards(self) -> list[Component]:
        """Return a list of vCards."""
        self._update()
        return [self._to_vcard(self._book[entry]) for entry in self._book.sections()]

    def to_vobject_etag(self, filename: str, uid: str) -> tuple[Component, str]:
        """Return vCard and etag of one Abook entry.

        filename  -- unused, for API compatibility only
        uid -- the UID of the Abook entry
        """
        return self.to_vobjects(filename, [uid])[0][1:3]

    def to_vobjects(
        self, filename: str, uids: Iterable[str] = None
    ) -> list[tuple[str, Component, str]]:
        """Return vCards and etags of all Abook entries in uids.

        filename  -- unused, for API compatibility only
        uids -- the UIDs of the Abook entries (all if None)
        """
        self._update()

        if not uids:
            uids = self.get_uids(filename)

        items = []

        for uid in uids:
            entry = self._book[uid.split("@")[0]]
            # TODO add getmtime of photo
            etag = sha1(str(dict(entry)).encode("utf-8"))
            items.append((uid, self._to_vcard(entry), f'"{etag.hexdigest()}"'))
        return items

    def to_vobject(self, filename: str = "", uid: str = "") -> Component:
        """Return the vCard corresponding to the uid.

        filename  -- unused, for API compatibility only
        uid -- the UID to get (required)
        """
        self._update()
        return self._to_vcard(self._book[uid.split("@")[0]])

    @staticmethod
    def _conv_adr(adr: Component, entry: SectionProxy) -> None:
        """Convert to Abook address format."""
        if adr.value.street:
            entry["address"] = adr.value.street
        if adr.value.extended:
            entry["address2"] = adr.value.extended
        if adr.value.city:
            entry["city"] = adr.value.city
        if adr.value.region:
            entry["state"] = adr.value.region
        if adr.value.code and adr.value.code != "0":
            entry["zip"] = adr.value.code
        if adr.value.country:
            entry["country"] = adr.value.country

    @staticmethod
    def _conv_tel_list(tel_list: list[Component], entry: SectionProxy) -> None:
        """Convert to Abook phone types."""
        for tel in tel_list:
            if not hasattr(tel, "TYPE_param"):
                entry["other"] = tel.value
            elif tel.TYPE_param.lower() == "home":
                entry["phone"] = tel.value
            elif tel.TYPE_param.lower() == "work":
                entry["workphone"] = tel.value
            elif tel.TYPE_param.lower() == "cell":
                entry["mobile"] = tel.value

    @staticmethod
    def to_abook(
        card: Component, section: str, book: ConfigParser, bookfile: str = ""
    ) -> None:
        """Convert a vCard to Abook."""
        book[section] = {}
        book[section]["name"] = card.fn.value

        if hasattr(card, "email"):
            book[section]["email"] = ",".join([e.value for e in card.email_list])

        if hasattr(card, "adr"):
            Abook._conv_adr(card.adr, book[section])

        if hasattr(card, "tel_list"):
            Abook._conv_tel_list(card.tel_list, book[section])

        if hasattr(card, "nickname") and card.nickname.value:
            book[section]["nick"] = card.nickname.value

        if hasattr(card, "url") and card.url.value:
            book[section]["url"] = card.url.value

        if hasattr(card, "note") and card.note.value:
            book[section]["notes"] = card.note.value

        if hasattr(card, "photo") and bookfile:
            try:
                photo_dir = join(dirname(bookfile), "photo")
                makedirs(photo_dir, exist_ok=True)
                photo_file = join(photo_dir, f"{card.fn.value}.{card.photo.TYPE_param}")
                with open(photo_file, "wb") as outfile:
                    outfile.write(card.photo.value)
            except IOError:
                pass

    @staticmethod
    def abook_file(vcard: Component, bookfile: str) -> None:
        """Write a new Abook file with the given vcards."""
        book = ConfigParser(default_section="format")

        book["format"] = {}
        book["format"]["program"] = "abook"
        book["format"]["version"] = "0.6.1"

        for (i, card) in enumerate(readComponents(vcard.read())):
            Abook.to_abook(card, str(i), book, bookfile)
        with open(bookfile, "w", encoding="utf-8") as outfile:
            book.write(outfile, False)


def abook2vcf() -> None:
    """Command line tool to convert from Abook to vCard."""
    from argparse import ArgumentParser, FileType
    from os.path import expanduser
    from sys import stdout

    parser = ArgumentParser(description="Converter from Abook to vCard syntax.")
    parser.add_argument(
        "infile",
        nargs="?",
        default=expanduser("~/.abook/addressbook"),
        help="The Abook file to process (default: ~/.abook/addressbook)",
    )
    parser.add_argument(
        "outfile",
        nargs="?",
        type=FileType("w"),
        default=stdout,
        help="Output vCard file (default: stdout)",
    )
    args = parser.parse_args()

    args.outfile.write(Abook(args.infile).to_vcf())


def vcf2abook() -> None:
    """Command line tool to convert from vCard to Abook."""
    from argparse import ArgumentParser, FileType
    from sys import stdin

    parser = ArgumentParser(description="Converter from vCard to Abook syntax.")
    parser.add_argument(
        "infile",
        nargs="?",
        type=FileType("r"),
        default=stdin,
        help="Input vCard file (default: stdin)",
    )
    parser.add_argument(
        "outfile",
        nargs="?",
        default=expanduser("~/.abook/addressbook"),
        help="Output Abook file (default: ~/.abook/addressbook)",
    )
    args = parser.parse_args()

    Abook.abook_file(args.infile, args.outfile)
