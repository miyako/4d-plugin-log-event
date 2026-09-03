//%attributes = {}
//requires admin privileges
$path:=Get 4D folder:C485(Current resources folder:K5:16)+"windows"+Folder separator:K24:12+"4dmsg-clone.dll"
$count_categories:=0
LOG REGISTER SOURCE("Custom 4D Application"; $count_categories; $path; \
EVENTLOG_WARNING_TYPE\
 | EVENTLOG_ERROR_TYPE\
 | EVENTLOG_INFORMATION_TYPE\
 | EVENTLOG_AUDIT_FAILURE\
 | EVENTLOG_AUDIT_SUCCESS)

//  //use this source
LOG SET SOURCE(""; "Custom 4D Application")

ARRAY TEXT:C222($params; 1)
$params{1}:="ì˙ñ{åÍÇÃÉÅÉbÉZÅ[ÉW"

//you can attach a binary to a message
C_BLOB:C604($data)

For ($event; 1; 9)
	LOG WRITE ENTRY(EVENTLOG_INFORMATION_TYPE; $category; $event; $params; $data)
End for 