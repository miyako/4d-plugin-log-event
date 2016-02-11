 /* Sample Message Text File
  *
  * Message Text Files
  * https://msdn.microsoft.com/en-us/library/dd996906(v=vs.85).aspx
  * Reporting Events
  * https://msdn.microsoft.com/en-us/library/aa363680(v=vs.85).aspx
  */
 // This is the header section.
 // The following are the message definitions.
//
//  Values are 32 bit values laid out as follows:
//
//   3 3 2 2 2 2 2 2 2 2 2 2 1 1 1 1 1 1 1 1 1 1
//   1 0 9 8 7 6 5 4 3 2 1 0 9 8 7 6 5 4 3 2 1 0 9 8 7 6 5 4 3 2 1 0
//  +---+-+-+-----------------------+-------------------------------+
//  |Sev|C|R|     Facility          |               Code            |
//  +---+-+-+-----------------------+-------------------------------+
//
//  where
//
//      Sev - is the severity code
//
//          00 - Success
//          01 - Informational
//          10 - Warning
//          11 - Error
//
//      C - is the Customer code flag
//
//      R - is a reserved bit
//
//      Facility - is the facility code
//
//      Code - is the facility's status code
//
//
// Define the facility codes
//
#define FACILITY_SYSTEM                  0x0
#define FACILITY_RUNTIME                 0x2


//
// Define the severity codes
//
#define STATUS_SEVERITY_WARNING          0x2
#define STATUS_SEVERITY_SUCCESS          0x0
#define STATUS_SEVERITY_INFORMATIONAL    0x1
#define STATUS_SEVERITY_ERROR            0x3


//
// MessageId: MSG_1
//
// MessageText:
//
// %1!S!%0
//
#define MSG_1                            ((WORD)0x00000001L)

 // Based on original 4dmsg.dll (no catagory)
//
// MessageId: MSG_DATABASE_LOG_START
//
// MessageText:
//
// The database %1!S! has been successfully started
//
#define MSG_DATABASE_LOG_START           ((WORD)0x00000002L)

//
// MessageId: MSG_WEB_LOG_START
//
// MessageText:
//
// The web server %1!S! has been successfully started
//
#define MSG_WEB_LOG_START                ((WORD)0x00000003L)

//
// MessageId: MSG_WEB_LOG_HALT
//
// MessageText:
//
// The web server %1!S! has been halted
//
#define MSG_WEB_LOG_HALT                 ((WORD)0x00000004L)

//
// MessageId: MSG_5
//
// MessageText:
//
// %1!S!%0
//
#define MSG_5                            ((WORD)0x00000005L)

//
// MessageId: MSG_6
//
// MessageText:
//
// %1!S!%0
//
#define MSG_6                            ((WORD)0x00000006L)

//
// MessageId: MSG_7
//
// MessageText:
//
// %1!S!%0
//
#define MSG_7                            ((WORD)0x00000007L)

 // The LOG EVENT COMMAND (no catagory)
//
// MessageId: MSG_LOG_EVENT
//
// MessageText:
//
// %1!S!%0
//
#define MSG_LOG_EVENT                    ((WORD)0x00000008L)

//
// MessageId: MSG_9
//
// MessageText:
//
// %1!S!%0
//
#define MSG_9                            ((WORD)0x00000009L)

