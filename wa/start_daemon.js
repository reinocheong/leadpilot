const fs = require('fs');
const log = fs.createWriteStream('/home/user/leadpilot/.logs/wa_daemon.log', { flags: 'a' });
const origLog = console.log;
const origErr = console.error;

console.log = (...args) => {
  origLog(...args);
  log.write(args.map(a => typeof a === 'string' ? a : JSON.stringify(a)).join(' ') + '\n');
};
console.error = (...args) => {
  origErr(...args);
  log.write('[ERR] ' + args.map(a => typeof a === 'string' ? a : JSON.stringify(a)).join(' ') + '\n');
};

console.log('=== wa_daemon started at', new Date().toISOString(), '===');
require('./wa_daemon.js');
