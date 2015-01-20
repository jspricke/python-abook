# Python library to convert between Abook and vCard

http://abook.sourceforge.net/.
Needs python-vobject and python-configobj libraries.

- Saves photo to ~/.abook/photo/NAME.jpeg
- Uses a modified abookrc:
```
field other = Other
view CONTACT = name, email
view ADDRESS = address, address2, city, state, zip, country
view PHONE = phone, workphone, mobile, other
view OTHER = nick, url, notes
```
