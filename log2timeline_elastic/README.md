
# PLASO log2timeline/ElasticSearch Tools

## psort2es_proxy.py

PLASO psort to ElasticSearch TCP proxy.

Deals with this issue:
https://github.com/log2timeline/plaso/issues/1156

    "../.. After importing a few thousand entries the elasticsearch instance crashes. In the elasticsearch log
    we get the following java exception: MapperParsingException[failed to parse [file_reference]]; nested:
    NumberFormatException[For input string: "62357-9"];"

The reason is that PSORT lets ES decide on the format of the index, which is deduced from the first values
submitted. This proxy intercepts the creation call and adds a mapping, so the fields are in the right format
despite of the values sent by psort.

The problem will be addressed by this issue later-on:
https://github.com/log2timeline/plaso/issues/1879

Tested with log2timeline 20180818.

IMPORTANT: This is a "hack" and not a full-fledged "download and run" application. You will need to adapt it in order
to make it do what you want it to do.

Based on SimpleTCPRedirector: https://gist.github.com/sivachandran/1969859
