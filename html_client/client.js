
var socket = null;
var isopen = false;

window.onload = function() {

    this.log = function(s) {
        var log_element = document.getElementById('log');
        var ts = '[' + new Date().toISOString().slice(0, 19).replace('T', ' ') + ']';
        log_element.innerText = ts + " " + s + '\n' + log_element.innerText;
    }

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


        var buf = this.msgpack.pack({'type': 'connect', 'username': username, 'password': password});
        var arr = new Uint8Array(buf);

        socket.onopen = function() {
            log("connection established, logging in...");
            isopen = true;
            socket.send(arr);
        };

        msg_map = {
            'WELCOME': function(msg_type, from, data) {
                log('logged in as ' + data);
            },
            'WRONG PASSWORD': function(m,f,t) {
                log('could not log in, wrong password');
                hostname_el.disabled = undefined;
                port_el.disabled = undefined;
                username_el.disabled = undefined;
                password_el.disabled = undefined;
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
                log('received: ' + msg_type + ' from ' + msg_from + ' with: ' + msg_data);
            }

        };

        socket.onclose = function(e) {
            log("Connection closed.");
            socket = null;
            isopen = false;
        };

    };

    log('waiting for input');

};

