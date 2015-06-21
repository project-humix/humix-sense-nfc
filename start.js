var sensorName   = 'humix-sense-nfc';
var natChannel   = 'humix.sense.nfc.command';
var workDir      = '/home/liuch/workspace/humix/humix-sense/controls/humix-sense-nfc';
var pythonScript = workDir + '/detectNFC.py';
var processing   = false;
var isClosed     = true;

var net  = require('net');
var fs   = require('fs');
var ps   = require('child_process');
var spawn =  require('child_process').spawn;
var nats = require('nats').connect();//connect immediately

//unlink domainSocket anyway

//the following server is only used for shutdown service
//once someone connects to the domain socket and close
//this service will shutdown
var server = net.createServer(function(conn) { 
    conn.on('end', function () {
        nats.close();
        server.unref();
    });
});

server.on('error', function (err) {
    console.error('failed to start service,' + err);
    nats.close();
    server.unref();
});

nats.subscribe('humix.sense.nfc.status.ping', function(request,replyto){
    console.log(' [NFC] received ping')
    console.log('sending pong');
    nats.publish(replyto, 'humix.sense.nfc.status.pong');
    
});

try {

    ps.exec('sudo python ' + pythonScript);
    isClosed = true;

} catch (e) {
    console.error('initial open failed' + e);
}
