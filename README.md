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

![jp-message](https://cloud.githubusercontent.com/assets/1725068/12970972/71f68f4a-d0d8-11e5-9894-1c4018da03b1.png)

How to create a custom message DLL
---

Create a message text file, as explained by [Microsoft](https://msdn.microsoft.com/en-us/library/dd996906(v=vs.85).aspx).

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

How to use the plugin
---

If you simply want to mimic the native command

```
  //using native command; the category is #0 and the event-is is #8
LOG EVENT(Into Windows log events;"some message";Information message)
```

Do this:

```
$category:=0
$event:=5  //%1
ARRAY TEXT($params;1)
$params{1}:="some message"
LOG WRITE ENTRY (EVENTLOG_INFORMATION_TYPE;$category;$event;$params)
```

You can even mimic built-in 4D events (2,3,4)

```
$category:=0
$event:=2  //the database %1 has been successfully started
LOG WRITE ENTRY (EVENTLOG_INFORMATION_TYPE;$category;$event;$params)
```

By default, the source name is "4D Application" (constant:``EVENTLOG_DEFAULT_SOURCE``)

```
LOG GET SOURCE ($serverName;$souceName)
```

You can also attach binary data

```
  //these values with be inserted in the "%n" placeholders  in the message
ARRAY TEXT($params;2)
$params{1}:="arg1"
$params{2}:="arg2"

  //you can attach a binary to a message
C_BLOB($data)

$category:=0
$event:=5  //%1
LOG WRITE ENTRY (EVENTLOG_ERROR_TYPE;$category;$event;$params;$data)
```

![registry](https://cloud.githubusercontent.com/assets/1725068/12971009/1cea7466-d0d9-11e5-9c17-dbfbf5188c1f.png)
