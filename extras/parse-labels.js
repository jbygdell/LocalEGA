// Based upon example by Guy Harwood https://guyharwood.co.uk/

'use strict'

const https = require('https')

const pullRequestId = process.argv[2]

if (!pullRequestId) {
	console.log('Missing argument: pull request id')
	process.exit(1)
}

const pullRequestUrl = `/repos/EGA-archive/LocalEGA/pulls/${pullRequestId}`

const options = {
	hostname: 'api.github.com',
	path: pullRequestUrl,
	method: 'GET',
	headers: {
		'User-Agent': 'node/https'
	}
}

const parseResponse = (res) => {
	let labels
	try {
		labels = JSON.parse(res).labels
		if (!labels || labels.length === 0) {
			console.log(`no labels found attached to PR ${pullRequestId}`)
			process.exit(0)
		}
	} catch (err) {
		console.error(`error parsing labels for PR ${pullRequestId}`)
		console.error(err)
		process.exit(1)
	}
	const ciBuildImages = labels.find(item => item.name === `build-images`)
	if (ciBuildImages) {
		console.log(`build-images`)
		process.exit(0)
	}
	console.log(`CI Build label not found on PR ${pullRequestId}`)
	process.exit(0)
}

https.get(options, (response) => {
	let data = ''

	response.on('data', (chunk) => {
		data += chunk
	})

	response.on('end', () => {
		parseResponse(data)
	})
}).on('error', (err) => {
	console.error('Error: ' + err.message)
})