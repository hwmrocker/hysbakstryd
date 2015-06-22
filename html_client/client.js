
var socket = null;
var isopen = false;

$.fn.selectRange = function(start, end) {
    if(!end) end = start;
    return this.each(function() {
        if (this.setSelectionRange) {
            this.focus();
            this.setSelectionRange(start, end);
        } else if (this.createTextRange) {
            var range = this.createTextRange();
            range.collapse(true);
            range.moveEnd('character', end);
            range.moveStart('character', start);
            range.select();
        }
    });
};

window.onload = function() {

    var help_line_template = Handlebars.compile($('#help-line-template').html());
    var help_command_template = Handlebars.compile("Received help for {{ command_name }}:\n{{{ doc }}}\n  Parameters: {{{ params }}}\n  Optional: {{{ optional }}}");

    var log_element = document.getElementById('log');

    this.log = function(s) {
        var ts = '[' + new Date().toISOString().slice(0, 19).replace('T', ' ') + ']';
        log_element.innerText = ts + " " + s + '\n' + log_element.innerText;
        log_element.scrollTop = 0;
    };

    this.connect_to_server = function() {
        var hostname_el = document.getElementById('connect_hostname');
        var port_el = document.getElementById('connect_port');
        var username_el = document.getElementById('connect_username');
        var password_el = document.getElementById('connect_password');

        hostname_el.disabled = "disabled";
        port_el.disabled = "disabled";
        username_el.disabled = "disabled";
        password_el.disabled = "disabled";

        var hostname = hostname_el.value | '127.0.0.1';
        var port = port_el.value | '9000';

        var username = username_el.value;
        var password = password_el.value;

        socket = new WebSocket("ws://" + hostname + ":" + port);
        socket.binaryType = "arraybuffer";

        socket.send_msgpack = function(obj) {
            var buf = window.msgpack.pack(obj);
            var arr = new Uint8Array(buf);
            socket.send(arr);
        };

        socket.onopen = function() {
            log("connection established, logging in...");
            isopen = true;
            socket.send_msgpack({'type': 'connect', 'username': username, 'password': password});
        };

        msg_map = {
            'LOGGEDIN': function(msg_type, from, data) {
                log("logged in as '" + data.username + "'\n    " + data.msg);
                $('#connection-form').toggle("fast");
                $('#connected-form').toggle("fast");
                hostname_el.disabled = undefined;
                port_el.disabled = undefined;
                username_el.disabled = undefined;
                password_el.disabled = undefined;

                $('#title-row').animate({height: '2%'});
                $('#title-row h1').animate({'margin-top': '-5.8%'});
                $('#connected-form').animate({height: '48%'});

                socket.send_msgpack({'type': 'help_command'});
            },
            'activated': function(t,f,d) {
                log('You have been activated for play.\n    ' + d.msg);
            },
            'WELCOME': function(t,f,d) {
                log('New player \'' + d + '\' has joined the game.');
            },
            'WRONG PASSWORD': function(t,f,d) {
                log('could not log in, wrong password');
                hostname_el.disabled = undefined;
                port_el.disabled = undefined;
                username_el.disabled = undefined;
                password_el.disabled = undefined;
            },
            'help_for_commands': function(t,f,d) {

                var commands = d;
                var list_el = $('#command-list');
                commands.sort();
                list_el.empty();
                for (var index in commands) {
                    context = {name: commands[index]};
                    list_el.append(help_line_template(context));
                }
            },
            'help_for_command': function(t,f,d) {
                log(help_command_template({
                    'command_name': d['name'],
                    'doc': d['doc'],
                    'params': JSON.stringify(d['params']),
                    'optional': JSON.stringify(d['optional'])
                }));
            }
        };

        socket.onmessage = function(e) {
            var arr = new Uint8Array(e.data);
            var msg = msgpack.unpack(arr);
            msg_type = msg[0];
            msg_from = msg[1];
            msg_data = msg[2];
            if (msg_type in msg_map) {
                msg_map[msg_type](msg_type, msg_from, msg_data);
            }
            else {
                if (typeof msg_data === 'string') {
                    log('received: ' + msg_type + ' from ' + msg_from + ' with: ' + msg_data);
                }
                else {
                    log('received: ' + msg_type + ' from ' + msg_from + ' with: ' + JSON.stringify(msg_data));
                }
            }

        };

        socket.onclose = function(e) {
            if (isopen) {
                log("Connection closed.");
                socket = null;
                isopen = false;
                $('#connection-form').toggle("fast");
                $('#connected-form').toggle("fast");
                $('#title-row').animate({height: '20%'});
                $('#title-row h1').animate({'margin-top': '0%'});
            }
        };

        socket.onerror = function(e) {
            log("Connection received an error: not connected.");
            if (isopen) {
                socket = null;
                isopen = false;
                $('#connection-form').toggle("fast");
                $('#connected-form').toggle("fast");
                $('#title-row').animate({height: '20%'});
                $('#title-row h1').animate({'margin-top': '0%'});
            }
        };

    };

    this.log_out = function() {
        // $('#connection-form').animate({height: '', opacity: 1});
        socket.close();
    };

    this.send_to_server = function() {
        try {
            var type = $('#action_type').val();
            var data = $.parseJSON($('#action_data').val());
            var to_send = $.extend({'type': type}, data);
            log('sending: ' + JSON.stringify(to_send));
            var buf = this.msgpack.pack(to_send);
            var arr = new Uint8Array(buf);
            socket.send(arr);
        } catch(e) {
            log('could not decode data, please enter a valid JSON string');
        }

    };

    window.set_command = function(command_name, command_data) {
        $('#action_type').val(command_name);
        if (command_data) {
            $('#action_data').val(command_data);
        }
        else {
            $('#action_data').val('{}');
            $('#action_data').selectRange(1);
        }
        $('#action_data').focus();
    };

    window.activate_on_server = function() {
        log('activating for play...');
        var buf = this.msgpack.pack({'type': 'activate'});
        var arr = new Uint8Array(buf);
        socket.send(arr);

    };

    log('waiting for input');

};

