xquery version "3.0";

import module namespace nav="http://www.tei-c.org/tei-simple/navigation" at "modules/navigation.xql";
import module namespace config="http://www.tei-c.org/tei-simple/config" at "modules/config.xqm";

(: The following external variables are set by the repo:deploy function :)

(: file path pointing to the exist installation directory :)
declare variable $home external;
(: path to the directory containing the unpacked .xar package :)
declare variable $dir external;
(: the target collection into which the app is deployed :)
declare variable $target external;

if (not(sm:user-exists("stazh"))) then
    sm:create-account("stazh", "", "tei", ())
else
    (),
(: API needs dba rights for LaTeX :)
sm:chgrp(xs:anyURI($target || "/modules/lib/api-dba.xql"), "dba"),
sm:chmod(xs:anyURI($target || "/modules/lib/api-dba.xql"), "rwxr-Sr-x"),

sm:chmod(xs:anyURI($target || "/data/annotate"), "rwxrwxr-x"),
sm:chown(xs:anyURI($target || "/data/annotate"), "stazh"),
sm:chmod(xs:anyURI($target || "/data/register.xml"), "rw-rw-r--"),
xmldb:create-collection($target || "/data", "temp"),
sm:chmod(xs:anyURI($target || "/data/temp"), "rwxrwxr-x"),
sm:chown(xs:anyURI($target || "/data/temp"), "tei"),
sm:chgrp(xs:anyURI($target || "/data/temp"), "tei"),
sm:chmod(xs:anyURI($target || "/odd"), "rwxrwxr-x"),
sm:chmod(xs:anyURI($target || "/transform"), "rwxrwxr-x"),
for $resource in xmldb:get-child-resources($target || "/transform")
return
    if (ends-with($resource, "-main.xql")) then
        sm:chmod(xs:anyURI($target || "/transform/" || $resource), "rwxrwxr-x")
    else
        sm:chmod(xs:anyURI($target || "/transform/" || $resource), "rw-rw-r--")
