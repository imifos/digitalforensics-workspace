#!/usr/bin/env python

# psort2es_proxy.py
#
# PLASO psort to ElasticSearch TCP proxy.
#
# Deals with this issue:
#    https://github.com/log2timeline/plaso/issues/1156
#
#    "../.. After importing a few thousand entries the elasticsearch instance crashes. In the elasticsearch log
#    we get the following java exception: MapperParsingException[failed to parse [file_reference]]; nested:
#    NumberFormatException[For input string: "62357-9"];"
#
# The reason is that PSORT lets ES decide on the format of the index, which is deduced from the first values
# submitted. This proxy intercepts the creation call and adds a mapping, so the fields are in the right format
# despite of the values sent by psort.
#
# The problem will be addressed by this issue later-on:
#    https://github.com/log2timeline/plaso/issues/1879
#
# Tested with log2timeline 20180818.
#
# IMPORTANT: This is a "hack" and not a full-fledged "download and run" application. You will need to adapt it in order
# to make it do what you want it to do.
#
# Based on SimpleTCPRedirector: https://gist.github.com/sivachandran/1969859
#
# psort command line: D:\plaso-20180818-Win32\psort.exe -o elastic  --port 9201 --index_name "tl1" D:\cases\c1\tl.plaso
#
# psort -o elastic / Additional Parameters:
#   --index_name INDEX_NAME
#                         Name of the index in ElasticSearch.
#   --doc_type DOCUMENT_TYPE
#                         Name of the document type that will be used in
#                         ElasticSearch.
#   --flush_interval FLUSH_INTERVAL
#                         Events to queue up before bulk insert to
#                         ElasticSearch.
#   --elastic_user ELASTIC_USER
#                         Username to use for Elasticsearch authentication.
#   --server HOSTNAME     The hostname or server IP address of the server.
#   --port PORT           The port number of the server.

# LICENSE
# This is free and unencumbered software released into the public domain.
# 
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
# 
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
# For more information, please refer to <http://unlicense.org>
        
import socket
import threading
import select
import sys

# Network settings
proxy_listening_host = "localhost"
proxy_listening_port = 9201
target_elastic_host = "localhost"
target_elastic_port = 9200

# Mapping we want the PLASO index to have.
#    Can be extracted using https://github.com/mobz/elasticsearch-head
#    No need to install, just download and start "file:///D:/Tools/elasticsearch-head-master/index.html"
# The below mapping also adds a <"copy_to": ["alldata"],> clause as there is no "_all" field in ES anymore.
# No need to add "raw_fields" as a keyword type is added for each field: app_version -> text, app_version.keyword -> raw
document_name="plaso_event"
putmappingbody= '''
        {
            "properties": {
                "is_allocated": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "boolean"
                },
                "source_append": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "app_version": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "number_of_pages": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "record_number": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "number_of_words": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "doc_security": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "event_identifier": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "uuid": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "inode": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "sha2048_hash": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "datetime": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "date"
                },
                "number_of_characters": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "imphash": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "drive_serial_number": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "message_identifier": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "total_time": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "drive_type": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "droid_file_identifier": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "offset": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "revision_number": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "author": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "display_name": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "file_reference": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "number_of_lines": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "strings_parsed": {
                    "type": "object"
                },
                "volume_label": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "filename": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "parser": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "size": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "name": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "relative_path": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "pe_type": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "template": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "pathspec": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "birth_droid_volume_identifier": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "file_attribute_flags": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text"
                },
                "origin": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "description": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "local_path": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "section_names": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "working_directory": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "command_line_arguments": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "file_system_type": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "long_name": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "localized_name": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "scale_crop": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "source_long": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "urls": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "source_short": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "strings": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "dll_name": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "mac_address": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "root": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "key_path": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "birth_droid_file_identifier": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "key": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "source_name": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "timestamp": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "computer_name": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "alldata": {
                    "ignore_above": 4098,
                    "type": "keyword"
                },
                "last_saved_by": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "hyperlinks_changed": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "icon_location": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "timestamp_desc": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "popularity_index": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "shell_item_path": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "i4": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "number_of_paragraphs": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "message": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "creating_app": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "xml_string": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "file_size": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "url": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "links_up_to_date": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "file_entry_type": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "number_of_characters_with_spaces": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "recovered": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "boolean"
                },
                "shared_doc": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "original_url": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "data_type": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "link_target": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "user_sid": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "event_level": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "long"
                },
                "droid_volume_identifier": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                },
                "env_var_location": {
                    "copy_to": [
                        "alldata"
                    ],
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "ignore_above": 2048,
                            "type": "keyword"
                        }
                    }
                }
            }
        }
'''

