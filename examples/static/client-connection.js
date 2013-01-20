$(function() {
    var conn = conn || null;
    window.messageHandler = simpleHandler();

    function log(msg) {
        var control = $('#log');
        control.html(control.html() + msg + '<br/>');
        control.scrollTop(control.scrollTop() + 1000);
    }

    function update_ui() {
        var msg = '';

        if (window.conn == null || window.conn.readyState != SockJS.OPEN) {
          $('#status').text('disconnected');
          $('#connect').text('Connect');
        } else {
          $('#status').text('connected (' + window.conn.protocol + ')');
          $('#connect').text('Disconnect');
        }
    }


    function connect(callback) {
        callback = callback || function() {};
        disconnect();

        var transports = $('#protocols input:checked').map(function(){
            return $(this).attr('id');
        }).get();

        window.conn = new SockJS('http://' + window.location.host + '/game', transports);

        log('Connecting...');

        window.conn.onopen = function() {
          log('Connected.');
          update_ui();
          callback();
        };

        window.conn.onmessage = function(e) {
          log('Received: ' + e.data);
          var message = JSON.parse(e.data)
          handleMessage(message[0], message[1])
        };

        window.conn.onclose = function() {
          log('Disconnected.');
          window.conn = null;
          update_ui();
        };
    }

    function disconnect() {
        if (window.conn != null) {
          log('Disconnecting...');

          window.conn.close();
          window.conn = null;

          update_ui();
        }
    }

    $('#connect').click(function() {
        if (window.conn == null) {
          connect();
        } else {
          disconnect();
        }

        update_ui();
        return false;
    });

    $('form').submit(function() {
        var text = $('#text').val();
        log('Sending: ' + text);
        window.conn.send(text);
        $('#text').val('').focus();
        return false;
    });

    function onConnect(){
        if(gameId !== null) {
            var pid = (playerId === null ? -1 : playerId)
            var text = 'join,' + JSON.stringify({'game_id':gameId, 'player_id':pid});
            console.log(text);
            window.conn.send(text);
        }
        console.log('no game');
    }
    connect(onConnect);
});

function handleMessage(action, data) {
    return window.messageHandler[action](data);
}

function simpleHandler() {
    return {
        'set': function(data) {
            $('.' + data['element']).attr(data['attr'], data['value']);
        },
        'setText': function(data) {
            $('#' + data[0]).html(data[1]);
        },
        'pushState': function(data) {
            $('#' + data[0]).html(data[1]);
            push(data[0], data[1]);
        },
        'update': function(data) {
            var path = [data['varType']];
            if(data['player'] & data['player'] != playerId) {
                 path.push(data['player']);
            }
            path.push(data['key']);
            selector = createOrSelect(path);
            console.log('selector: ' + selector);
            $(selector).replaceWith(objToHtml(data['key'], data['value']));
        }
    };
}

function push(variable, value) {
    var url = '/g/';
    window[variable] = value;
    for each (var v in [gameType, gameId, playerId]) {
        if(v !== null) {
            url += v + '/';
        }
    }
    window.history.pushState({variable: value}, '', url);
}

function objToHtml(k, obj) {
    var ul = $(document.createElement('ul')).addClass(k);
    if(typeof(k) == "string") {
        ul.append($('<li>').addClass('title').html(k.replace('_', ' ')));
    }
    switch(typeof(obj)) {
        case "string":
        case "number":
            ul.attr('data-' + k, obj);
            ul.append($('<li>').addClass('value').html(obj));
            break;
        case "object":
            for(var key in obj) {
                ul.attr('data-' + key, obj[key]);
                ul.append($('<li>').addClass('value').append(objToHtml(key, obj[key]))); 
            }
            break;
    }
    return ul;
}

function createOrSelect(path) {
    selector = '#' + path.shift();
    while(path.length) {
        next = path.shift();
        if( ! $(selector).children('.' + next).length) {
            $(selector).append('<span class="' + next + '"></span>');
        }
        selector += ' .' + next;
    }
    return selector;
} 
