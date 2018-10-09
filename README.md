# User-Version-File-System
A personalised versioning file system written in Python; primarily for text files, this project allows users to create and edit files within a mounted directory, to which versions can be spawned from. See below for further explanation on how to use:

Firstly, clone the project in your local workspace (note this project was designed for usage on LINUX):

```
$ git clone https://github.com/cyrus-raitava/User-Version-File-System.git
```

Now, navigate your way to the inside of the A3/ directory, using the terminal. Once here, perform the command:

```
python2 versionfs.py ____
```

where the blank may be filled in with an arbitrarily chosen filename, with which to mount. Now open a second terminal, and navigate to the same position as the first. Create files in the mount directory, using the touch command, and your favourite text editor. Edit these files, and a maximum of 6 older versions may be spawned, in between your edits.


