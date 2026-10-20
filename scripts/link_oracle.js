// Parse each JSON header value from standard input with the http-link-header package
// installed under the folder given as the first argument; print the refs as JSON.
'use strict'
const path = require('path')
const Link = require(path.join(process.argv[2], 'node_modules', 'http-link-header'))
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'))
const out = input.map((header) => {
  try {
    return Link.parse(header).refs
  } catch (error) {
    return { error: String(error) }
  }
})
process.stdout.write(JSON.stringify(out))
