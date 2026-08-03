'use strict';

const fs = require('fs');

fs.writeFileSync(
  '/tmp/archonyx-less-marker',
  'LESS_PLUGIN_EXECUTED\n',
  { encoding: 'utf8' }
);

const plugin = {
  install() {}
};

if (typeof registerPlugin === 'function') {
  registerPlugin(plugin);
} else {
  module.exports = plugin;
}
