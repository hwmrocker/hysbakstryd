
var socket = null;
var isopen = false;

window.onload = function() {

    return;

    socket = new WebSocket("ws://127.0.0.1:9000");
    socket.binaryType = "arraybuffer";

    socket.onopen = function() {
        console.log("Connected!");
        isopen = true;
    }

    socket.onmessage = function(e) {
        if (typeof e.data == "string") {
            console.log("Text message received: " + e.data);
        } else {
            var arr = new Uint8Array(e.data);
            var hex = '';
            for (var i = 0; i < arr.length; i++) {
                hex += ('00' + arr[i].toString(16)).substr(-2);
            }
            console.log("Binary message received: " + hex);
        }
    }

    socket.onclose = function(e) {
        console.log("Connection closed.");
        socket = null;
        isopen = false;
    }
};

function log(s) {
    console.log(s);
}

function connect_to_server(e) {
    console.log('connecting...');

    var hostname = document.getElementById('connect_hostname').value | '127.0.0.1';
    var port = document.getElementById('connect_port').value | '9000';

    var username = document.getElementById('connect_username').value;
    var password = document.getElementById('connect_password').value;

    socket = new WebSocket("ws://" + hostname + ":" + port);
    socket.binaryType = "arraybuffer";


    var buf = this.msgpack.pack({'type': 'connect', 'username': username, 'password': password});
    var arr = new Uint8Array(buf);

    socket.onopen = function() {
        log("Connected, logging in...");
        isopen = true;
        socket.send(arr);
    };

    msg_map = {
        'WELCOME': function(msg_type, from, data) {
            log('connected as ' + data);
        }
    }

    socket.onmessage = function(e) {
        // pop off the first byte, don't know why it's there, but it kills our decoder
        var arr = new Uint8Array(e.data.slice(1));
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

}
