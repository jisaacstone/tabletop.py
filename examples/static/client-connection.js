$(function() {
  var conn = null;
  var player_id = null;
  var game_id = null;
  var game_type = null;

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
      if(game_id){
          conn.send('join,' + JSON.stringify([game_type, game_id, player_id]))
      }
      update_ui();
    };

    conn.onmessage = function(e) {
      log('Received: ' + e.data);
      comma = e.data.indexOf(',')
      if(comma !== -1){
          messageType = e.data.sice(0, comma)
          messageData = e.data.slice(comma + 1)
          log(messageType)
      }
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
