filestalker
=================

search for files on a samba share and get notified if the stalker finds a match! KDE And gnome3 might have some icon problems at the start, if its the case: tell me

the usage is simple: the stalker connects to a samba share and looks on the root area for folders matching the needles in the configuration. the stalker looks inside the matching folders and displays every file and folder as a "hit" and tries to tell you about new files since you last saw them (in this session).



Installation
==============

use the .deb file and install it accordingly. take the example config from the doc directory and place it in /home/<username>/.filestalker/config and alter it to your needs.


Building the deb
==================

just run "debuild" in the root of the project
