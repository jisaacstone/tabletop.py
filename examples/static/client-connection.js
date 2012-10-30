$(function() {
  var conn = null;
  var playerId = null;
  var gameId = null;
  var gameType = null;
  window.messageHandler = simpleHandler();

  function log(msg) {
    var control = $('#log');
    control.html(control.html() + msg + '<br/>');
    control.scrollTop(control.scrollTop() + 1000);
  }

  function connect() {
    disconnect();

    var transports = $('#protocols input:checked').map(function(){
        return $(this).attr('id');
    }).get();

    conn = new SockJS('http://' + window.location.host + '/game', transports);

    log('Connecting...');

    conn.onopen = function() {
      log('Connected.');
      if(gameId) {
          conn.send('join,' + JSON.stringify([game_type, game_id, player_id]))
      }
      update_ui();
    };

    conn.onmessage = function(e) {
      log('Received: ' + e.data);
      var message = JSON.parse(e.data)
      handleMessage(message[0], message[1])
    };

    conn.onclose = function() {
      log('Disconnected.');
      conn = null;
      update_ui();
    };
  }

  function disconnect() {
    if (conn != null) {
      log('Disconnecting...');

      conn.close();
      conn = null;

      update_ui();
    }
  }

  function update_ui() {
    var msg = '';

    if (conn == null || conn.readyState != SockJS.OPEN) {
      $('#status').text('disconnected');
      $('#connect').text('Connect');
    } else {
      $('#status').text('connected (' + conn.protocol + ')');
      $('#connect').text('Disconnect');
    }
  }

  $('#connect').click(function() {
    if (conn == null) {
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
    conn.send(text);
    $('#text').val('').focus();
    return false;
  });

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
            var selector = '#' + data['varType'];
            if(data['player'] & data['player'] != playerId) {
                selector += ' .' + data['player'];
            }
            selector += ' .' + data['key'];
            $(selector).html(objToHtml(data['value']));
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

function objToHtml(obj) {
    switch(typeof(obj)) {
        case "string":
        case "number":
            return obj;
        case "object":
            var html = '';
            for(var key in obj) {
                html += '<span class="' + key + '">' +
                    objTpHtml(obj[key]) +
                    '</span>\n'; 
            }
            return html;
    }
}

