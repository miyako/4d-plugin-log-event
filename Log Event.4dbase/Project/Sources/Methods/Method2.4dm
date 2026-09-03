//%attributes = {}
//using native command; the category is #0 and the event-is is #8
LOG EVENT:C667(Into Windows log events:K38:4; "some message"; Information message:K38:1)

//using plugin; by default, the source name is "4D Application"
LOG GET SOURCE($serverName; $souceName)

//these values with be inserted in the "%n" placeholders  in the message
ARRAY TEXT:C222($params; 2)
$params{1}:="arg1"
$params{2}:="arg2"

//you can attach a binary to a message
C_BLOB:C604($data)

$category:=0
$event:=2  //the database %1 has been successfully started
LOG WRITE ENTRY(EVENTLOG_ERROR_TYPE; $category; $event; $params; $data)

$category:=0
$params{1}:="oops"
$event:=5  //%1
LOG WRITE ENTRY(EVENTLOG_ERROR_TYPE; $category; $event; $params; $data)