signal_term_proxy = False


class ClientThread(threading.Thread):

    def __init__(self, client_socket, target_host, target_port):
        threading.Thread.__init__(self)
        self.__client_socket = client_socket
        self.__target_host = target_host
        self.__target_port = target_port

    def run(self):
        print("Client thread started")

        self.__client_socket.setblocking(0)

        print("Connecting to target host")
        target_host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_host_socket.connect((self.__target_host, self.__target_port))
        target_host_socket.setblocking(0)

        print("Ready for traffic - Packets max 100k, v = ES -> PSORT (down), ^ = PSORT -> ES (up)")
        client_data = bytearray()
        target_host_data = bytearray()
        terminate_connection = False
        found_index_creation=False

        while not terminate_connection and not signal_term_proxy:

            inputs = [self.__client_socket, target_host_socket]
            outputs = []

            if len(client_data) > 0:
                outputs.append(self.__client_socket)

            if len(target_host_data) > 0:
                outputs.append(target_host_socket)

            try:
                inputs_ready, outputs_ready, errors_ready = select.select(inputs, outputs, [], 1.0)
            except Exception as e:
                print(e)
                break

            for inp in inputs_ready:
                if inp == self.__client_socket:
                    try:
                        data = self.__client_socket.recv(102400)
                    except Exception as e:
                        print(e)
                    if data != None:
                        if len(data) > 0:
                            target_host_data += data
                        else:
                            terminate_connection = True

                elif inp == target_host_socket:
                    try:
                        data = target_host_socket.recv(102400)
                    except Exception as e:
                        print(e)

                    if data != None:
                        if len(data) > 0:
                            client_data += data
                        else:
                            terminate_connection = True

            for out in outputs_ready:
                if out == self.__client_socket and len(client_data) > 0:
                    sys.stdout.write('v')
                    sys.stdout.flush()
                    bytes_written = self.__client_socket.send(client_data)
                    if bytes_written > 0:
                        client_data = client_data[bytes_written:]

                elif out == target_host_socket and len(target_host_data) > 0:

                    sys.stdout.write('^')
                    sys.stdout.flush()
                    bytes_written = target_host_socket.send(target_host_data)

                    temp_target_host_data=target_host_data

                    if bytes_written > 0:
                        target_host_data = target_host_data[bytes_written:]

                    # Logic to intercept the index creation request in order to
                    # sneak in additional requests to define mapping et al.
                    if not found_index_creation:
                        string_data=temp_target_host_data.decode('utf-8')

                        if "PUT /" in string_data and "mappings" in string_data:
                            print("\n\nINTERCEPT TO ADD MAPPING");
                            found_index_creation = True
                            start = string_data.index("PUT /") + len("PUT /")
                            end = string_data.index(" HTTP/", start)
                            index_name=string_data[start:end] # no error handling, it's a hack after all :)
                            print("TO ES: ",string_data,"\n\n")

                            target_host_socket.setblocking(1) # we want to wait for the replay right now
                            d = target_host_socket.recv(10240)
                            print("INTERCEPTED REPLAY:", d)
                            msg = "PUT /" + index_name + "/_mapping/"+document_name + ' HTTP/1.1\r\nHost: 127.0.0.1:'+str(proxy_listening_port)+'\r\nAccept-Encoding: identity\r\nContent-Length: ' + \
                                  str(len(putmappingbody)) + '\r\nconnection: keep-alive\r\ncontent-type: application/json\r\n\r\n' + putmappingbody
                            print("ADD MAPPING for " + index_name)
                            target_host_socket.setblocking(0)
                            target_host_socket.send(msg.encode())
                            print("LEAVE INTERCEPTION\n\n")

        self.__client_socket.close()
        target_host_socket.close()
        print("\nClient connection/thread terminated. CTRL+C to stop proxy to listen for new connections.")


if __name__ == '__main__':

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((proxy_listening_host, proxy_listening_port))
    server_socket.listen(5)
    print("Waiting for connections...")

    while True:

        try:
            accepted_socket, address = server_socket.accept()
        except KeyboardInterrupt:
            print("\nGracefully terminating proxy...")
            signal_term_proxy = True
            break

        ClientThread(accepted_socket, target_elastic_host, target_elastic_port).start()

    server_socket.close()
    print("\nProxy terminated. Over and Out!");

