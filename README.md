# 4d-plugin-log-event
Write to Windows Event Log (with more control than native LOG EVENT)

##Platform

| carbon | cocoa | win32 | win64 |
|:------:|:-----:|:---------:|:---------:|
|🚫|🚫|🆗|🆗|

About
---

The built in command LOG EVENT has a bug, which means that Japanese messages get corrupt in the event log.

This plugin provides a way to work around that problem.

It also allows the developer to use their own message DLL.

How to create a custom message DLL
---

Create a message text file, as explain by [Microsoft](https://msdn.microsoft.com/en-us/library/dd996906(v=vs.85).aspx).

You must save the file in UTF-16LE encoding.

Compile the file.

```
mc -u 4dmsg-clone.mc
```

The following files are created:

* 4dmsg-clone.h
* 4dmsg-clone.rc
* MSG00411.bin (English data)
* MSG00409.bin (Japanese data)
 
Compile the resource file.

```
rc 4dmsg-clone.rc
```

The following file is created:

* 4dmsg-clone.res

Create a resouce-only DLL.

```
link -dll -noentry /machine:x86 4dmsg-clone.res
```

Create also a 64 bit version.

```
link -dll -noentry /machine:x64 4dmsg-clone.res
```
