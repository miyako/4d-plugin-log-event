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

You can find a sample msg4d.dll clone with the project.

```
; /* Sample Message Text File
;  *
;  * Message Text Files
;  * https://msdn.microsoft.com/en-us/library/dd996906(v=vs.85).aspx
;  * Reporting Events
;  * https://msdn.microsoft.com/en-us/library/aa363680(v=vs.85).aspx
;  */

; // This is the header section.

SeverityNames=(Success=0x0:STATUS_SEVERITY_SUCCESS
  Informational=0x1:STATUS_SEVERITY_INFORMATIONAL
  Warning=0x2:STATUS_SEVERITY_WARNING
  Error=0x3:STATUS_SEVERITY_ERROR
)

FacilityNames=(System=0x0:FACILITY_SYSTEM
  Runtime=0x2:FACILITY_RUNTIME
)

LanguageNames=(English=0x409:MSG00409)
LanguageNames=(Japanese=0x411:MSG00411)

; // The following are the message definitions.

MessageIdTypedef=WORD

MessageId=0x1
SymbolicName=MSG_1
Language=English
%1!S!%0
.

Language=Japanese
%1!S!%0
.

; // Based on original 4dmsg.dll (no catagory)

MessageId=0x2
SymbolicName=MSG_DATABASE_LOG_START
Language=English
The database %1!S! has been successfully started
.

Language=Japanese
データベースの%1!S!を開始しました
.

MessageId=0x3
SymbolicName=MSG_WEB_LOG_START
Language=English
The web server %1!S! has been successfully started
.

Language=Japanese
Webサーバーの%1!S!を開始しました
.

MessageId=0x4
SymbolicName=MSG_WEB_LOG_HALT
Language=English
The web server %1!S! has been halted
.

Language=Japanese
Webサーバーの%1!S!を停止しました
.

MessageId=0x5
SymbolicName=MSG_5
Language=English
%1!S!%0
.

Language=Japanese
%1!S!%0
.

MessageId=0x6
SymbolicName=MSG_6
Language=English
%1!S!%0
.

Language=Japanese
%1!S!%0
.

MessageId=0x7
SymbolicName=MSG_7
Language=English
%1!S!%0
.

Language=Japanese
%1!S!%0
.

; // The LOG EVENT COMMAND (no catagory)

MessageId=0x8
SymbolicName=MSG_LOG_EVENT
Language=English
%1!S!%0
.

Language=Japanese
%1!S!%0
.

MessageId=0x9
SymbolicName=MSG_9
Language=English
%1!S!%0
.

Language=Japanese
%1!S!%0
.

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
